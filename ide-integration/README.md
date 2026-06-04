# IDE Integration

This directory contains MCP configuration files for integrating Arduino Vibe IDE with various AI-powered IDEs and editors.

## Supported IDEs

| IDE | Config File | Transport |
|---|---|---|
| **Cursor** | `mcp-cursor.json` | stdio, HTTP, SSE |
| **Windsurf** | `mcp-windsurf.json` | stdio, HTTP, SSE |
| **Claude Code** | `mcp-claude.json` | stdio, HTTP |
| **Claude Desktop** | `mcp-claude.json` | stdio, HTTP |
| **Codex CLI** | `mcp-codex.json` | stdio, HTTP |
| **Cline** | `mcp-cursor.json` | stdio, HTTP |
| **VS Code + Copilot** | `mcp-cursor.json` | stdio, HTTP |
| **Zed** | `mcp-cursor.json` | stdio, HTTP |
| **Continue** | `mcp-cursor.json` | stdio, HTTP |
| **Goose** | `mcp-cursor.json` | stdio, HTTP |

## Universal Config

All tools that support **stdio transport** (which is all of them) use the same config:

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": [],
      "env": {
        "PYTHONPATH": "/home/john/projects/arduino-vibe-ide"
      }
    }
  }
}
```

Just paste this into whichever config file your tool uses.

## Installation

### Quick Setup

1. Install the package:
   ```bash
   pip install -e /home/john/projects/arduino-vibe-ide
   ```

2. Copy the config to your tool's MCP config location (see table above).

3. Restart your tool. The 53 MCP tools should be available.

### Manual Configuration

If your IDE requires a different format, add this to your MCP config:

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": [],
      "env": {
        "PYTHONPATH": "/home/john/projects/arduino-vibe-ide"
      }
    }
  }
}
```

## Available Tools

Once configured, you can use these tools in your IDE:

### Sketch Generation
- `generate_sketch` — Generate Arduino sketch from natural language prompt
- `agent_build_sketch` — Build AgentCore-enabled sketch from NL prompt
- `agent_compile_sketch` — Compile sketch to .hex file
- `agent_flash_sketch` — Flash compiled sketch to Arduino board
- `agent_build_and_flash` — Full pipeline: build → compile → flash

### Templates
- `list_templates_tool` — List pre-built AgentCore templates
- `get_template_tool` — Get specific template with code and wiring
- `search_templates_tool` — Search templates by keyword

### Device Management
- `list_devices` — Discover USB and Bluetooth Arduino devices
- `verify_board` — Verify board connection and type
- `check_modules` — Detect connected sensors and modules

### Serial Communication
- `serial_terminal_open` — Open serial terminal connection
- `serial_terminal_read` — Read data from serial terminal
- `serial_terminal_close` — Close serial terminal
- `serial_send` — Send data over serial port

### LED Control
- `set_leds` — Control LEDs via serial commands

### Compilation & Upload
- `compile_sketch_tool` — Compile sketch using arduino-cli
- `upload_sketch_tool` — Compile and upload to board

### Library Management
- `install_library_tool` — Install Arduino library
- `list_libraries_tool` — List installed libraries
- `search_library_tool` — Search library index

### Project Management
- `create_project` — Create new project
- `save_project` — Save project state
- `backup_project` — Create project backup
- `list_projects` — List all projects
- `load_project` — Load project details

### Agent Bridge (AgentCore Firmware)
- `agent_connect` — Connect to AgentCore device
- `agent_ping` — Ping device
- `agent_get_capabilities` — Query device capabilities
- `agent_read_sensor` — Read sensor by name
- `agent_read_all` — Read all sensors
- `agent_write_pin` — Write digital pin
- `agent_control_led` — Control LED
- `agent_control_servo` — Control servo
- `agent_get_state` — Get full device state
- `agent_subscribe` — Subscribe to sensor telemetry
- `agent_disconnect` — Disconnect from device

## Example Usage

### Claude Code Example
```bash
# Generate a sketch
claude code "Create an Arduino sketch that blinks an LED on pin 13"

# Using the MCP tools directly
claude code "Use generate_sketch to create a rainbow LED effect"

# Compile and upload
claude code "Use compile_sketch_tool to compile /home/john/projects/arduino/my-sketch.ino"
claude code "Use upload_sketch_tool to upload to /dev/ttyACM0"
```

### Cursor Example
In Cursor's chat or terminal:
```bash
# List devices
cursor "List available Arduino devices"

# Generate sketch
cursor "Generate a sketch for a temperature sensor with OLED display"

# Use AgentCore
cursor "Connect to AgentCore device at /dev/ttyACM0 and read all sensors"
```

### Codex Example
In Codex chat:
```bash
# Template usage
codex "Show me the weather station template"
codex "Get the weather-station template and compile it"

# Full vibe coding
codex "Build and flash a smart plant monitor using the smart-plant-monitor template"
```

## Troubleshooting

### Connection Issues
- Ensure `arduino-cli` is installed and accessible
- Check USB permissions: `sudo usermod -aG dialout $USER`
- Verify board is connected and port is accessible

### MCP Server Errors
- Check Python environment has required dependencies
- Verify `PYTHONPATH` includes project root
- Ensure `arduino-vibe-mcp` is in PATH

### Library Installation
- Run `arduino-cli core install arduino:avr` if cores are missing
- Check internet connection for library downloads

## Development

### Adding New Tools
1. Define tool in `src/server.py` using `@mcp.tool()` decorator
2. Test with Claude Code CLI
3. Update this README with new tool documentation

### Testing
```bash
# Test MCP server directly
arduino-vibe-mcp

# Test with Claude Code
claude code "List devices using arduino-vibe-ide MCP tools"
```
