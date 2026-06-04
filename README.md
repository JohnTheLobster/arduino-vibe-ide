# ⚡ Arduino Vibe IDE

AI-powered Arduino IDE MCP server and CLI wizard for hardware vibe coding.

**Version 0.2.1** — Multi-Board Support & Serial Plotter

[📖 Step-by-Step Setup Guide](SETUP.md) — *For beginners, no MCP knowledge needed*

## Features

- **MCP Server** — 53 tools for Arduino hardware control, sketch generation, and IDE integration
- **CLI Wizard** — Interactive setup with rich UI (click + rich)
- **IDE Plugin** — Install as MCP plugin for Claude Code, Cursor, and Codex
- **AgentCore Vibe Coding** — Natural language → sketch → compile → flash in one prompt
- **Template Library** — 6 pre-built AgentCore templates (weather, IoT, security, etc.)
- **Device Discovery** — USB serial + Bluetooth HC-05 scanning
- **Sketch Generation** — AI generates Arduino C++ code from natural language prompts
- **Project Management** — Create, save, backup, load projects
- **Serial Terminal** — Interactive serial communication
- **LED Control** — Runtime LED effects via serial commands (FastLED/SK6812)
- **Agent Bridge** — Live hardware feedback loop for iterative development
- **Hardware Inference** — Keyword-based hardware detection and wiring suggestions

## Quick Start

### CLI Mode

```bash
# Install package
pip install -e .

# Run setup wizard
arduino-vibe init

# Discover devices
arduino-vibe discover

# Generate a sketch
arduino-vibe sketch "LED controller with FastLED and SK6812"

# Compile and upload
arduino-vibe compile sketch.ino
arduino-vibe upload sketch.ino

# Open serial terminal
arduino-vibe terminal --device /dev/ttyACM0
```

### IDE Plugin Mode

```bash
# Install MCP server as IDE plugin
pip install -e .

# Run MCP server (stdio transport)
arduino-vibe-mcp

# Or use pre-built configs for Claude Code, Cursor, or Codex
# See ide-integration/ for installation instructions
```

**Example Claude Code Prompt:**
```
Create an Arduino sketch for a weather station with DHT22 temperature/humidity sensor and OLED display.
Use AgentCore architecture with sensor reading every 5 minutes.
Compile and flash to Arduino Nano.
```

## MCP Tools (53 Total)

### Hardware
- `list_devices` — Discover USB serial + Bluetooth devices
- `serial_terminal_open/close/read/write` — Serial communication
- `serial_send` — Send data over serial
- `serial_check_connection` — Verify serial link is alive
- `serial_reconnect` — Auto-reconnect to last known port
- `verify_board` — Verify connected board
- `check_modules` — Detect connected modules

### Serial Plotter
- `serial_plotter_open` — Start plotter on a serial port
- `serial_plotter_read` — Read and parse sensor data
- `serial_plotter_summary` — Get statistics (min/max/avg)
- `serial_plotter_close` — Close plotter session

### Configuration Profiles
- `profile_list` — List saved hardware profiles
- `profile_get` — Get profile details
- `profile_create` — Create a new profile
- `profile_update` — Update an existing profile
- `profile_delete` — Delete a profile
- `profile_set_active` — Set active profile
- `profile_get_active` — Get the active profile

### Sketch Generation
- `generate_sketch` — AI generates Arduino C++ from prompt
- `agent_sketch_builder` — NL prompt → AgentCore-enabled sketch
- `compile_sketch_tool` — Compile via arduino-cli
- `upload_sketch_tool` — Flash to board
- `upload_spiffs_tool` — Upload SPIFFS filesystem (ESP32/ESP8266)
- `upload_littlefs_tool` — Upload LittleFS filesystem (ESP32)

### AgentCore Vibe Coding
- `vibe_code` — One-shot NL prompt → sketch → compile → flash
- `vibe_code_iterative` — Interactive sketch refinement
- `vibe_code_template` — Template-based sketch generation
- `read_sensor_data` — Live sensor reading
- `set_leds` — Runtime LED control
- `set_servo` — Servo position control

### Templates
- `list_templates` — Browse 6 pre-built templates
- `search_templates` — Find templates by keyword
- `create_template_project` — Generate project from template

### Board Management
- `install_board_core` — Install board support (ESP32, ESP8266, RP2040)
- `board_manager_update` — Update board manager index
- `board_detect` — Detect connected board type
- `board_list` — List installed board cores

### Libraries
- `install_library_tool` — Install Arduino library
- `list_libraries_tool` — List installed libraries
- `search_library` — Search for libraries

### Projects
- `create_project` — Create new project
- `save_project` — Save project state
- `backup_project` — Full backup (tarball)
- `list_projects` — List saved projects
- `load_project` — Load a project

## Hardware

Supported boards:

| Family | Boards |
|---|---|
| **Arduino AVR** | Uno, Nano, Mega, Leonardo, Micro |
| **ESP32** | ESP32, ESP32 Dev, ESP32-S3 |
| **ESP8266** | ESP8266, NodeMCU |
| **RP2040** | Raspberry Pi Pico, Pico W |

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
├── CHANGELOG.md       # Version history
├── SETUP.md           # Step-by-step setup guide (for beginners)
├── config.yaml        # Default configuration
├── pyproject.toml     # Package metadata
├── examples/          # Example sketches (blink, sensor, WiFi, MQTT, PWM)
├── templates/         # Pre-built AgentCore templates
├── src/
│   ├── __init__.py    # Package init
│   ├── server.py      # MCP server (53 tools)
│   ├── cli.py         # CLI wizard (click + rich)
│   ├── agent_bridge.py             # AgentCore hardware bridge
│   ├── agent_sketch_builder.py     # NL → sketch generation
│   ├── config_profiles.py          # Hardware profile CRUD
│   ├── devices.py                  # Device discovery
│   ├── serial_plotter.py           # Serial plotter with stats
│   ├── serial_terminal.py          # Serial communication
│   ├── compiler.py                 # arduino-cli wrapper (multi-board)
│   ├── project.py                  # Project management
│   └── sketch_generator.py         # AI sketch templates
├── tests/             # Test suite (35 tests)
└── projects/          # User projects (auto-created)
```

## Dependencies

- Python 3.11+
- `mcp` 1.26.0 (MCP SDK)
- `click` 8.3.1, `rich` 14.3.3
- `pyserial` (serial communication)
- `arduino-cli` 1.5.0
- `bluetoothctl` 5.72 (for BT device scanning)
- `FastLED` 3.10.3 (Arduino library)
