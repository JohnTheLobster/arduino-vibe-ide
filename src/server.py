"""
Arduino Vibe IDE MCP Server.

MCP server exposing Arduino hardware control tools.
Supports USB serial, Bluetooth, compilation, upload, and project management.
"""

import os
import sys
from pathlib import Path

# Add src to path
_src_dir = Path(__file__).parent
sys.path.insert(0, str(_src_dir))
# Add project root to path for templates import
sys.path.insert(0, str(_src_dir.parent))

from mcp.server.fastmcp import FastMCP

from devices import discover_devices_json, check_modules as _check_modules
from serial_terminal import SerialTerminal, send_serial
from serial_plotter import SerialPlotter
from compiler import (
    compile_sketch, upload_sketch, install_library, list_libraries,
    search_library, verify_board as _verify_board, board_manager_update,
    upload_spiffs, upload_littlefs,
    install_board_core,
)
from bluetooth_upload import (
    pair_bluetooth_device, setup_rfcomm, release_rfcomm,
    connect_bluetooth_for_upload, disconnect_bluetooth,
    trigger_bootloader_reset, list_rfcomm_connections,
    BluetoothUploadConfig,
)
from project import ArduinoProject
from sketch_generator import (
    generate_sketch_from_prompt, build_led_command, LED_PRESET_COLORS,
    build_led_prompt, build_ir_prompt, build_sensor_prompt,
    build_servo_prompt, build_generic_prompt, build_bt_bridge_prompt,
)
from agent_bridge import AgentBridge, register_agent_tools
from agent_sketch_builder import (
    register_sketch_builder_tools, build_sketch_from_prompt,
    infer_hardware, HardwareSpec,
)
import templates
from config_profiles import register_profile_tools

# Server instance
mcp = FastMCP(
    name="arduino-vibe-ide",
    instructions="AI-powered Arduino IDE MCP server for vibe coding hardware projects",
)

# Global instances
_serial_terminal = SerialTerminal()
_project_manager = ArduinoProject()
_agent_bridge = AgentBridge()
_plotter = SerialPlotter()

# Register sketch builder tools (agent_build_sketch, agent_compile_sketch, agent_flash_sketch, agent_build_and_flash)
register_sketch_builder_tools(mcp)


# ─── Device Discovery ─────────────────────────────────────────────

@mcp.tool()
def list_devices() -> dict:
    """
    Discover all Arduino-compatible devices.
    Scans USB serial ports (/dev/ttyACM*, /dev/ttyUSB*) and Bluetooth devices.

    Returns:
        Dict with device list, counts, and metadata for each device.
    """
    result = discover_devices_json()
    return result


@mcp.tool(name="verify_board")
def verify_board_tool(port: str = "", fqbn: str = "") -> dict:
    """
    Verify a connected Arduino board.
    Detects board type, firmware, and connection status.

    Args:
        port: Serial port path (e.g., /dev/ttyACM0). Auto-detect if empty.
        fqbn: Board FQBN to verify against (e.g., arduino:avr:nano).

    Returns:
        Board verification status with details.
    """
    return _verify_board(port=port, fqbn=fqbn)


@mcp.tool(name="check_modules")
def check_modules_tool(device_path: str) -> dict:
    """
    Detect connected modules (HC-05, sensors, etc.) via serial probing.
    Sends AT commands and scans for I2C devices.

    Args:
        device_path: Serial port path to probe.

    Returns:
        Dict with detected modules and their details.
    """
    return _check_modules(device_path)


# ─── Serial Communication ─────────────────────────────────────────

@mcp.tool()
def serial_terminal_open(path: str, baudrate: int = 115200) -> dict:
    """
    Open a serial terminal connection.

    Args:
        path: Device path (/dev/ttyACM0, /dev/ttyUSB0, rfcomm:MAC)
        baudrate: Baud rate (default 115200)

    Returns:
        Connection status with port info.
    """
    global _serial_terminal
    _serial_terminal = SerialTerminal()
    return _serial_terminal.open(path, baudrate)


@mcp.tool()
def serial_terminal_read(size: int = 1024) -> dict:
    """
    Read data from the open serial terminal.

    Args:
        size: Maximum bytes to read (default 1024)

    Returns:
        Received data and buffer status.
    """
    return _serial_terminal.read(size)


