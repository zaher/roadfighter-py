## Road Fighter ##

A Game based on opensource version of [Road Fighter](https://ecsoft2.org/road-fighter), ported to Python 3/SDL using `gpt 5.4-high` by my friend (thanks for my firend for porting it)

### Features ###

* Full screen support
* 2-player local split-screen
* **P2P Network Multiplayer** (NEW!)
* Joystick support for 2 players

### Running the Game ###

Run from this directory:

```bash
python3 main.py
```

Optional:

```bash
python3 main.py 3
```

The optional number is the starting stage, not the menu difficulty.
- 1 through 6 selects the first stage to play
- the in-game menu still shows only LEVEL A / LEVEL B / LEVEL C
- LEVEL A / B / C are the original game modes, separate from stage number

### Network Multiplayer ###

Play with a friend over LAN or Internet!

#### How to Play Online:

1. **Start the game**: `python3 main.py`
2. **Select "NETWORK GAME"** from the main menu
3. **Choose your role**:
   - **HOST**: Creates a game and waits for opponent
   - **JOIN**: Connects to a host's game

4. **If HOSTING**:
   - Choose port (default: 5555)
   - Your local IP will be displayed
   - Share your IP with your friend
   - Wait for them to connect

5. **If JOINING**:
   - Enter the host's IP address
   - Enter the port (default: 5555)
   - Click CONNECT

6. **Play!** Once connected, the game starts automatically

#### Network Requirements:

- **LAN**: Works automatically on the same network
- **Internet**: 
  - Host needs port forwarding enabled on their router (port 5555 UDP by default)
  - OR use a VPN like Hamachi, Radmin, or ZeroTier for virtual LAN

#### Technical Details:

- Uses UDP P2P (peer-to-peer) networking
- Input-based lockstep synchronization
- Automatic latency compensation (10-frame buffer)
- Connection timeout: 10 seconds
- Ping measurement for latency display

### Controls ###

**Player 1** (Arrow keys):
- Left/Right: Steer
- Up: Accelerate
- Down: Brake
- Space: Fire/Turbo

**Player 2** (WASD):
- A/D: Steer
- W: Accelerate
- S: Brake
- Left Shift: Fire/Turbo

**General**:
- F12: Quit game
- Alt+Enter: Toggle fullscreen
- F1: Pause

### File Structure ###

This bundle is self-contained. It uses the local copies of:
- `source/` - Game source code
- `graphics/` - Game sprites and images
- `sound/` - Audio files
- `maps/` - Level files
- `fonts/` - Font files

### Replay System ###

Record and playback your gameplay:

```bash
# Record a replay
ROADFIGHTER_RECORD_REPLAY=1 python3 main.py

# Load a replay
ROADFIGHTER_LOAD_REPLAY=1 python3 main.py
```

### Development ###

#### Network Module Structure:

```
source/network/
├── __init__.py           - Module exports
├── p2p.py               - P2P UDP networking
├── protocol.py          - Message serialization
└── input_buffer.py      - Lag compensation
```

#### Testing Network:

```bash
python test_network.py
```

### Troubleshooting ###

**Connection Issues**:
- Make sure both players are using the same port
- Check firewall settings (allow Python UDP traffic)
- For Internet play, ensure port forwarding is enabled
- Try using a VPN if port forwarding isn't possible

**Lag/Desync**:
- Network uses 10-frame input buffer for smooth gameplay
- High latency (>200ms) may cause delayed opponent movement
- Game will pause if connection is lost

### License ###

See LICENSE file for details.
