"""
Agent Bridge — AI agent control layer for Arduino hardware.

Enables structured command/response feedback loops between AI agents
and Arduino boards. An agent can:
- Connect to a board
- Query capabilities and sensor readings
- Control outputs (LEDs, servos, relays, motors)
- Run autonomous control loops based on real-time data
- Monitor hardware state continuously
"""

import json
import re
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable

from serial_terminal import SerialTerminal


# ─── Protocol ──────────────────────────────────────────────────────
# All agent-ready sketches speak this protocol over serial.
# Commands: AGENT_<ACTION> [payload]
# Responses: JSON lines prefixed with AGENT_RESP:

AGENT_COMMANDS = {
    "PING": "AGENT_PING",                          # Liveness check
    "CAPABILITIES": "AGENT_CAPS",                   # What can this board do?
    "READ": "AGENT_READ {sensor}",                  # Read a sensor by name
    "READ_ALL": "AGENT_READ_ALL",                   # Read all sensors
    "WRITE": "AGENT_WRITE {pin} {value}",           # Digital/PWM write
    "SET_LED": "AGENT_LED {idx} {r} {g} {b}",      # Set LED color
    "SET_EFFECT": "AGENT_EFFECT {name}",            # Set LED animation
    "SERVO_MOVE": "AGENT_SERVO {idx} {angle}",     # Move servo
    "RELA Y": "AGENT_RELAY {idx} {on|off}",        # Toggle relay
    "EXECUTE": "AGENT_EXEC {code}",                # Execute Arduino function
    "SUBSCRIBE": "AGENT_SUB {sensor} {interval}",  # Subscribe to sensor data
    "UNSUBSCRIBE": "AGENT_UNSUB {sensor}",         # Stop subscription
    "STATE": "AGENT_STATE",                        # Full board state dump
}


@dataclass
class AgentCapability:
    """Describes a hardware capability on the board."""
    type: str          # "sensor", "actuator", "led", "servo", "relay"
    name: str          # Human-readable name
    pin: Optional[int] = None
    unit: str = ""     # "°C", "lux", "degrees", etc.
    range_min: float = 0
    range_max: float = 1
    description: str = ""


@dataclass
class AgentReading:
    """A sensor reading or actuator state."""
    name: str
    value: float
    unit: str = ""
    timestamp: float = field(default_factory=time.time)
    raw: str = ""


