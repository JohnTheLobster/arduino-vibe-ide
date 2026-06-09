"""
Device discovery module for Arduino Vibe IDE.
Scans USB serial ports and Bluetooth devices.
"""

import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class DeviceInfo:
    """Represents a discovered Arduino-compatible device."""
    device_id: str
    device_type: str  # "usb_serial" | "bluetooth"
    path: str
    name: str = ""
    description: str = ""
    vendor_id: str = ""
    product_id: str = ""
    board_hint: str = ""
    mac_address: str = ""
    bt_pin: str = ""
    rfcomm_channel: int = 1
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def scan_usb_serial_ports() -> list[DeviceInfo]:
    """Scan /dev/ttyACM* and /dev/ttyUSB* for Arduino devices."""
    devices: list[DeviceInfo] = []
    patterns = ["/dev/ttyACM*", "/dev/ttyUSB*"]

    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            info = _probe_usb_device(path)
            if info:
                devices.append(info)

    return devices


def _probe_usb_device(path: str) -> Optional[DeviceInfo]:
    """Probe a single USB serial device for metadata."""
    device_id = f"usb:{os.path.basename(path)}"

    # Try to read sysfs attributes
    vendor_id = ""
    product_id = ""
    product_name = ""

    try:
        # Get sysfs path for USB device
        uevent_path = os.path.join("/sys", os.path.relpath(path, "/dev"))
        # Navigate to parent USB device
        dev_dir = os.path.dirname(os.path.dirname(os.path.dirname(uevent_path)))

        if os.path.exists(os.path.join(dev_dir, "idVendor")):
            with open(os.path.join(dev_dir, "idVendor")) as f:
                vendor_id = f.read().strip()
        if os.path.exists(os.path.join(dev_dir, "idProduct")):
            with open(os.path.join(dev_dir, "idProduct")) as f:
                product_id = f.read().strip()
        if os.path.exists(os.path.join(dev_dir, "product")):
            with open(os.path.join(dev_dir, "product")) as f:
                product_name = f.read().strip()

    except (FileNotFoundError, PermissionError, OSError):
        pass

    # Infer board from product name and IDs
    board_hint = _infer_usb_board(vendor_id, product_id, product_name)

    # Known USB-to-serial chip IDs
    known_vendors = {
        "2341": "Arduino",
        "1a86": "Silabs/CH340",
        "10c4": "FTDI",
        "0403": "FTDI",
        "2a03": "Microchip",
    }
    vendor_name = known_vendors.get(vendor_id, "Unknown")

    description = f"{vendor_name} USB Serial"
    if product_name:
        description = product_name

    return DeviceInfo(
        device_id=device_id,
        device_type="usb_serial",
        path=path,
        name=product_name or os.path.basename(path),
        description=description,
        vendor_id=vendor_id,
        product_id=product_id,
        board_hint=board_hint,
    )


def _infer_usb_board(vendor_id: str, product_id: str, product_name: str) -> str:
    """Infer Arduino board type from USB device IDs."""
    combined = f"{vendor_id}:{product_id}".lower()
    name_lower = product_name.lower()

    # Arduino official boards
    if vendor_id == "2341":
        if product_id == "0043" or "nano" in name_lower:
            return "arduino:avr:nano"
        if product_id == "0001" or "uno" in name_lower:
            return "arduino:avr:uno"
        if product_id == "0010" or "mega" in name_lower:
            return "arduino:avr:mega"
        if product_id == "0042" or "leonardo" in name_lower:
            return "arduino:avr:leonardo"
        if product_id == "804b" or "micro" in name_lower:
            return "arduino:avr:micro"
        if product_id == "0037" or "pro micro" in name_lower:
            return "arduino:avr:promicro"
        return "arduino:avr:nano"  # default to nano for Arduino vendor

    # CH340 clones (common on Nano clones)
    if vendor_id == "1a86" and product_id == "5523":
        return "arduino:avr:nano"

    # ATmega16U2 bootloader (official Arduino)
    if vendor_id == "2341":
        return "arduino:avr:nano"

    return ""