@mcp.tool()
def serial_terminal_close() -> dict:
    """
    Close the serial terminal connection.

    Returns:
        Disconnection status.
    """
    global _serial_terminal
    result = _serial_terminal.close()
    _serial_terminal = SerialTerminal()
    return result


@mcp.tool()
def serial_send(path: str, data: str, baudrate: int = 115200) -> dict:
    """
    Send data over serial port (stateless: opens, sends, closes).

    Args:
        path: Serial port path
        data: Data string to send
        baudrate: Baud rate (default 115200)

    Returns:
        Send status with bytes transmitted.
    """
    return send_serial(path, data, baudrate)


@mcp.tool()
def serial_check_connection() -> dict:
    """Check if the serial connection is still alive."""
    return _serial_terminal.check_connection()


@mcp.tool()
def serial_reconnect() -> dict:
    """Attempt to reconnect to the last known serial port."""
    return _serial_terminal.reconnect()


# ─── Serial Plotter ───────────────────────────────────────────────

@mcp.tool()
def serial_plotter_open(path: str, baudrate: int = 115200) -> dict:
    """Open a serial plotter. Reads numeric data from serial and parses it for plotting. Supports comma/tab/space separated values."""
    global _plotter
    _plotter = SerialPlotter()
    return _plotter.open(path, baudrate)


@mcp.tool()
def serial_plotter_read(count: int = 50) -> dict:
    """Read latest data from the serial plotter with timestamps, values, and statistics."""
    return _plotter.read_latest(count)


@mcp.tool()
def serial_plotter_summary() -> dict:
    """Get statistics summary from the serial plotter. Returns min/max/avg/latest for each channel."""
    return _plotter.get_summary()


@mcp.tool()
def serial_plotter_close() -> dict:
    """Close the serial plotter connection."""
    global _plotter
    result = _plotter.close()
    _plotter = SerialPlotter()
    return result


# ─── LED Control ──────────────────────────────────────────────────

@mcp.tool()
def set_leds(
    command: str = "ALL",
    path: str = "",
    baudrate: int = 115200,
    led_index: int = -1,
    red: int = 255,
    green: int = 255,
    blue: int = 255,
    brightness: int = -1,
    effect: str = "",
    speed: int = -1,
    color_name: str = "",
) -> dict:
    """
    Control LEDs on connected Arduino via serial command.
    Supports FastLED/SK6812/NeoPixel runtime commands.

    Args:
        command: Control command (LED, ALL, BRIGHT, EFFECT, SPEED, COLOR)
        path: Serial port path
        baudrate: Baud rate (default 115200)
        led_index: Individual LED index (for LED command, -1 for all)
        red: Red value (0-255)
        green: Green value (0-255)
        blue: Blue value (0-255)
        brightness: Brightness (0-255)
        effect: Animation effect (solid, rainbow, pulse, fire, wave, running, random, chase)
        speed: Animation speed (1-255)
        color_name: Preset color name (white, red, green, blue, yellow, cyan, magenta, orange, purple, pink, off)

    Returns:
        Command send status and response.
    """
    # Resolve color name
    if color_name:
        rgb = LED_PRESET_COLORS.get(color_name.lower(), (255, 255, 255))
        red, green, blue = rgb

    cmd_string = build_led_command(
        command=command,
        led_index=led_index,
        red=red,
        green=green,
        blue=blue,
        brightness=brightness,
        effect=effect,
        speed=speed,
    )

    if not cmd_string:
        return {
            "status": "error",
            "message": "No command generated. Check parameters.",
        }

    if path:
        result = send_serial(path, cmd_string, baudrate)
    else:
        result = _serial_terminal.write(cmd_string)

    return {
        "status": "sent",
        "command": cmd_string,
        "send_result": result,
    }


# ─── Agent Bridge (Live Hardware Feedback Loop) ────────────────────

# Register agent tools for AI agent ↔ Arduino feedback loop
register_agent_tools(mcp, _agent_bridge)


# ─── Sketch Generation ────────────────────────────────────────────

