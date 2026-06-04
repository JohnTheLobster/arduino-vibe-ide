# ⚡ Arduino Vibe IDE — Quick Setup Guide

> **For inexperienced users** — step by step, no prior MCP knowledge needed.

---

## What You're Building

A bridge between Claude Code (or any AI coding tool) and your Arduino board. You tell the AI what to build, it writes the code, compiles it, and flashes it to your board — all from the chat.

```
┌─────────────┐       ┌──────────────┐       ┌──────────────┐       ┌────────────┐
│ Claude Code │ ────▶ │  MCP Server  │ ────▶ │ arduino-cli  │ ────▶ │  Arduino   │
│   (the AI)  │ ◀──── │ (this bridge)│ ◀──── │ (the compiler)│ ◀──── │  (your board)│
└─────────────┘       └──────────────┘       └──────────────┘       └────────────┘
```

---

## Step 1: Prerequisites

### Install Arduino CLI

Arduino CLI is the compiler and flasher. It does all the heavy lifting.

**Linux:**
```bash
# Download
wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux64.tar.gz
tar -xvf arduino-cli_latest_Linux64.tar.gz
sudo mv arduino-cli /usr/local/bin/

# Initialize
arduino-cli config init

# Install board support (Arduino AVR boards — Uno, Nano, Mega)
arduino-cli core update-index
arduino-cli core install arduino:avr
```

**macOS:**
```bash
brew install arduino-cli
arduino-cli core update-index
arduino-cli core install arduino:avr
```

**Windows:**
```bash
winget install Arduino.arduino-cli
arduino-cli core update-index
arduino-cli core install arduino:avr
```

### Install Python 3.11+

```bash
python3 --version
# Should show 3.11 or higher
```

---

## Step 2: Install Arduino Vibe IDE

```bash
# Clone the repository
git clone https://github.com/JohnTheLobster/arduino-vibe-ide.git
cd arduino-vibe-ide

# Install the package
pip install -e .
```

This installs two commands:
- `arduino-vibe` — CLI tool (discover devices, compile, upload, etc.)
- `arduino-vibe-mcp` — MCP server (the bridge for AI tools)

---

## Step 3: Connect Your Arduino

1. **Plug your Arduino into USB**
2. **Find the port:**

```bash
# Auto-discover connected boards
arduino-vibe discover
```

Example output:
```
┌──────────────────────────────────────────────┐
│              🔍 Device Discovery             │
└──────────────────────────────────────────────┘

┌───┬──────────────────┬──────┬──────────┬────────────────┬─────────┬────────┐
│ # │ ID               │ Type │ Name     │ Path           │ Board   │ Status │
├───┼──────────────────┼──────┼──────────┼────────────────┼─────────┼────────┤
│ 1 │ usb-arduino-nano │ 🔌 USB │ Arduino │ /dev/ttyACM0   │ arduino │ ✅    │
└───┴──────────────────┴──────┴──────────┴────────────────┴─────────┴────────┘
```

Note the **Path** (e.g. `/dev/ttyACM0`). That's your board's USB port.

---

## Step 4: Install Board Support (if needed)

The package supports these boards out of the box:

| Board Family | Boards | Install Command |
|---|---|---|
| **Arduino AVR** | Uno, Nano, Mega, Leonardo, Micro | `arduino-cli core install arduino:avr` |
| **ESP32** | ESP32, ESP32 Dev, ESP32-S3 | `arduino-cli core install esp32:esp32` |
| **ESP8266** | ESP8266, NodeMCU | `arduino-cli core install esp8266:esp8266` |
| **RP2040** | Raspberry Pi Pico, Pico W | `arduino-cli core install rp2040:rp2040` |

Install the one that matches your board. ESP32/ESP8266/RP2040 need the first run:

```bash
# ESP32 example
arduino-cli core update-index --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32
```

---

## Step 5: Run the MCP Server

Open a terminal and start the server:

```bash
cd ~/arduino-vibe-ide
arduino-vibe-mcp
```

That's it. The server runs and waits for connections. Leave this terminal open.

The server uses **stdio transport** (standard input/output), which is the simplest connection method — no ports, no networking.

---

## Step 6: Connect Your AI Coding Tool

The MCP server uses **stdio transport** (stdin/stdout). This is the most universal method — supported by every major AI coding tool.

### Cursor