def scan_bluetooth_devices() -> list[DeviceInfo]:
    """Scan for Bluetooth devices using bluetoothctl."""
    devices: list[DeviceInfo] = []

    try:
        # List paired devices
        result = _run_command(["bluetoothctl", "paired-devices"], timeout=10)
        if result:
            for dev in _parse_paired_devices(result):
                devices.append(dev)

        # List connected devices
        result = _run_command(["bluetoothctl", "devices"], timeout=10)
        if result:
            for dev in _parse_devices(result):
                # Add if not already in list
                if not any(d.mac_address == dev.mac_address for d in devices):
                    devices.append(dev)

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        devices.append(DeviceInfo(
            device_id="bt:bluetoothctl_missing",
            device_type="bluetooth",
            path="",
            name="bluetoothctl",
            description=f"bluetoothctl not found or timed out: {e}",
            metadata={"status": "missing"},
        ))

    return devices


def _parse_paired_devices(output: str) -> list[DeviceInfo]:
    """Parse bluetoothctl paired-devices output."""
    devices = []
    lines = output.strip().split("\n")

    for line in lines:
        match = re.search(r"Device\s+([0-9A-Fa-f:]+)\s*(.*)", line)
        if match:
            mac = match.group(1).strip()
            name = match.group(2).strip() or ""

            device_type = _classify_bluetooth_device(mac, name)

            devices.append(DeviceInfo(
                device_id=f"bt:{mac}",
                device_type="bluetooth",
                path=f"rfcomm:{mac}",
                name=name or "Bluetooth Device",
                description=f"Paired Bluetooth device ({device_type})",
                mac_address=mac,
                bt_pin="1234",
                board_hint=_infer_bt_board(mac, name),
                metadata={"bt_module": device_type},
            ))

    return devices


def _parse_devices(output: str) -> list[DeviceInfo]:
    """Parse bluetoothctl devices output."""
    devices = []
    lines = output.strip().split("\n")

    for line in lines:
        match = re.search(r"Device\s+([0-9A-Fa-f:]+)\s+(.*)", line)
        if match:
            mac = match.group(1).strip()
            name = match.group(2).strip() or ""

            device_type = _classify_bluetooth_device(mac, name)

            devices.append(DeviceInfo(
                device_id=f"bt:{mac}",
                device_type="bluetooth",
                path=f"rfcomm:{mac}",
                name=name or "Bluetooth Device",
                description=f"Bluetooth device ({device_type})",
                mac_address=mac,
                bt_pin="1234",
                board_hint=_infer_bt_board(mac, name),
                metadata={"bt_module": device_type},
            ))

    return devices


def _classify_bluetooth_device(mac: str, name: str) -> str:
    """Classify Bluetooth device type."""
    name_lower = name.lower()

    if "hc-05" in name_lower or "hc05" in name_lower:
        return "HC-05"
    if "hc-06" in name_lower or "hc06" in name_lower:
        return "HC-06"
    if "jy-mcu" in name_lower:
        return "JY-MCU"
    if "bluno" in name_lower:
        return "Bluno"
    if "linvor" in name_lower:
        return "Linvor BT"

    # Check known MAC prefixes
    mac_upper = mac.upper()
    if mac_upper.startswith("98:DA:50"):
        return "HC-05"

    return "Generic BT"


def _infer_bt_board(mac: str, name: str) -> str:
    """Infer Arduino board from Bluetooth device info."""
    name_lower = name.lower()
    if "uno" in name_lower:
        return "arduino:avr:uno"
    if "nano" in name_lower:
        return "arduino:avr:nano"
    # Default assumption for HC-05 modules: Arduino Nano
    return "arduino:avr:nano"