@mcp.tool()
def list_templates_tool(category: str = None) -> dict:
    """
    List available AgentCore-enabled sketch templates.

    Args:
        category: Filter by category (environment, agriculture, security, automation, lighting, connectivity)

    Returns:
        List of templates with name, category, and description.
    """
    template_list = templates.list_templates(category)
    return {
        "count": len(template_list),
        "templates": [
            {
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "sensors": t.sensors,
                "actuators": t.actuators,
                "displays": t.displays,
                "libraries": t.libraries,
            }
            for t in template_list
        ]
    }


@mcp.tool()
def get_template_tool(name: str) -> dict:
    """
    Get a specific AgentCore sketch template by name.

    Args:
        name: Template name (e.g., 'Weather Station', 'Smart Plant Monitor')

    Returns:
        Template with full sketch code, wiring diagram, and metadata.
    """
    template = templates.get_template(name)
    if not template:
        return {
            "status": "error",
            "message": f"Template '{name}' not found",
            "available": [t.name for t in templates.list_templates()],
        }

    return {
        "status": "success",
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "wiring": template.wiring,
        "sensors": template.sensors,
        "actuators": template.actuators,
        "displays": template.displays,
        "libraries": template.libraries,
        "sketch_size": len(template.sketch),
        "sketch": template.sketch,
    }


@mcp.tool()
def search_templates_tool(query: str) -> dict:
    """
    Search AgentCore sketch templates by keyword.

    Args:
        query: Search term (e.g., 'weather', 'security', 'plant', 'iot')

    Returns:
        Matching templates with descriptions.
    """
    results = templates.search_templates(query)
    return {
        "query": query,
        "count": len(results),
        "templates": [
            {
                "name": t.name,
                "category": t.category,
                "description": t.description,
            }
            for t in results
        ]
    }

@mcp.tool()
def generate_sketch(
    prompt: str,
    board: str = "arduino:avr:nano",
    hardware: str = "",
    led_pin: int = 6,
    num_leds: int = 288,
    led_type: str = "SK6812",
    ir_pin: int = 2,
    servo_pin: int = 9,
    output_path: str = "",
) -> dict:
    """
    Generate an Arduino sketch from a natural language prompt.
    Supports LEDs, IR remotes, sensors, servos, and generic sketches.

    Args:
        prompt: Natural language description of the sketch
        board: Target board FQBN (default arduino:avr:nano)
        hardware: Additional hardware description
        led_pin: LED data pin (default 6)
        num_leds: Number of LEDs (default 288)
        led_type: LED type (SK6812, WS2812B, NEOPIXEL)
        ir_pin: IR receiver pin (default 2)
        servo_pin: Servo control pin (default 9)
        output_path: File path to save sketch (optional)

    Returns:
        Generated sketch code and save status.
    """
    hardware_context = {
        "led_pin": led_pin,
        "num_leds": num_leds,
        "led_type": led_type,
        "ir_pin": ir_pin,
        "servo_pin": servo_pin,
    }

    sketch = generate_sketch_from_prompt(
        prompt=prompt,
        board=board,
        hardware_context=hardware_context,
    )

    result = {
        "status": "generated",
        "sketch": sketch,
        "board": board,
        "size_bytes": len(sketch),
    }

    # Save to file if path provided
    if output_path:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(sketch)
        result["saved_to"] = output_path

    return result


# ─── Compilation & Upload ─────────────────────────────────────────

@mcp.tool()
def compile_sketch_tool(
    sketch_path: str,
    fqbn: str = "",
    port: str = "",
) -> dict:
    """
    Compile an Arduino sketch using arduino-cli.

    Args:
        sketch_path: Path to .ino file or sketch directory
        fqbn: Board FQBN (e.g., arduino:avr:nano). Auto-detect if empty.
        port: Serial port for auto-detection.

    Returns:
        Compilation result with success status, output, and size info.
    """
    result = compile_sketch(sketch_path, fqbn, port)
    return result.to_dict()


@mcp.tool()
def upload_sketch_tool(
    sketch_path: str,
    fqbn: str = "",
    port: str = "",
) -> dict:
    """
    Compile and upload an Arduino sketch to the board.

    Args:
        sketch_path: Path to .ino file or sketch directory
        fqbn: Board FQBN (e.g., arduino:avr:nano)
        port: Serial port for upload (e.g., /dev/ttyACM0)

    Returns:
        Upload result with success status and output.
    """
    result = upload_sketch(sketch_path, fqbn, port)
    return result.to_dict()


