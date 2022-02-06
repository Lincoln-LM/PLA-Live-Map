"""Flask application to display live memory information from
   PLA onto a map"""
import json
import struct
import requests
import colorama
from colorama import Fore, Back, Style
from flask import Flask, render_template, request
import nxreader
import time
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

def generate_next_shiny(spawner_id,rolls,guaranteed_ivs):
    """Find the next shiny advance for a spawner"""
    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+spawner_id*0x40:X}",8)
    spawner_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF
    main_rng = XOROSHIRO(spawner_seed)
    for adv in range(40960):
        generator_seed = main_rng.next()
        rng = XOROSHIRO(generator_seed)
        rng.next()
        encryption_constant,pid,ivs,ability,gender,nature,shiny = \
            generate_from_seed(rng.next(),rolls,guaranteed_ivs)
        if shiny:
            break
        main_rng.next()
        main_rng = XOROSHIRO(main_rng.next())
    return adv,encryption_constant,pid,ivs,ability,gender,nature

@app.route('/read-seed', methods=['POST'])
def read_seed():
    """Read current information and next shiny for a spawner"""
    spawner_id = request.json['spawnerID']
    thresh = request.json['thresh']
    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+spawner_id*0x80:X}",8)
    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+spawner_id*0x40:X}",8)
    spawner_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF
    rng = XOROSHIRO(generator_seed)
    rng.next()
    fixed_seed = rng.next()
    encryption_constant,pid,ivs,ability,gender,nature,shiny \
        = generate_from_seed(fixed_seed,request.json['rolls'],request.json['ivs'])
    display = f"Spawner Seed: {spawner_seed:X}<br>"
    if shiny:
        display += f"Shiny: <font color=\"green\"><b>{shiny}</b></font></br>"
    else:
        display += f"Shiny: <font color=\"red\"><b>{shiny}</b></font><br>"
    display += f"EC: {encryption_constant:X} PID: {pid:X}<br>" \
              f"Nature: {natures[nature]} Ability: {ability} Gender: {gender}<br>" \
              f"{'/'.join(str(iv) for iv in ivs)}<br>"
    adv,encryption_constant,pid,ivs,ability,gender,nature \
        = generate_next_shiny(spawner_id,request.json['rolls'],request.json['ivs'])
    if adv <= thresh:
        display += f"Next Shiny: <font color=\"green\"><b> {adv} </b></font><br>"
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

@app.route('/get-shiny', methods=['POST'])
def getshiny():
    thresh = request.json['thresh']
    name = request.json['name']
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{name}.json"
    markers = json.loads(requests.get(url).text)
    size = (len(markers.keys()))-1
    """Scan all active spawns"""
    spawns = {}
    print(f"Checking up to index {size}")
    for index in range(0,size):
        if index % int(size//100) == 0:
            print(f"{index/size*100}% done scanning")
        generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+index*0x80:X}",8)
        generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+index*0x40:X}",8)
        spawner_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF
        rng = XOROSHIRO(generator_seed)
        rng.next()
        fixed_seed = rng.next()
        ident = index*17
        print(ident)
        encryption_constant,pid,ivs,ability,gender,nature,shiny \
            = generate_from_seed(fixed_seed,request.json['rolls'],markers[str(ident)]["ivs"])
        adv,encryption_constant,pid,ivs,ability,gender,nature \
            = generate_next_shiny(ident,request.json['rolls'],markers[str(ident)]["ivs"])
        pos = markers[str(ident)]["coords"]
        if adv <= thresh:
            spawns[str(ident)] = {"check":"True",
                                  "x":pos[0],
                                  "y":pos[1],
                                  "z":pos[2]}
        else:
            spawns[str(ident)] = {"check":"False",
                                  "x":pos[0],
                                  "y":pos[1],
                                  "z":pos[2]}
    return json.dumps(spawns)
    
#@app.route('/get-shiny', methods=['POST'])
#def getshiny():
#    underthresh = "false"
#    spawner_id = request.json['spawnerID']
#    thresh = request.json['thresh']
#    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+spawner_id*0x80:X}",8)
#   generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+spawner_id*0x40:X}",8)
# #   spawner_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF
#    rng = XOROSHIRO(generator_seed)
#    rng.next()
#    fixed_seed = rng.next()
#    encryption_constant,pid,ivs,ability,gender,nature,shiny \
#        = generate_from_seed(fixed_seed,request.json['rolls'],request.json['ivs'])
#    adv,encryption_constant,pid,ivs,ability,gender,nature \
#        = generate_next_shiny(spawner_id,request.json['rolls'],request.json['ivs'])
#    if adv <= thresh:
#        underthresh = "true"
#    print(f"Spawner: {spawner_id} Shiny: {underthresh}")
#    return underthresh
        
    
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
