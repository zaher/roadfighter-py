## Road Fighter

A game based on the open-source version of [Road Fighter](https://ecsoft2.org/road-fighter), initially ported to Python 3/SDL using GPT-4.1 by my friend (thanks to my friend for porting it).

## Features

Features added after porting to Python

- Full-screen support
- Joystick support for 2 players (auto-detect)
- Configuration saved in INI format
- Add Horn sound effect
- Optimized graphics and convert from BMP to PNG
- Hidden cursor while playing
- Sparkles when crash
- Any player who starts a single game takes control
- Save screenshot Ctrl+P (C:\Users\%username%\.roadfighter\)

## Installation

This bundle is self-contained. It uses local copies of:

- `source/` - Game source code
- `graphics/` - Game graphics (PNG format)
- `sound/` - Sound effects and music
- `maps/` - Level maps
- `fonts/` - Game fonts
- `controller/` - Joystick button mappings

## Usage

Run the game from the project directory:

```bash
python main.py
```

### Command-Line Arguments

```
usage: main.py [-h] [--level {a,b,c}] [--record-replay] [--load-replay] [LEVEL]

Road Fighter - A retro remake of the classic Konami racing game

positional arguments:
  LEVEL                 Starting level number (1-6). Higher levels are more
                        difficult with more traffic. (default: 1)

options:
  -h, --help            Show this help message and exit
  --level {a,b,c}, -l {a,b,c}
                        Game mode/level type:
                          a = Normal mode
                          b = More traffic
                          c = Night driving
                        If not specified, you will select from the menu.
  --record-replay       Record all keyboard inputs to replay.txt for later
                        playback. The replay includes the random seed, so the
                        same game can be replayed exactly.
  --load-replay         Load and play back a previously recorded replay from
                        replay.txt. The game will run automatically using the
                        recorded inputs.
```

### Examples

```bash
# Start at level 1, select mode from menu
python main.py

# Start at level 3
python main.py 3

# Start level 1 in mode B (more traffic)
python main.py -l b

# Start at level 5 in mode C (night driving)
python main.py --level c 5

# Record gameplay to replay.txt
python main.py --record-replay

# Play back replay from replay.txt
python main.py --load-replay

# Combine options: start at level 2, mode A, and record
python main.py --level a --record-replay 2
```

### Notes

- **Level Number (1-6)**: Selects the starting stage. Higher levels are more difficult with increased traffic.
- **Level Type (A/B/C)**: These are the original game modes:
  - **LEVEL A**: Normal mode - standard gameplay
  - **LEVEL B**: More traffic - increased enemy vehicles
  - **LEVEL C**: Night driving - darker visuals with headlights

The level number and level type are independent settings. The in-game menu always shows LEVEL A/B/C, but you can skip directly to any stage (1-6) using the command line.

### Controls

#### Player 1 (Default)
- **Arrow Keys**: Move car
- **Space**: Fire / Turbo

#### Player 2 (Default)
- **WASD**: Move car
- **Tab**: Fire / Turbo

Joysticks are automatically detected and mapped to player controls.

### Keys

- **Enter**: Select
- **Alt + Enter**: Toggle full-screen mode
- **F12**: Quit the game
- **Ctrl + P**: Save a screenshot to the userdata screenshots folder

### Replay System

The replay system records all keyboard inputs along with the random seed, allowing you to replay the exact same game session.

1. **Record a replay**:
   ```bash
   python main.py --record-replay
   ```
   The replay is saved to `replay.txt` in the userdata directory.

2. **Play back a replay**:
   ```bash
   python main.py --load-replay
   ```
   The game will automatically play using the recorded inputs.

## License

GNU General Public License (GPL)

This is a remake of the original Road Fighter by Konami. The original code was open-sourced and has been ported to modern Python/SDL.

## Done

- Joystick & GameController support (2 players, auto-detect, custom mappings via `gamecontrollerdb.txt`)
- Keyboard and joystick are active by default from the first run
- Configuration & key bindings saved in INI format (human-readable key names)
- Menu improvements: glowing selected item, arrow positioning, full-screen toggle, removed redundant Extras option
- Graphics optimizations: converted BMP to PNG, SDL2-based rotation/scaling, shader effects, glowing text, hidden cursor during race
- Sound effects: looping car engine with pitch shifting, optimized skid sounds, horn on Select button
- Visual effects: explosion particles (yellow, orange, red fire), skid wheel marks (lag-optimized)
- Replay system: record/load replays from command line (`--record-replay`, `--load-replay`)
- Command-line options: level number (1-6), level type (`-l a/b/c`), debug mode (`--debug`)
- Input fixes: proper Fire key mapping, Up/Down/Back navigation, hat motion support
- Configurable fuel factor via config file
- General performance improvements and bug fixes

## Resources

[Horn sound](https://cdn.pixabay.com/download/audio/2023/06/11/audio_1777c08c36.mp3?filename=universfield-automobile-horn-153260.mp3)