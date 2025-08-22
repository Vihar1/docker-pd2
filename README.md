# Project Diablo 2 Docker Container

This Docker container provides a complete environment for running Project Diablo 2 with VNC remote access, memory monitoring, and MCP server integration for AI assistance.

## Features

- **Headless Gaming**: Runs Project Diablo 2 in a virtual X11 display
- **Remote Access**: VNC server for remote desktop connection
- **AI Integration**: MCP server for Claude Desktop integration
- **Memory Monitoring**: Real-time game state monitoring
- **Custom Resolution**: Optimized 1068x600 resolution for container environment
- **3dfx Support**: Enhanced graphics rendering with 3dfx emulation

## Prerequisites

- Docker and Docker Compose installed
- Project Diablo 2 game files in `pd2/` directory
- VNC client (optional, for remote access)

## Quick Start

1. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

2. **Connect via VNC:**
   - Host: `localhost`
   - Port: `5901`
   - No password required

3. **Access services:**
   - VNC: `localhost:5901`
   - MCP Server: `localhost:8765`
   - Health Check: `localhost:3000`

## Directory Structure

```
Diablo2/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
├── README.md               # This documentation file
├── INSTALL.md              # Installation and setup guide
├── start_diablo2.sh        # Main startup script (executable)
├── diablo2_monitor.py      # Memory monitoring service
├── diablo2_mcp_server.py   # MCP server for AI integration
├── screenshots/            # Directory for game screenshots
├── memory_dumps/           # Directory for memory analysis dumps
└── pd2/                    # Project Diablo 2 game files (user provided)
    ├── Base Game Files (Root Level):
    ├── D2.LNG              # Language file
    ├── d2char.mpq          # Base character data
    ├── d2data.mpq          # Base game data
    ├── d2exp.mpq           # Expansion pack data
    ├── d2music.mpq         # Base music files
    ├── d2sfx.mpq           # Base sound effects
    ├── d2speech.mpq        # Base voice files
    ├── d2video.mpq         # Base video files
    ├── D2xMusic.mpq        # Expansion music
    ├── d2xtalk.mpq         # Expansion voice files
    ├── D2xVideo.mpq        # Expansion videos
    ├── Patch_D2.mpq        # Base game patches
    ├── Save/               # Save Directory
    │
    └── ProjectD2/          # Project D2 mod directory
        ├── Executables:
        ├── Game.exe        # Main game executable
        ├── Diablo II.exe   # Original Diablo 2 executable
        ├── PD2Launcher.exe # Project D2 launcher
        ├── D2VidTst.exe    # Video test utility
        │
        ├── Core Game Libraries:
        ├── D2Client.dll    # Client library
        ├── D2Common.dll    # Common game functions
        ├── D2Game.dll      # Core game library
        ├── D2gfx.dll       # Graphics library
        ├── D2Lang.dll      # Language support
        ├── D2Launch.dll    # Game launcher
        ├── D2Net.dll       # Network functionality
        ├── D2sound.dll     # Audio system
        ├── D2Win.dll       # Windows interface
        ├── D2CMP.dll       # Compression library
        ├── D2Multi.dll     # Multiplayer support
        ├── D2MCPClient.dll # Battle.net client
        ├── Fog.dll         # Blizzard utility library
        ├── Storm.dll       # Blizzard core library
        │
        ├── Graphics & Display:
        ├── D2DDraw.dll     # DirectDraw wrapper
        ├── D2Direct3D.dll  # Direct3D wrapper
        ├── D2Gdi.dll       # GDI graphics
        ├── D2Glide.dll     # 3dfx Glide wrapper
        ├── D2HD.dll        # HD graphics support
        ├── ddraw.dll       # DirectDraw implementation
        ├── glide3x.dll     # 3dfx Glide library
        ├── SGD2FreeRes.dll # Resolution mod library
        ├── SGD2FreeDisplayFix.dll # Display fix library
        │
        ├── Media & Codec Libraries:
        ├── binkw32.dll     # Bink video codec
        ├── SmackW32.dll    # Smacker video codec
        ├── ijl11.dll       # Intel JPEG library
        ├── sciter.dll      # HTML/CSS engine
        ├── WebView2Loader.dll # Modern web integration
        ├── libcrypto-1_1.dll # Cryptography library
        │
        ├── Project D2 Mods:
        ├── ProjectDiablo.dll # Main Project D2 modifications
        ├── PD2_EXT.dll     # Project D2 extensions
        ├── BH.dll          # BH maphack integration
        ├── Bnclient.dll    # Battle.net client mod
        ├── StormLib.dll    # MPQ archive library
        │
        ├── Game Data Archives:
        ├── d2gl.mpq        # D2GL graphics mod
        ├── D2MultiRes.mpq  # Multi-resolution support
        ├── patch_d2.mpq    # Game patches
        ├── pd2assets.mpq   # Project D2 assets
        ├── pd2data.mpq     # Project D2 data
        ├── pd2maps.mpq     # Project D2 maps
        ├── SGD2FreeRes.mpq # Resolution mod data
        ├── SlashDiabloHD.mpq # HD graphics pack
        ├── ver-IX86-1.mpq  # Version-specific data
        │
        ├── Configuration Files:
        ├── BH.json         # BH maphack settings
        ├── BH.json.bak     # BH settings backup
        ├── d2gl.json       # D2GL graphics settings
        ├── d2gl.yaml       # D2GL YAML config
        ├── ddraw.ini       # DirectDraw settings
        ├── D2HD.ini        # HD graphics settings
        ├── default.filter  # Default item filter
        ├── loot.filter     # Loot filter settings
        ├── local_metadata.json # File integrity checksums
        ├── ProjectDiablo.cfg # Project D2 configuration
        ├── ProjectDiablo.json # Project D2 JSON config
        ├── ProjectDiablo.json.bak # Config backup
        ├── SGD2FreeResolution.json # Resolution settings
        ├── SGD2FreeRes.json # Resolution config
        └── UI.ini          # UI positioning configuration
```