@mcp.tool()
def upload_spiffs_tool(port: str, fqbn: str, data_dir: str) -> dict:
    """Upload SPIFFS filesystem to ESP32/ESP8266 board. Args: port, fqbn, data_dir."""
    result = upload_spiffs(port, fqbn, data_dir)
    return result.to_dict()


@mcp.tool()
def upload_littlefs_tool(port: str, fqbn: str, data_dir: str) -> dict:
    """Upload LittleFS filesystem to ESP32 board. Args: port, fqbn, data_dir."""
    return upload_littlefs(port, fqbn, data_dir)


@mcp.tool()
def install_board_core_tool(board_name: str) -> dict:
    """Install board core for ESP32, ESP8266, RP2040, or AVR."""
    return install_board_core(board_name)


# ─── Library Management ───────────────────────────────────────────

@mcp.tool()
def install_library_tool(library_name: str) -> dict:
    """
    Install an Arduino library from the library index.

    Args:
        library_name: Library name (e.g., FastLED, IRremote, DHT-sensor-library)

    Returns:
        Installation status.
    """
    return install_library(library_name)


@mcp.tool()
def list_libraries_tool() -> dict:
    """
    List installed Arduino libraries.

    Returns:
        List of installed libraries with version info.
    """
    return list_libraries()


@mcp.tool()
def search_library_tool(query: str) -> dict:
    """
    Search Arduino library index.

    Args:
        query: Search query string

    Returns:
        List of matching libraries.
    """
    return search_library(query)


# ─── Project Management ───────────────────────────────────────────

@mcp.tool()
def create_project(
    name: str,
    board: str = "arduino:avr:nano",
    description: str = "",
    libraries: list = None,
    pins: list = None,
    connection_type: str = "usb",
    device_path: str = "",
    bt_mac: str = "",
    bt_pin: str = "",
    notes: str = "",
) -> dict:
    """
    Create a new Arduino Vibe IDE project.

    Args:
        name: Project name
        board: Target board FQBN (default arduino:avr:nano)
        description: Project description
        libraries: List of required libraries
        pins: List of pin configurations
        connection_type: Connection type (usb or bluetooth)
        device_path: Device port path
        bt_mac: Bluetooth MAC address
        bt_pin: Bluetooth PIN
        notes: Project notes

    Returns:
        Project creation result with paths and metadata.
    """
    return _project_manager.create(
        name=name,
        board=board,
        description=description,
        libraries=libraries or [],
        pins=pins or [],
        connection_type=connection_type,
        device_path=device_path,
        bt_mac=bt_mac,
        bt_pin=bt_pin,
        notes=notes,
    )


@mcp.tool()
def save_project(
    name: str,
    sketch_path: str = "",
    notes: str = "",
) -> dict:
    """
    Save current project state.

    Args:
        name: Project name
        sketch_path: Path to sketch file to save
        notes: Additional notes to append

    Returns:
        Save status.
    """
    return _project_manager.save(name, sketch_path, notes)


@mcp.tool()
def backup_project(name: str) -> dict:
    """
    Create a full backup of a project (sketch + config + notes).

    Args:
        name: Project name

    Returns:
        Backup info with tarball path and size.
    """
    return _project_manager.backup(name)


@mcp.tool()
def list_projects() -> dict:
    """
    List all Arduino Vibe IDE projects.

    Returns:
        List of projects with metadata.
    """
    return _project_manager.list_projects()


@mcp.tool()
def load_project(name: str) -> dict:
    """
    Load a project.

    Args:
        name: Project name

    Returns:
        Full project data including sketch code, metadata, and backups.
    """
    return _project_manager.load(name)


# ─── Bluetooth Tools ──────────────────────────────────────────────

@mcp.tool()
def bt_pair_device(mac: str, pin: str = "1234") -> dict:
    """
    Pair with a Bluetooth device (HC-05/HC-06).

    Args:
        mac: MAC address (e.g., "AA:BB:CC:DD:EE:FF")
        pin: PIN code (default "1234")

    Returns:
        Pairing status with success, message, and paired flag.
    """
    return pair_bluetooth_device(mac, pin)


