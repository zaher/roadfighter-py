Run from this directory:

python3 main.py

Optional:

python3 main.py 3

The optional number is the starting stage, not the menu difficulty.

- 1 through 6 selects the first stage to play
- the in-game menu still shows only LEVEL A / LEVEL B / LEVEL C
- LEVEL A / B / C are the original game modes, separate from stage number

This bundle is self-contained. It uses the local copies of:

- roadfighter/
- graphics/
- sound/
- maps/
- fonts/

Replay toggles:

- ROADFIGHTER_RECORD_REPLAY=1 python3 main.py
- ROADFIGHTER_LOAD_REPLAY=1 python3 main.py