## File Categories

### Essential Game Files

**Base Diablo 2 Installation** (in `pd2/`):

- `*.mpq` files - Original game data archives
- `D2.LNG` - Language support file

**Project D2 Mod** (in `pd2/ProjectD2/`):

- `Game.exe` - Modified game executable
- `D2*.dll` - Core game libraries
- `ProjectDiablo.dll` - Main mod functionality
- Modified `*.mpq` files - Mod-specific content

### Enhancement Files

- `BH.dll` - BH maphack integration
- `SGD2FreeRes.mpq` + `SGD2FreeResolution.json` - Resolution mod
- `WebView2Loader.dll` - Modern web integration

### Configuration Files

- `UI.ini` - Interface positioning
- `SGD2FreeResolution.json` - Display settings

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WINEPREFIX` | `/root/.wine` | Wine installation directory |
| `WINEARCH` | `win32` | Wine architecture (32-bit) |
| `WINEDEBUG` | `-all` | Disable Wine debug messages |
| `DISPLAY` | `:1` | X11 display number |

## Ports

| Port | Service | Description |
|------|---------|-------------|
| 5901 | VNC | Remote desktop access |
| 8080 | Web VNC | Optional web-based VNC |
| 3000 | Health Check | Container health endpoint |
| 8765 | MCP Server | AI integration endpoint |

## Game Launch Parameters

The game is launched with the following parameters:

```bash
wine Game.exe -ns -3dfx
```

- **`-ns`**: No splash screen
- **`-3dfx`**: Enable 3dfx graphics acceleration

## Desktop Integration

The container creates desktop shortcuts and menu entries:

- **Desktop Shortcut**: `/root/Desktop/Diablo2.desktop`
- **Fluxbox Menu**: Right-click desktop to access game launcher
- **Applications Menu**: Available in `/root/.local/share/applications/`

## Troubleshooting

### Common Issues

1. **Game won't start:**
   - Check if game files exist in `pd2/ProjectD2/`
   - Verify Wine initialization completed successfully
   - Check container logs for error messages

2. **VNC connection failed:**
   - Ensure port 5901 is not blocked by firewall
   - Try connecting to `0.0.0.0:5901` instead of `localhost:5901`

3. **Resolution issues:**
   - Modify `SGD2FreeResolution.json` for different resolutions
   - Adjust Xvfb resolution in `start_diablo2.sh`

4. **Performance issues:**
   - Try different Wine D3D renderer settings
   - Adjust container resource limits in docker-compose.yml

### Debug Commands

Access the running container:

```bash
docker exec -it diablo2_container /bin/bash
```

Check running processes:

```bash
docker exec diablo2_container ps aux
```

View logs:

```bash
docker-compose logs diablo2
```

## Development

### Adding New Features

1. **Memory Monitoring**: Extend `diablo2_monitor.py`
2. **MCP Server**: Modify `diablo2_mcp_server.py`
3. **Game Configuration**: Update config files in `pd2/ProjectD2/`

### Custom Resolutions

To use different resolutions:

1. Update `SGD2FreeResolution.json`:

   ```json
   "Ingame Resolutions": ["1920x1080"]
   ```

2. Modify Xvfb in `start_diablo2.sh`:

   ```bash
   Xvfb $DISPLAY -screen 0 1920x1080x16 &
   ```

## Security Notes

- VNC server runs without password (suitable for local development only)
- Container runs as root (consider non-root user for production)
- All ports are exposed (restrict in production environments)

## License

This container setup is for educational and development purposes. Ensure you own legitimate copies of all game files.