@mcp.tool()
def bt_connect(mac: str, pin: str = "1234", channel: int = 1, device: str = "/dev/rfcomm0") -> dict:
    """
    Connect to Bluetooth device and create RFCOMM serial port.

    Creates /dev/rfcomm0 as a serial port usable with arduino-cli upload.
    The HC-05 must be wired to Arduino pins 0 (TX) and 1 (RX) for bootloader access.

    Args:
        mac: MAC address of Bluetooth device
        pin: PIN code
        channel: RFCOMM channel (default 1)
        device: RFCOMM device path (default /dev/rfcomm0)

    Returns:
        Connection status with device path and instructions.
    """
    config = BluetoothUploadConfig(
        mac_address=mac,
        pin=pin,
        rfcomm_channel=channel,
        rfcomm_device=device,
    )
    return connect_bluetooth_for_upload(config)


@mcp.tool()
def bt_disconnect(device: str = "/dev/rfcomm0") -> dict:
    """
    Disconnect Bluetooth RFCOMM connection.

    Args:
        device: RFCOMM device path

    Returns:
        Disconnection status.
    """
    return disconnect_bluetooth(device)


@mcp.tool()
def bt_status() -> dict:
    """
    Show Bluetooth and RFCOMM status.

    Returns active RFCOMM connections and paired Bluetooth devices.

    Returns:
        Status dict with RFCOMM connections and paired devices.
    """
    result = {
        "rfcomm": list_rfcomm_connections(),
        "paired_devices": [],
    }
    # Scan for paired devices
    from devices import scan_bluetooth_devices
    bt_devices = scan_bluetooth_devices()
    if bt_devices:
        for dev in bt_devices:
            result["paired_devices"].append({
                "name": dev.name,
                "mac": dev.mac_address,
                "path": dev.path,
            })
    return result


@mcp.tool()
def bt_upload(
    sketch_path: str,
    mac: str = "",
    device: str = "/dev/rfcomm0",
    fqbn: str = "arduino:avr:nano",
    pin: str = "1234",
) -> dict:
    """
    Upload sketch via Bluetooth (HC-05/HC-06).

    The HC-05 must be wired to Arduino pins 0 (TX) and 1 (RX)
    for bootloader access (hardware UART only).

    Args:
        sketch_path: Path to .ino file or sketch directory
        mac: Bluetooth MAC address (optional, connects if provided)
        device: RFCOMM device path
        fqbn: Board FQBN (default arduino:avr:nano)
        pin: Bluetooth PIN

    Returns:
        Upload result with success, message, and error details.
    """
    result = {
        "success": False,
        "message": "",
        "sketch": sketch_path,
        "device": device,
        "fqbn": fqbn,
        "steps": {},
    }

    # Step 1: Connect if MAC provided
    if mac:
        config = BluetoothUploadConfig(
            mac_address=mac, pin=pin, rfcomm_device=device,
        )
        conn = connect_bluetooth_for_upload(config)
        result["steps"]["connect"] = conn
        if not conn["success"]:
            result["message"] = f"Connect warning: {conn['message']}"
            # Continue anyway — device may already be connected

    # Step 2: Compile
    compile_result = compile_sketch(sketch_path, fqbn, device)
    result["steps"]["compile"] = compile_result.to_dict()
    if not compile_result.success:
        result["message"] = "Compilation failed"
        result["error"] = "; ".join(compile_result.errors)
        return result

    # Step 3: Reset bootloader
    reset_result = trigger_bootloader_reset(device)
    result["steps"]["reset"] = reset_result

    # Step 4: Upload
    result["steps"]["uploading"] = True
    upload_result = upload_sketch(sketch_path, fqbn, device)
    result["steps"]["upload_result"] = upload_result.to_dict()

    # Cleanup
    disconnect_bluetooth(device)
    result["steps"]["disconnected"] = True

    result["success"] = upload_result.success
    result["message"] = upload_result.message
    result["error"] = upload_result.error
    return result


# Register profile tools
register_profile_tools(mcp)


# ─── Main ─────────────────────────────────────────────────────────

def run_server():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    run_server()
