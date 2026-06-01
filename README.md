# ⚡ Arduino Vibe IDE

AI-powered Arduino IDE MCP server and CLI wizard for hardware vibe coding.

## Features

- **MCP Server** — 15+ tools for Arduino hardware control
- **CLI Wizard** — Interactive setup with rich UI (click + rich)
- **Device Discovery** — USB serial + Bluetooth HC-05 scanning
- **Sketch Generation** — Template-based Arduino C++ code generation
- **Project Management** — Create, save, backup, load projects
- **Serial Terminal** — Interactive serial communication
- **LED Control** — Runtime LED effects via serial commands (FastLED/SK6812)
- **IR Remote** — IR receive/send with code storage
- **Sensor Support** — DHT, BMP, BME, I2C device detection

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python src/cli.py init

# Discover devices
python src/cli.py discover

# Generate a sketch
python src/cli.py sketch "LED controller with FastLED and SK6812"

# Compile and upload
python src/cli.py compile sketch.ino
python src/cli.py upload sketch.ino

# Open serial terminal
python src/cli.py terminal --device /dev/ttyACM0

# MCP server
python src/server.py
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_devices` | Discover USB serial + Bluetooth devices |
| `serial_terminal_open` | Open serial port |
| `serial_terminal_read` | Read from serial |
| `serial_terminal_close` | Close serial port |
| `serial_send` | Send data over serial |
| `generate_sketch` | AI generates Arduino C++ from prompt |
| `compile_sketch_tool` | Compile via arduino-cli |
| `upload_sketch_tool` | Flash to board |
| `install_library_tool` | Install Arduino library |
| `list_libraries_tool` | List installed libraries |
| `create_project` | Create new project |
| `save_project` | Save project state |
| `backup_project` | Full backup (tarball) |
| `list_projects` | List saved projects |
| `load_project` | Load a project |
| `set_leds` | Runtime LED control |
| `verify_board` | Verify connected board |
| `check_modules` | Detect connected modules |

## Hardware

Default configuration:
- **Board:** Arduino Nano (clone)
- **Bluetooth:** HC-05 (RXD→D11, TXD→D10, MAC: 98:DA:50:01:E2:CF)
- **LEDs:** SK6812 3-pin (Data→D6), 288 LEDs, FastLED
- **BT PIN:** 1234

## LED Commands

The generated sketches support runtime LED control via serial:

- `LED <index> <R> <G> <B>` — Set individual LED
- `ALL <R> <G> <B>` — Set all LEDs
- `BRIGHT <0-255>` — Set brightness
- `EFFECT <name>` — Set animation (solid, rainbow, pulse, fire, wave, running, random, chase)
- `SPEED <1-255>` — Set animation speed
- `COLOR <R> <G> <B>` — Set base color for effects

## Project Structure

```
arduino-vibe-ide/
├── config.yaml          # Default configuration
├── pyproject.toml       # Package metadata
├── requirements.txt     # Dependencies
├── src/
│   ├── __init__.py      # Package init
│   ├── server.py        # MCP server (15+ tools)
│   ├── cli.py           # CLI wizard (click + rich)
│   ├── devices.py       # Device discovery
│   ├── serial_terminal.py  # Serial communication
│   ├── compiler.py      # arduino-cli wrapper
│   ├── project.py       # Project management
│   └── sketch_generator.py  # AI sketch templates
└── projects/            # User projects (auto-created)
```

## Dependencies

- Python 3.11+
- `mcp` 1.26.0 (MCP SDK)
- `click` 8.3.1, `rich` 14.3.3
- `pyserial` (serial communication)
- `arduino-cli` 1.5.0
- `bluetoothctl` 5.72 (for BT device scanning)
- `FastLED` 3.10.3 (Arduino library)
