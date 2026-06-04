"""
Serial communication module for Arduino Vibe IDE.
Supports USB serial (/dev/ttyACM*) and Bluetooth RFCOMM.
"""

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import serial
import serial.tools.list_ports


@dataclass
class SerialPort:
    """Represents an open serial connection."""
    port: Optional[serial.Serial] = None
    path: str = ""
    baudrate: int = 115200
    connected: bool = False
    read_buffer: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "baudrate": self.baudrate,
            "connected": self.connected,
        }


class SerialTerminal:
    """
    Serial terminal for communicating with Arduino boards.
    Supports both USB serial and Bluetooth RFCOMM connections.
    """

    _instance: Optional["SerialTerminal"] = None

    def __init__(self):
        self.port: Optional[serial.Serial] = None
        self.path: str = ""
        self.baudrate: int = 115200
        self.connected: bool = False
        self.read_buffer: str = ""
        self._lock = threading.Lock()
        self._read_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self.max_retries: int = 3
        self.retry_delay: float = 1.0
        self.auto_reconnect: bool = False

    @classmethod
    def get_instance(cls) -> "SerialTerminal":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def open(self, path: str, baudrate: int = 115200) -> dict:
        """
        Open a serial port connection.

        Args:
            path: Device path (/dev/ttyACM0, /dev/ttyUSB0, rfcomm:MAC)
            baudrate: Baud rate (default 115200)

        Returns:
            Status dict with connection info
        """
        with self._lock:
            # Handle Bluetooth RFCOMM paths
            if path.startswith("rfcomm:"):
                mac = path.split(":", 1)[1]
                path = _resolve_rfcomm_path(mac)

            if not path:
                return {
                    "status": "error",
                    "message": f"Serial path not found: {path}",
                    "path": path,
                }

            try:
                if self.port and self.port.is_open:
                    self.close()

                self.port = serial.Serial(
                    port=path,
                    baudrate=baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1,
                )

                self.path = path
                self.baudrate = baudrate
                self.connected = True
                self.read_buffer = ""

                return {
                    "status": "connected",
                    "path": self.path,
                    "baudrate": self.baudrate,
                    "message": f"Connected to {path} at {baudrate} baud",
                }

            except serial.SerialException as e:
                return {
                    "status": "error",
                    "path": path,
                    "message": f"Serial error: {e}",
                }

    def close(self) -> dict:
        """Close the serial port connection."""
        with self._lock:
            if self.port and self.port.is_open:
                try:
                    self.port.close()
                except serial.SerialException:
                    pass
                self.read_buffer = ""

            self.connected = False
            return {
                "status": "closed",
                "path": self.path,
                "message": f"Disconnected from {self.path}",
            }

    def write(self, data: str) -> dict:
        """
        Write data to the serial port.

        Args:
            data: String data to send

        Returns:
            Status dict with bytes sent
        """
        with self._lock:
            if not self.connected or not self.port:
                return {
                    "status": "disconnected",
                    "message": "Serial port not connected",
                }

            try:
                if not isinstance(data, bytes):
                    raw = data.encode("utf-8")
                else:
                    raw = data

                self.port.write(raw)
                self.port.flush()

                return {
                    "status": "sent",
                    "bytes": len(raw),
                    "data": data,
                    "path": self.path,
                }

            except serial.SerialException as e:
                self.connected = False
                return {
                    "status": "error",
                    "message": f"Write error: {e}",
                }

    def read(self, size: int = 1024) -> dict:
        """
        Read data from the serial port.

        Args:
            size: Maximum bytes to read

        Returns:
            Status dict with received data
        """
        with self._lock:
            if not self.connected or not self.port:
                return {
                    "status": "disconnected",
                    "message": "Serial port not connected",
                }

            try:
                raw = self.port.read(size)
                data = raw.decode("utf-8", errors="replace")
                self.read_buffer += data

                return {
                    "status": "received",
                    "data": data,
                    "bytes": len(raw),
                    "buffer_size": len(self.read_buffer),
                }

            except serial.SerialException as e:
                self.connected = False
                return {
                    "status": "error",
                    "message": f"Read error: {e}",
                }

    def readline(self) -> dict:
        """Read a line from the serial port."""
        with self._lock:
            if not self.connected or not self.port:
                return {
                    "status": "disconnected",
                    "message": "Serial port not connected",
                }

            try:
                line = self.port.readline().decode("utf-8", errors="replace")
                return {
                    "status": "received",
                    "data": line,
                    "is_line": True,
                }
            except serial.SerialException as e:
                self.connected = False
                return {
                    "status": "error",
                    "message": f"Readline error: {e}",
                }

    def send_command(self, command: str, timeout: float = 5.0) -> dict:
        """
        Send a command and wait for response.

        Args:
            command: Command string to send
            timeout: Seconds to wait for response

        Returns:
            Status dict with response
        """
        write_result = self.write(command + "\r\n")
        if write_result["status"] != "sent":
            return write_result

        response = ""
        start = time.time()
        while time.time() - start < timeout:
            read_result = self.read(256)
            if read_result["status"] == "received" and read_result["data"]:
                response += read_result["data"]
                if "\n" in read_result["data"]:
                    break
            time.sleep(0.05)

        return {
            "status": "response",
            "command": command,
            "response": response.strip(),
        }

    def get_status(self) -> dict:
        """Get current connection status."""
        return {
            "connected": self.connected,
            "path": self.path,
            "baudrate": self.baudrate,
            "buffer_size": len(self.read_buffer),
            "port_info": self.port.name if self.port else None,
        }

    def retry_write(self, data: str, retries: int = None) -> dict:
        """Write with automatic retry on disconnect."""
        retries = retries or self.max_retries
        for attempt in range(retries):
            result = self.write(data)
            if result["status"] == "sent":
                return result
            if self.auto_reconnect and result["status"] == "error" and self.path:
                self.open(self.path, self.baudrate)
            time.sleep(self.retry_delay * (attempt + 1))
        return result

    def check_connection(self) -> dict:
        """Check if the serial connection is still alive."""
        with self._lock:
            if not self.port or not self.port.is_open:
                return {"connected": False, "path": self.path}
            try:
                self.port.read(1)
                return {"connected": True, "path": self.path}
            except serial.SerialException as e:
                self.connected = False
                return {"connected": False, "path": self.path, "error": str(e)}

    def reconnect(self) -> dict:
        """Attempt to reconnect to the last known port."""
        with self._lock:
            if not self.path:
                return {"status": "error", "message": "No path to reconnect to"}
            self.close()
            time.sleep(1)
            return self.open(self.path, self.baudrate)


