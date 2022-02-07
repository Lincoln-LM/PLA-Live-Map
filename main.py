"""Flask application to display live memory information from
   PLA onto a map"""
import json
import struct
import requests
from flask import Flask, render_template, request
import nxreader
from xoroshiro import XOROSHIRO

natures = ["Hardy","Lonely","Brave","Adamant","Naughty",
           "Bold","Docile","Relaxed","Impish","Lax",
           "Timid","Hasty","Serious","Jolly","Naive",
           "Modest","Mild","Quiet","Bashful","Rash",
           "Calm","Gentle","Sassy","Careful","Quirky"]
PLAYER_LOCATION_PTR = "[[[[[[main+42B2558]+88]+90]+1F0]+18]+80]+90"
SPAWNER_PTR = "[[main+4267ee0]+330]"
app = Flask(__name__)
with open("config.json","r",encoding="utf-8") as config:
    IP_ADDRESS = json.load(config)["IP"]
reader = nxreader.NXReader(IP_ADDRESS)

def generate_from_seed(seed,rolls,guaranteed_ivs):
    """Generate pokemon information from a fixed seed (FixInitSpec)"""
    rng = XOROSHIRO(seed)
    encryption_constant = rng.rand(0xFFFFFFFF)
    sidtid = rng.rand(0xFFFFFFFF)
    for _ in range(rolls):
        pid = rng.rand(0xFFFFFFFF)
        shiny = ((pid >> 16) ^ (sidtid >> 16) ^ (pid & 0xFFFF) ^ (sidtid & 0xFFFF)) < 0x10
        if shiny:
            break
    ivs = [-1,-1,-1,-1,-1,-1]
    for i in range(guaranteed_ivs):
        index = rng.rand(6)
        while ivs[index] != -1:
            index = rng.rand(6)
        ivs[index] = 31
    for i in range(6):
        if ivs[i] == -1:
            ivs[i] = rng.rand(32)
    ability = rng.rand(2)
    gender = rng.rand(252) + 1
    nature = rng.rand(25)
    return encryption_constant,pid,ivs,ability,gender,nature,shiny

def generate_next_shiny(group_id,rolls,guaranteed_ivs):
    """Find the next shiny advance for a spawner"""
    group_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x70+group_id*0x440+0x408:X}",8)
    main_rng = XOROSHIRO(group_seed)
    for adv in range(1,40960):
        generator_seed = main_rng.next()
        main_rng.next() # spawner 1's seed, unused
        rng = XOROSHIRO(generator_seed)
        rng.next()
        encryption_constant,pid,ivs,ability,gender,nature,shiny = \
            generate_from_seed(rng.next(),rolls,guaranteed_ivs)
        if shiny:
            break
        main_rng = XOROSHIRO(main_rng.next())
    return adv,encryption_constant,pid,ivs,ability,gender,nature

@app.route('/read-seed', methods=['POST'])
def read_seed():
    """Read current information and next shiny for a spawner"""
    group_id = request.json['groupID']
    thresh = request.json['thresh']
    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}"\
                                             f"+{0x70+group_id*0x440+0x20:X}",8)
    rng = XOROSHIRO(generator_seed)
    rng.next()
    fixed_seed = rng.next()
    encryption_constant,pid,ivs,ability,gender,nature,shiny \
        = generate_from_seed(fixed_seed,request.json['rolls'],request.json['ivs'])
    display = f"Generator Seed: {generator_seed:X}<br>" \
              f"Shiny: <font color=\"{'green' if shiny else 'red'}\"><b>{shiny}</b></font><br>" \
              f"EC: {encryption_constant:X} PID: {pid:X}<br>" \
              f"Nature: {natures[nature]} Ability: {ability} Gender: {gender}<br>" \
              f"{'/'.join(str(iv) for iv in ivs)}<br>"
    adv,encryption_constant,pid,ivs,ability,gender,nature \
        = generate_next_shiny(group_id,request.json['rolls'],request.json['ivs'])
    if adv <= thresh:
        display += f"Next Shiny: <font color=\"green\"><b>{adv}</b></font><br>"
    else:
        display += f"Next Shiny: {adv} <br>"
    display += f"EC: {encryption_constant:X} PID: {pid:X}<br>" \
               f"Nature: {natures[nature]} Ability: {ability} Gender: {gender}<br>" \
               f"{'/'.join(str(iv) for iv in ivs)}<br>"
    return display

@app.route('/teleport', methods=['POST'])
def teleport():
    """Teleport the player to provided coordinates"""
    coordinates = request.json['coords']
    print(f"Teleporting to {coordinates}")
    position_bytes = struct.pack('fff', *coordinates)
    reader.write_pointer(PLAYER_LOCATION_PTR,f"{int.from_bytes(position_bytes,'big'):024X}")
    return ""

@app.route('/read-coords', methods=['GET'])
def read_coords():
    """Read the players current position"""
    pos = struct.unpack('fff', reader.read_pointer(PLAYER_LOCATION_PTR,12))
    coords = {
        "x":pos[0],
        "y":pos[1],
        "z":pos[2]
    }
    return json.dumps(coords)

@app.route('/update-positions', methods=['GET'])
def update_positions():
    """Scan all active spawns"""
    spawns = {}
    size = reader.read_pointer_int(f"{SPAWNER_PTR}+18",4)
    size = int(size//0x40 - 1)
    print(f"Checking up to index {size}")
    for index in range(0,size):
        if index % int(size//100) == 0:
            print(f"{index/size*100}% done scanning")
        position_bytes = reader.read_pointer(f"{SPAWNER_PTR}+{0x70+index*0x40:X}",12)
        seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+index*0x40:X}",12)
        pos = struct.unpack('fff', position_bytes)
        if not (seed == 0 or pos[0] < 1 or pos[1] < 1 or pos[2] < 1):
            print(f"Active: spawner_id {index} {pos[0]},{pos[1]},{pos[2]} {seed:X}")
            spawns[str(index)] = {"x":pos[0],
                                  "y":pos[1],
                                  "z":pos[2],
                                  "seed":seed}
    return json.dumps(spawns)

@app.route('/check-near', methods=['POST'])
def check_near():
    """Check all spawners' nearest shiny advance to update icons"""
    thresh = request.json['thresh']
    name = request.json['name']
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{name}.json"
    markers = json.loads(requests.get(url).text)
    maximum = list(markers.keys())[-1]
    near = []
    for group_id, marker in markers.items():
        print(f"Checking group_id {group_id}/{maximum}")
        adv,_,_,_,_,_,_ = \
            generate_next_shiny(group_id,request.json['rolls'],marker["ivs"])
        if adv <= thresh:
            near.append(group_id)
    return json.dumps(near)

@app.route("/")
def root():
    """Display index.html at the root of the application"""
    return render_template('index.html')

@app.route("/map/<name>")
def load_map(name):
    """Read markers and generate map based on location"""
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{name}.json"
    markers = json.loads(requests.get(url).text)
    return render_template('map.html',markers=markers.values(),map_name=name)

if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