Open **Cursor Settings → MCP Servers** (or edit `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

Restart Cursor. You'll see "arduino-vibe-ide" in your MCP tools list.

### Windsurf (Codeium)

Open **Windsurf Settings → MCP** (or edit `~/.codeium/mcp.json`):

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

### Claude Code

Edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

### Claude Desktop

Edit `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

### VS Code + GitHub Copilot

Create `.github/copilot.mcp.json` in your project (or add to your user MCP config):

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

### Codex CLI

Edit `~/.codex/mcp.json`:

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

### Cline (VS Code Extension)

Open **Cline → MCP Servers** and add:

- **Command:** `arduino-vibe-mcp`
- **Args:** (leave empty)

### Zed Editor

Add to `~/.config/zed/settings.json`:

```json
{
  "mcp_servers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

### Continue (VS Code / JetBrains Extension)

Add to `.continue/config.json`:

```json
{
  "mcpServers": {
    "arduino-vibe-ide": {
      "command": "arduino-vibe-mcp",
      "args": []
    }
  }
}
```

### ChatGPT (Plus/Pro)

ChatGPT uses **remote HTTP transport**, so you need the server running with an HTTP endpoint. Start with:

```bash
arduino-vibe-mcp --transport http --port 8601
```

Then in ChatGPT: **Settings → Connectors → Add Custom** → point to `http://localhost:8601/mcp`

---

## All Compatible Tools

| Tool | Transport | How Popular |
|---|---|---|
| **Cursor** | stdio, HTTP, SSE | ⭐ Most popular AI IDE |
| **Claude Code** | stdio, HTTP | ⭐ Anthropic's CLI |
| **Windsurf** | stdio, HTTP, SSE | ⭐ Growing fast (VS Code fork) |
| **VS Code + Copilot** | stdio, HTTP | ⭐ Built into VS Code |
| **Cline** | stdio, HTTP | Popular VS Code extension |
| **Zed** | stdio, HTTP | Fast editor, gaining traction |
| **Continue** | stdio, HTTP | Open-source, VS Code / JetBrains |
| **Goose** | stdio, HTTP | Block's AI coding tool |
| **Codex** | stdio, HTTP | OpenAI's CLI |
| **ChatGPT** | HTTP only | Remote only, needs HTTP transport |

**All tools that support stdio** just need the config above — one command, no ports, no networking.

---

## Step 7: Start Vibe Coding

Open Claude Code and start chatting:

### Example Conversations

**Basic:**
> "Make an LED blink on my Arduino"

Claude Code will:
1. Generate the sketch
2. Compile it
3. Upload it to your board

**Advanced:**
> "Create a temperature sensor dashboard that reads from an DS18B20 sensor on pin 2 and prints the temperature every second"

> "Build a WiFi web server on my ESP32 that toggles an LED on pin 15"

> "Read analog data from pin A0 and send it in serial plotter format"

### What Claude Code Can Do

| Action | Example Prompt |
|---|---|
| Generate code | "Make a motor controller with PWM on pin 3" |
| Compile | "Compile this sketch" |
| Upload | "Flash the sketch to my board" |
| One-shot build | "Build and flash: RGB LED rainbow animation" |
| Serial terminal | "Open serial monitor at 115200 baud" |
| Serial plotter | "Start the plotter on /dev/ttyACM0" |
| Save profiles | "Save this setup as 'my-workshop'" |
| List libraries | "Show me installed Arduino libraries" |
| Install library | "Install the DHT sensor library" |

---

## Troubleshooting

### "Board not found"
```bash
# Check if the board is connected
ls /dev/ttyACM* /dev/ttyUSB*

# Linux: add user to dialout group
sudo usermod -aG dialout $USER
```

### "Permission denied" on serial port
```bash
# Linux
sudo chmod 666 /dev/ttyACM0  # quick fix
# or add user to dialout group (persistent)
sudo usermod -aG dialout $USER
```

### "arduino-cli not found"
```bash
arduino-cli version
# Install if missing (see Step 1)
```

### "Port already in use"
Close other tools using the serial port (Arduino IDE, serial monitors, etc.)

### ESP32 upload fails
1. Put ESP32 in **bootloader mode** (hold BOOT button while pressing RESET)
2. Try again

---

## Quick Reference

```bash
# Start the MCP server (leave running)
arduino-vibe-mcp

# Discover connected boards
arduino-vibe discover

# Compile a sketch
arduino-vibe compile sketch.ino --fqbn arduino:avr:nano

# Upload a sketch
arduino-vibe upload sketch.ino

# Open serial terminal
arduino-vibe terminal --device /dev/ttyACM0

# Install a library
arduino-vibe library FastLED
```

---

That's it. You're ready to vibe code hardware! 🎉