def _resolve_rfcomm_path(mac: str) -> str:
    """
    Resolve a Bluetooth MAC address to an RFCOMM device path.

    Checks /dev/rfcomm* for the MAC address.
    """
    # Check existing rfcomm devices
    for rfcomm_path in sorted(
        [f"/dev/rfcomm{i}" for i in range(0, 20)]
    ):
        if os.path.exists(rfcomm_path):
            try:
                with open(os.path.join("/sys", os.path.relpath(rfcomm_path, "/dev"), "uevent")) as f:
                    content = f.read()
                    if mac.upper().replace(":", ":") in content.upper() or mac.upper() in content.upper():
                        return rfcomm_path
            except (FileNotFoundError, PermissionError):
                pass

    # Try to bind rfcomm0
    try:
        import subprocess
        result = subprocess.run(
            ["rfcomm", "bind", "rfcomm0", mac],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return "/dev/rfcomm0"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return f"/dev/rfcomm0"


def open_terminal(path: str, baudrate: int = 115200) -> dict:
    """Open a serial terminal connection (stateless helper)."""
    terminal = SerialTerminal()
    return terminal.open(path, baudrate)


def close_terminal(terminal_id: str = "") -> dict:
    """Close the singleton serial terminal."""
    terminal = SerialTerminal.get_instance()
    return terminal.close()


def send_serial(path: str, data: str, baudrate: int = 115200) -> dict:
    """
    Send data over serial (stateless: opens, sends, closes).
    """
    terminal = SerialTerminal()
    open_result = terminal.open(path, baudrate)
    if open_result["status"] != "connected":
        return open_result

    send_result = terminal.write(data)
    terminal.close()
    return send_result


def read_serial(path: str, baudrate: int = 115200, size: int = 1024) -> dict:
    """Read data from serial port (stateless)."""
    terminal = SerialTerminal()
    open_result = terminal.open(path, baudrate)
    if open_result["status"] != "connected":
        return open_result

    read_result = terminal.read(size)
    terminal.close()
    return read_result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
        terminal = SerialTerminal()
        print(json.dumps(terminal.open(path, baud), indent=2))
    else:
        import sys
        print("Usage: python serial_terminal.py <device_path> [baudrate]")
        print("  e.g., python serial_terminal.py /dev/ttyACM0 115200")
