# PLA-Live-Map
Flask application that displays live information on an interactive map for Pokemon Legends: Arceus.
![](./Map_Screenshot.png)

## PLA-Live-Map uses [sysbot-base](https://github.com/olliz0r/sys-botbase) to connect to the switch, and this must be installed on your console

# How to run:
1. Install requirements ``pip install -r requirements.txt``
2. Copy-paste ``config.json.template`` and rename to ``config.json``
3. Edit the ``IP`` field to contain your switch's IP
4. Run main.py ``python3 ./main.py``
5. Open ``http://localhost:8080/`` in your browser
6. Select your current map

# Troubleshooting
- What does ``FileNotFoundError: [Errno 2] No such file or directory: 'config.json'`` mean?
    - This error means the script could not find your config file in the directory its being run, make sure youre running the script from cmd in the project's directory, and that you've actually renamed ``config.json.template`` to ``config.json``.

- I'm getting ``ModuleNotFoundError: No module named 'requests'`` even though the pip install command runs fine!
    - Make sure that you do not have multiple python versions installed, and **DO NOT USE THE WINDOWS STORE PYTHON**. You can uninstall versions by searching "Uninstall" in your windows search bar and selecting "Add or remove program".
- Windows tells me ``Python was not found; run without arguments to install form the Microsoft Store...`` but I thought we didnt want windows store python?
    - Windows does this whenever it cant detect an already installed version and you try to use python, you can disable this by typing "Manage app execution aliases" in your windows search bar and deselecting python and python3.
- The script is telling me ``TimeoutError: timed out``, what does this mean?
    - This error is a general connection error, common causes include:
        - The ip in your config.json is not your switch's actual ip.
        - The switch is not connected to the same internet as your pc.
        - Your internet connection is failing.
- When I click on a marker I get ``binascii.Error: Odd-length string``
    - This error means that sysbot-base gave the script bad data, the cause of this is typically trying to read from memory (this happens when you click on a marker) while its already doing an action. Do not click any markers until the script is done doing whatever action its doing (you can see the progress in the terminal/cmd).
    - If this happens once, it may cause sysbot-base to get stuck, to fix this you can restart the script and your console.
- What does ``ConnectionAbortedError`` mean?
    - This error happens when something caused the connection to the switch to abruptly stop, make sure your switch and pc are still connected to the internet, and restart the script.
- Nothing is advancing correctly! or Every marker has the same generator seed! or The near shiny button makes a marker green but its way past the limit I have set?
    - If you've gotten to this point it means that your pc can connect to your switch, and that sysbot-base is able to send information to your pc. The most common causes of these issues are another program running on the switch that accesses memory. Make sure to not have programs like Edizon or CaptureSight running while you are trying to rng (Edizon might be accessing memory by default if its installed, so it may be best to uninstall it.)
    - Also make sure you do not have a mass outbreak active on your map if you are trying to rng a non mass outbreak, this will cause the group ids to be shifted and things will not advance properly.

# Current features
- Ability to read all active spawns with "Update Active Spawns" (Pokemon are displayed as a red pokeball)
- Ability to track and display the players current position on the map with "Track Player Position"
- Ability to teleport to any location on the map at the specified height on click with "Teleport"
- Ability to teleport to specific markers on the map with "Teleport to marker id X" in the marker pop-up
- Ability to read the spawner information and next shiny advance of known group ids and/or active pokemon
- Ability to read the current map's mass outbreak information
- Ability to read the pokemon that you are currently in battle with

# Credits
- berichan's [PLA Warper](https://github.com/berichan/PLAWarper) for the pointer to player location
- Serebii's [Pokearth](https://www.serebii.net/pokearth/hisui/) for the map images

# Licensed Software
- PLA-Live-Map uses [sidebar-v2](https://github.com/Turbo87/sidebar-v2) which is licensed under the [MIT License](./static/sidebar-v2/LICENSE)