# PLA-Live-Map
Flask application that displays live information on an interactive map for Pokemon Legends: Arceus.
![](./Map_Screenshot.png)

# How to run:
1. Install requirements ``pip install -r requirements.txt``
2. Copy-paste ``config.json.template`` and rename to ``config.json``
3. Edit the ``IP`` field to contain your switch's IP
4. Run main.py ``python3 ./main.py``
5. Open ``http://localhost:8080/`` in your browser
6. Select your current map

# Current features
- Ability to read all active spawns with "Update Active Spawns" (Pokemon are displayed as a red pokeball)
- Ability to track and display the players current position on the map with "Track Player Position"
- Ability to teleport to any location on the map at the specified height on click with "Teleport"
- Ability to teleport to specific markers on the map with "Teleport to marker id X" in the marker pop-up
- Ability to read the spawner information and next shiny advance of known group ids and/or active pokemon

# Credits
- berichan's [PLA Warper](https://github.com/berichan/PLAWarper) for the pointer to player location
- Serebii's [Pokearth](https://www.serebii.net/pokearth/hisui/) for the map images

# Licensed Software
- PLA-Live-Map uses [sidebar-v2](https://github.com/Turbo87/sidebar-v2) which is licensed under the [MIT License](./static/sidebar-v2/LICENSE)