def _run_command(cmd: list[str], timeout: int = 10) -> Optional[str]:
    """Run a shell command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def discover_all_devices() -> list[DeviceInfo]:
    """Discover all Arduino-compatible devices (USB + Bluetooth)."""
    usb_devices = scan_usb_serial_ports()
    bt_devices = scan_bluetooth_devices()
    return usb_devices + bt_devices


def discover_devices_json() -> dict:
    """Return structured JSON for MCP tool response."""
    all_devices = discover_all_devices()
    return {
        "devices": [d.to_dict() for d in all_devices],
        "total_count": len(all_devices),
        "usb_count": len([d for d in all_devices if d.device_type == "usb_serial"]),
        "bt_count": len([d for d in all_devices if d.device_type == "bluetooth"]),
    }


def check_modules(device_path: str) -> dict:
    """
    Attempt to detect connected modules by querying serial port.
    Sends AT commands and probes for known module responses.
    """
    results = {
        "device": device_path,
        "modules": [],
        "detected": {},
    }

    try:
        import serial

        # Try AT commands for HC-05/HC-06
        try:
            ser = serial.Serial(
                port=device_path, baudrate=38400, timeout=2,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            ser.write(b"AT\r\n")
            resp = ser.read(32).decode("utf-8", errors="replace")
            if "OK" in resp:
                results["modules"].append({
                    "type": "HC-05/HC-06",
                    "status": "responding",
                    "baudrate": 38400,
                })

                # Query version
                ser.write(b"AT+VERSION\r\n")
                ver = ser.read(64).decode("utf-8", errors="replace")
                results["modules"][-1]["version"] = ver.strip()

                # Query name
                ser.write(b"AT+NAME\r\n")
                nm = ser.read(64).decode("utf-8", errors="replace")
                results["modules"][-1]["name"] = nm.strip()

                ser.close()

            # Try at 9600 baud (HC-06 default)
            if not results["modules"]:
                ser = serial.Serial(
                    port=device_path, baudrate=9600, timeout=1
                )
                ser.write(b"AT\r\n")
                resp = ser.read(32).decode("utf-8", errors="replace")
                if "OK" in resp:
                    results["modules"].append({
                        "type": "HC-06",
                        "status": "responding",
                        "baudrate": 9600,
                    })
                    ser.close()

        except serial.SerialException:
            results["modules"].append({
                "type": "serial",
                "status": "available",
                "note": "serial port opened successfully",
            })

    except ImportError:
        results["modules"].append({
            "type": "serial",
            "status": "pyserial_missing",
        })

    # Detect by I2C scan (requires wiring)
    results["i2c_modules"] = _detect_i2c_modules(device_path)

    return results


def _detect_i2c_modules(device_path: str) -> list:
    """Detect I2C modules connected to Arduino."""
    modules = []
    try:
        import serial
        import time

        ser = serial.Serial(
            port=device_path, baudrate=115200, timeout=1
        )
        time.sleep(0.5)

        # Send I2C scan command (requires I2C scanner sketch running on board)
        ser.write(b"I2C_SCAN\r\n")
        resp = ser.read(256).decode("utf-8", errors="replace")
        ser.close()

        # Parse I2C addresses
        addresses = re.findall(r"0x([0-9A-Fa-f]{2})", resp)
        i2c_device_names = {
            "0x27": "PCF8574 I/O Expander",
            "0x3C": "ST7735/ST7789 Display",
            "0x3A": "ST7735 Display",
            "0x48": "HTU21D Temp/Humidity Sensor",
            "0x76": "BMP280 Pressure Sensor",
            "0x77": "BME280/BMP180 Sensor",
            "0x68": "DS3231 RTC",
            "0x6B": "MPU6050 IMU",
            "0x1E": "MCP23017 I/O Expander",
            "0x20": "MCP23008 I/O Expander",
            "0x40": "PCA9685 PWM Servo Driver",
            "0x23": "ADS1115 ADC",
            "0x5C": "TSL2591 Light Sensor",
            "0x14": "ADS1015 ADC",
            "0x3D": "ST7789 Display",
        }

        for addr in addresses:
            name = i2c_device_names.get(addr, f"Unknown I2C Device")
            modules.append({
                "type": "i2c",
                "address": f"0x{addr}",
                "name": name,
            })

    except Exception:
        pass

    return modules


if __name__ == "__main__":
    print(json.dumps(discover_devices_json(), indent=2))