@dataclass
class AgentBridge:
    """
    AI Agent ↔ Arduino bridge.

    Manages a persistent connection to an agent-ready Arduino board.
    Supports command execution, sensor subscriptions, and autonomous control loops.
    """
    terminal: Optional[SerialTerminal] = None
    path: str = ""
    baudrate: int = 115200
    capabilities: list = field(default_factory=list)
    subscriptions: dict = field(default_factory=dict)
    _subscribe_thread: Optional[threading.Thread] = None
    _subscribe_running: bool = False
    _on_reading: Optional[Callable] = None

    def connect(self, path: str = "", baudrate: int = 115200) -> dict:
        """Connect to an agent-ready Arduino board."""
        if not path:
            # Auto-detect
            from devices import discover_devices_json
            result = discover_devices_json()
            if result["devices"]:
                path = result["devices"][0]["path"]
            else:
                return {"status": "error", "message": "No devices found"}

        self.terminal = SerialTerminal()
        open_result = self.terminal.open(path, baudrate)
        if open_result["status"] == "connected":
            self.path = path
            self.baudrate = baudrate

            # Handshake
            ping = self._send("AGENT_PING", timeout=3)
            if "OK" in str(ping.get("response", "")):
                # Load capabilities
                caps_result = self._send("AGENT_CAPS", timeout=3)
                caps_text = caps_result.get("response", "")
                if caps_text:
                    self._parse_capabilities(caps_text)

                return {
                    "status": "connected",
                    "path": self.path,
                    "handshake": "ok",
                    "capabilities": self.capabilities,
                }
            else:
                # Board might not be agent-ready yet
                return {
                    "status": "connected",
                    "path": self.path,
                    "handshake": "legacy",
                    "message": "Board connected but not agent-ready. Upload AgentCore sketch first.",
                    "capabilities": [],
                }
        return open_result

    def disconnect(self) -> dict:
        """Disconnect from the board."""
        self._subscribe_running = False
        if self.terminal:
            return self.terminal.close()
        return {"status": "closed", "message": "Not connected"}

    def ping(self) -> dict:
        """Check board liveness."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}
        return self._send("AGENT_PING", timeout=2)

    def get_capabilities(self) -> dict:
        """Query what hardware is available on the board."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}

        result = self._send("AGENT_CAPS", timeout=3)
        caps_text = result.get("response", "")
        if caps_text:
            self._parse_capabilities(caps_text)
        return {
            "status": "ok",
            "capabilities": self.capabilities,
            "count": len(self.capabilities),
        }

    def read_sensor(self, name: str) -> dict:
        """Read a specific sensor by name."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}
        return self._send(f"AGENT_READ {name}", timeout=3)

    def read_all_sensors(self) -> dict:
        """Read all available sensors."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}
        result = self._send("AGENT_READ_ALL", timeout=5)
        response = result.get("response", "")
        readings = self._parse_readings(response)
        return {
            "status": "ok",
            "readings": readings,
            "count": len(readings),
        }

    def write_pin(self, pin: int, value: float, mode: str = "digital") -> dict:
        """Write a value to a pin (digital or PWM)."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}
        return self._send(f"AGENT_WRITE {pin} {int(value)}", timeout=3)

    def control_led(self, index: int, r: int, g: int, b: int) -> dict:
        """Set an individual LED color."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}
        return self._send(f"AGENT_LED {index} {r} {g} {b}", timeout=3)

    def control_servo(self, index: int, angle: int) -> dict:
        """Move a servo to an angle."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}
        return self._send(f"AGENT_SERVO {index} {angle}", timeout=3)

    def get_state(self) -> dict:
        """Get full board state dump."""
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}
        result = self._send("AGENT_STATE", timeout=5)
        response = result.get("response", "")
        readings = self._parse_readings(response)
        return {
            "status": "ok",
            "path": self.path,
            "connected": True,
            "capabilities": self.capabilities,
            "readings": readings,
            "subscriptions": list(self.subscriptions.keys()),
        }

    def subscribe(self, sensor: str, interval_ms: int = 1000,
                  callback: Optional[Callable] = None) -> dict:
        """
        Subscribe to continuous sensor readings.

        The bridge will read data at the specified interval and
        invoke the callback with each reading.
        """
        if not self.terminal or not self.terminal.connected:
            return {"status": "disconnected"}

        # Send subscription request to board
        send_result = self._send(f"AGENT_SUB {sensor} {interval_ms}", timeout=3)

        self.subscriptions[sensor] = {
            "interval_ms": interval_ms,
            "callback": callback,
            "started": time.time(),
        }

        # Start subscription thread if not running
        if not self._subscribe_running:
            self._subscribe_running = True
            self._subscribe_thread = threading.Thread(
                target=self._subscription_loop, daemon=True
            )
            self._subscribe_thread.start()

        return {
            "status": "subscribed",
            "sensor": sensor,
            "interval_ms": interval_ms,
            "board_response": send_result,
        }

    def unsubscribe(self, sensor: str) -> dict:
        """Stop a sensor subscription."""
        if sensor in self.subscriptions:
            self._send(f"AGENT_UNSUB {sensor}", timeout=2)
            del self.subscriptions[sensor]
            return {"status": "unsubscribed", "sensor": sensor}
        return {"status": "not_found", "sensor": sensor}

    def autonomous_loop(self, condition: Callable, action: Callable,
                        interval_ms: int = 500, max_iterations: int = 100) -> dict:
        """
        Run an autonomous control loop.

        condition: function(readings) -> bool (continue while True)
        action: function(readings) -> str (returns command to send)

        Example:
            bridge.autonomous_loop(
                condition=lambda r: any(s["value"] > 30 for s in r if s["name"] == "temperature"),
                action=lambda r: "AGENT_LED 0 255 0 0",  # Red when hot
                interval_ms=1000,
            )
        """
        iterations = 0
        results = []

        while iterations < max_iterations:
            # Read all sensors
            reading_result = self.read_all_sensors()
            readings = reading_result.get("readings", [])

            if not condition(readings):
                break

            # Execute action
            command = action(readings)
            if command:
                cmd_result = self._send(command, timeout=3)
                results.append({
                    "iteration": iterations,
                    "readings": readings,
                    "command": command,
                    "result": cmd_result,
                })

            time.sleep(interval_ms / 1000)
            iterations += 1

        return {
            "status": "completed",
            "iterations": iterations,
            "results": results[-10:],  # Last 10 iterations
        }

    # ─── Internal ──────────────────────────────────────────────────

    def _send(self, command: str, timeout: float = 3) -> dict:
        """Send a command and wait for response."""
        if not self.terminal:
            return {"status": "error", "message": "No terminal"}
        return self.terminal.send_command(command, timeout=timeout)

    def _parse_capabilities(self, text: str) -> list:
        """Parse capability response from board."""
        self.capabilities = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("AGENT"):
                continue

            # Parse JSON capability declarations
            if "AGENT_CAP:" in line:
                try:
                    cap_str = line.split("AGENT_CAP:", 1)[1].strip()
                    cap = json.loads(cap_str)
                    self.capabilities.append(AgentCapability(**cap))
                except (json.JSONDecodeError, TypeError):
                    pass

            # Parse plain text capabilities
            elif "SENSOR:" in line:
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[1]
                    unit = parts[2] if len(parts) > 2 else ""
                    self.capabilities.append(AgentCapability(
                        type="sensor", name=name, unit=unit
                    ))

            elif "ACTUATOR:" in line:
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[1]
                    pin = int(parts[2]) if parts[2].isdigit() else None
                    self.capabilities.append(AgentCapability(
                        type="actuator", name=name, pin=pin
                    ))

        return self.capabilities

    def _parse_readings(self, text: str) -> list:
        """Parse sensor reading response from board."""
        readings = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Parse JSON readings
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    readings.append(AgentReading(
                        name=data.get("name", "unknown"),
                        value=float(data.get("value", 0)),
                        unit=data.get("unit", ""),
                    ))
                except (json.JSONDecodeError, ValueError):
                    pass

            # Parse AGENT_READ:name:value:unit format
            elif "AGENT_READ:" in line:
                parts = line.split(":", 4)
                if len(parts) >= 4:
                    readings.append(AgentReading(
                        name=parts[1],
                        value=float(parts[2]) if parts[2] else 0,
                        unit=parts[3] if len(parts) > 3 else "",
                        raw=line,
                    ))

        return readings

    def _subscription_loop(self):
        """Background thread that reads subscription data."""
        while self._subscribe_running and self.terminal and self.terminal.connected:
            result = self.terminal.read(1024)
            if result.get("status") == "received" and result.get("data"):
                data = result["data"]
                # Parse subscription data
                for line in data.strip().split("\n"):
                    if "AGENT_SUB_READ:" in line:
                        try:
                            parts = line.split(":", 4)
                            if len(parts) >= 4:
                                sensor_name = parts[1]
                                value = float(parts[2]) if parts[2] else 0
                                unit = parts[3] if len(parts) > 3 else ""

                                reading = AgentReading(
                                    name=sensor_name, value=value, unit=unit
                                )

                                # Invoke callback
                                sub = self.subscriptions.get(sensor_name)
                                if sub and sub.get("callback"):
                                    sub["callback"](reading)
                        except (ValueError, IndexError):
                            pass
            time.sleep(0.1)


# ─── MCP Tool Integration ──────────────────────────────────────────
# Import here to avoid circular imports

def register_agent_tools(mcp, bridge: AgentBridge):
    """Register agent bridge tools with an MCP server."""

    @mcp.tool()
    def agent_connect(path: str = "", baudrate: int = 115200) -> dict:
        """
        Connect to an agent-ready Arduino board.

        Args:
            path: Serial port path (auto-detect if empty)
            baudrate: Baud rate (default 115200)

        Returns:
            Connection status with capabilities.
        """
        return bridge.connect(path=path, baudrate=baudrate)

    @mcp.tool()
    def agent_ping() -> dict:
        """Check if the connected Arduino board is alive."""
        return bridge.ping()

    @mcp.tool()
    def agent_get_capabilities() -> dict:
        """Query available sensors and actuators on the board."""
        return bridge.get_capabilities()

    @mcp.tool()
    def agent_read_sensor(name: str) -> dict:
        """
        Read a specific sensor by name.

        Args:
            name: Sensor name (e.g., 'temperature', 'humidity', 'light')
        """
        return bridge.read_sensor(name)

    @mcp.tool()
    def agent_read_all() -> dict:
        """Read all available sensors on the board."""
        return bridge.read_all_sensors()

    @mcp.tool()
    def agent_write_pin(pin: int, value: int, mode: str = "digital") -> dict:
        """
        Write a value to a digital or PWM pin.

        Args:
            pin: Pin number
            value: Value (0 or 1 for digital, 0-255 for PWM)
            mode: Pin mode (digital or pwm)
        """
        return bridge.write_pin(pin, value, mode)

    @mcp.tool()
    def agent_control_led(index: int, red: int, green: int, blue: int) -> dict:
        """
        Set an individual LED color.

        Args:
            index: LED index (0 for all)
            red: Red value (0-255)
            green: Green value (0-255)
            blue: Blue value (0-255)
        """
        return bridge.control_led(index, red, green, blue)

    @mcp.tool()
    def agent_control_servo(index: int, angle: int) -> dict:
        """
        Move a servo to an angle.

        Args:
            index: Servo index
            angle: Angle in degrees (0-180)
        """
        return bridge.control_servo(index, angle)

    @mcp.tool()
    def agent_get_state() -> dict:
        """Get full board state including sensors, actuators, and subscriptions."""
        return bridge.get_state()

    @mcp.tool()
    def agent_subscribe(sensor: str, interval_ms: int = 1000) -> dict:
        """
        Subscribe to continuous sensor readings.

        Args:
            sensor: Sensor name to subscribe to
            interval_ms: Update interval in milliseconds (default 1000)
        """
        return bridge.subscribe(sensor, interval_ms)

    @mcp.tool()
    def agent_disconnect() -> dict:
        """Disconnect from the Arduino board."""
        return bridge.disconnect()
