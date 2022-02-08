"""Flask application to display live memory information from
   PLA onto a map"""
import json
import struct
import requests
from flask import Flask, render_template, request
import nxreader
from pa8 import Pa8
from xoroshiro import XOROSHIRO

with open("./static/resources/text_natures.txt",encoding="utf-8") as text_natures:
    NATURES = text_natures.read().split("\n")
with open("./static/resources/text_species.txt",encoding="utf-8") as text_species:
    SPECIES = text_species.read().split("\n")
PLAYER_LOCATION_PTR = "[[[[[[main+42B2558]+88]+90]+1F0]+18]+80]+90"
SPAWNER_PTR = "[[main+4267ee0]+330]"
PARTY_PTR = "[[[main+4268000]+d0]+58]"
WILD_PTR = "[[[[main+4267f00]+b0]+e0]+d0]"

with open("config.json","r",encoding="utf-8") as config:
    IP_ADDRESS = json.load(config)["IP"]

app = Flask(__name__)
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
        main_rng.reseed(main_rng.next())
    return adv,encryption_constant,pid,ivs,ability,gender,nature

def generate_mass_outbreak(main_rng,rolls):
    """Generate the current set of a mass outbreak and return a string representing it along with
       a bool to show if a shiny is present"""
    # pylint: disable=too-many-locals
    # this many variables is appropriate to display all the information about
    # the mass outbreak that a user might want
    display = ""
    shiny_present = False
    for init_spawn in range(1,5):
        generator_seed = main_rng.next()
        main_rng.next() # spawner 1's seed, unused
        fixed_rng = XOROSHIRO(generator_seed)
        fixed_rng.next()
        fixed_seed = fixed_rng.next()
        encryption_constant,pid,ivs,ability,gender,nature,shiny = \
            generate_from_seed(fixed_seed,rolls,0)
        display += f"<b>Init Spawn {init_spawn}</b> Shiny: " \
                   f"<b><font color=\"{'green' if shiny else 'red'}\">{shiny}</font></b><br>" \
                   f"EC: {encryption_constant:08X} PID: {pid:08X}<br>" \
                   f"Nature: {NATURES[nature]} Ability: {ability} Gender: {gender}<br>" \
                   f"{'/'.join(str(iv) for iv in ivs)}<br>"
        shiny_present |= shiny
    group_seed = main_rng.next()
    main_rng.reseed(group_seed)
    respawn_rng = XOROSHIRO(group_seed)
    for respawn in range(1,9):
        generator_seed = respawn_rng.next()
        respawn_rng.next() # spawner 1's seed, unused
        respawn_rng.reseed(respawn_rng.next())
        fixed_rng = XOROSHIRO(generator_seed)
        fixed_rng.next()
        fixed_seed = fixed_rng.next()
        encryption_constant,pid,ivs,ability,gender,nature,shiny = \
            generate_from_seed(fixed_seed,rolls,0)
        display += f"<b>Respawn {respawn}</b> Shiny: " \
                   f"<b><font color=\"{'green' if shiny else 'red'}\">{shiny}</font></b><br>" \
                   f"EC: {encryption_constant:08X} PID: {pid:08X}<br>" \
                   f"Nature: {NATURES[nature]} Ability: {ability} Gender: {gender}<br>" \
                   f"{'/'.join(str(iv) for iv in ivs)}<br>"
        shiny_present |= shiny
    return display,shiny_present

def generate_next_shiny_mass_outbreak(main_rng,rolls):
    """Find the next shiny of a mass outbreak and return a string representing it"""
    shiny_present = False
    advance = 0
    while not shiny_present:
        advance += 1
        display, shiny_present = generate_mass_outbreak(main_rng,rolls)
    return f"<b>Advance: {advance}</b><br>{display}"

@app.route('/read-battle', methods=['GET'])
def read_battle():
    """Read all battle pokemon and return the information as an html formatted string"""
    display = ""
    party_count = reader.read_pointer_int(f"{PARTY_PTR}+88",1)
    wild_count = reader.read_pointer_int(f"{WILD_PTR}+1a0",1) \
               - party_count
    if wild_count > 30:
        wild_count = 0
    for i in range(wild_count):
        pkm = Pa8(reader.read_pointer(f"{WILD_PTR}+{0xb0+8*(i+party_count):X}"\
                                       "]+70]+60]+98]+10]",Pa8.STOREDSIZE))
        pokemon_name = f"{SPECIES[pkm.species]}" \
                       f"{('-' + str(pkm.form_index)) if pkm.form_index > 0 else ''} " \
                       f"{'' if pkm.shiny_type == 0 else '⋆' if pkm.shiny_type == 1 else '◇'}"
        pokemon_info = f"EC: {pkm.encryption_constant:08X}<br>" \
                       f"PID: {pkm.pid:08X}<br>" \
                       f"Nature: {NATURES[pkm.nature]}<br>" \
                       f"Ability: {pkm.ability_string}<br>" \
                       f"IVs: {'/'.join(str(iv) for iv in pkm.ivs)}"
        if pkm.is_valid:
            display += f"<button type=\"button\" class=\"collapsible\" " \
                       f"data-for=\"battle{i}\" onclick=collapsibleOnClick()>{i+1} " \
                       f"{pokemon_name}</button>" \
                       f"<div class=\"info\" id=\"battle{i}\">{pokemon_info}</div><br>"
    return display

@app.route('/read-mass-outbreak', methods=['POST'])
def read_mass_outbreak():
    """Read current mass outbreak information and predict next shiny"""
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{request.json['name']}.json"
    minimum = int(list(json.loads(requests.get(url).text).keys())[-1])
    group_id = 510
    group_seed = 0
    while group_seed == 0 and group_id != minimum:
        group_id -= 1
        print(f"Finding group_id {510-group_id}/{510-minimum}")
        group_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x70+group_id*0x440+0x408:X}",8)
    if group_id == minimum:
        print("No mass outbreak found")
        return json.dumps(["No mass outbreak found","No mass outbreak found"])
    print(f"Found group_id {group_id}")
    generator_seed = reader.read_pointer_int(f"main+4267ee0]+330]+{0x70+group_id*0x440+0x20:X}",8)
    group_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF
    main_rng = XOROSHIRO(group_seed)
    display = [f"Group Seed: {group_seed:X}<br>"
               + generate_mass_outbreak(main_rng,request.json['rolls'])[0],
               generate_next_shiny_mass_outbreak(main_rng,request.json['rolls'])]
    return json.dumps(display)

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
              f"Nature: {NATURES[nature]} Ability: {ability} Gender: {gender}<br>" \
              f"{'/'.join(str(iv) for iv in ivs)}<br>"
    adv,encryption_constant,pid,ivs,ability,gender,nature \
        = generate_next_shiny(group_id,request.json['rolls'],request.json['ivs'])
    if adv <= thresh:
        display += f"Next Shiny: <font color=\"green\"><b>{adv}</b></font><br>"
    else:
        display += f"Next Shiny: {adv} <br>"
    display += f"EC: {encryption_constant:X} PID: {pid:X}<br>" \
               f"Nature: {NATURES[nature]} Ability: {ability} Gender: {gender}<br>" \
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
            generate_next_shiny(int(group_id),request.json['rolls'],marker["ivs"])
        if adv <= thresh:
            near.append(group_id)
    return json.dumps(near)

if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
