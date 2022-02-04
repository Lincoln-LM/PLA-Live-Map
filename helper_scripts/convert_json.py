"""Convert json into a format we can use"""
import json

def convert_coordinates(coordinates):
    """Convert real coordinates into map coordinates"""
    return [coordinates[2] * -0.5, coordinates[0] * 0.5]

if __name__ == "__main__":
    with open("input.json",encoding="utf-8") as f:
        inp = json.load(f)
    SPAWNER = "/pokearth/hisui/icons/pokeball.png"
    ALPHA_SPAWNER = "/pokearth/hisui/icons/alpha.png"
    DISTORTION_SPAWNER = "/pokearth/hisui/icons/distortion.png"
    accepted = [SPAWNER, ALPHA_SPAWNER, DISTORTION_SPAWNER]
    out = {}
    for i,item in enumerate(inp):
        item.pop("layer")
        item["coords"] = convert_coordinates(item["coords"])
        item["spawnerID"] = -1
        item["markerID"] = str(i)
        if item["icon"] == ALPHA_SPAWNER:
            item["ivs"] = 3
        else:
            item["ivs"] = 0
        if item["icon"] in accepted:
            out[i] = item
    with open("output.json","w+",encoding="utf-8") as f:
        json.dump(out,f,indent=2)
