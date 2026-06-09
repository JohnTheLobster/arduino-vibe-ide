"""
Bluetooth upload module for Arduino Vibe IDE.
Handles HC-05/HC-06 pairing, RFCOMM setup, and sketch upload over Bluetooth.
"""

import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class BluetoothUploadConfig:
    """Configuration for Bluetooth upload."""
    mac_address: str
    pin: str = "1234"
    rfcomm_device: str = "/dev/rfcomm0"
    rfcomm_channel: int = 1
    upload_baudrate: int = 57600  # Arduino Nano bootloader baudrate
    data_baudrate: int = 9600     # Default HC-05 data baudrate


def pair_bluetooth_device(mac: str, pin: str = "1234") -> dict:
    """
    Pair a Bluetooth device using bluetoothctl.

    Args:
        mac: MAC address (e.g., "AA:BB:CC:DD:EE:FF")
        pin: PIN code (default "1234" for HC-05/HC-06)

    Returns:
        Status dict with success, message, and paired status
    """
    result = {
        "success": False,
        "message": "",
        "paired": False,
        "mac": mac,
    }

    # Check if already paired
    paired_output = _run_bluetoothctl(["paired-devices"], timeout=10)
    if paired_output and mac in paired_output:
        result["success"] = True
        result["paired"] = True
        result["message"] = f"Already paired with {mac}"
        return result

    # Pair using bluetoothctl with expect-style interaction
    try:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        commands = [
            f"pair {mac}\n",
            f"{pin}\n",  # Send PIN when prompted
            "trust " + mac + "\n",
            "quit\n",
        ]
        stdin_data = "".join(commands)
        stdout, stderr = proc.communicate(input=stdin_data, timeout=30)

        combined = stdout + stderr
        result["output"] = combined

        # Check for success indicators
        if "Pairing successful" in combined or "paired" in combined.lower():
            result["success"] = True
            result["paired"] = True
            result["message"] = f"Successfully paired with {mac}"
        elif "Already paired" in combined:
            result["success"] = True
            result["paired"] = True
            result["message"] = f"Already paired with {mac}"
        else:
            result["message"] = f"Pairing result unclear for {mac}"
            # Check if it's in paired list now
            check = _run_bluetoothctl(["paired-devices"], timeout=10)
            if check and mac in check:
                result["success"] = True
                result["paired"] = True
                result["message"] = f"Verified paired with {mac}"
            else:
                result["message"] = f"Pairing may have failed: {combined[:200]}"

    except subprocess.TimeoutExpired:
        result["message"] = "bluetoothctl timed out during pairing"
    except FileNotFoundError:
        result["message"] = "bluetoothctl not found. Install bluez-utils."

    return result


def setup_rfcomm(mac: str, channel: int = 1, device: str = "/dev/rfcomm0") -> dict:
    """
    Set up an RFCOMM serial connection to a Bluetooth device.

    Creates /dev/rfcomm0 (or specified device) as a serial port
    that can be used with arduino-cli for uploads.

    Args:
        mac: MAC address of the Bluetooth device
        channel: RFCOMM channel (default 1)
        device: RFCOMM device path (default /dev/rfcomm0)

    Returns:
        Status dict with success, device path, and message
    """
    result = {
        "success": False,
        "message": "",
        "device": device,
        "mac": mac,
    }

    # Kill any existing RFCOMM on this device
    _release_rfcomm(device)

    try:
        # Bind RFCOMM device
        bind_cmd = ["rfcomm", "bind", device, mac, str(channel)]
        stdout, stderr, code = _run_command(bind_cmd, timeout=15)

        if code == 0:
            # Verify the device exists
            if os.path.exists(device):
                result["success"] = True
                result["message"] = f"RFCOMM bound: {device} -> {mac}"
                return result
            else:
                result["message"] = f"RFCOMM bind succeeded but {device} not found"
        else:
            result["message"] = f"rfcomm bind failed: {stderr.strip()}"

    except FileNotFoundError:
        result["message"] = "rfcomm not found. Install bluez-utils."
    except subprocess.TimeoutExpired:
        result["message"] = "rfcomm bind timed out"

    return result


def release_rfcomm(device: str = "/dev/rfcomm0") -> dict:
    """
    Release an RFCOMM connection.

    Args:
        device: RFCOMM device path

    Returns:
        Status dict
    """
    return _release_rfcomm(device)


def _release_rfcomm(device: str = "/dev/rfcomm0") -> dict:
    """Internal: release RFCOMM, ignoring errors if already released."""
    result = {"success": True, "message": ""}
    try:
        _run_command(["rfcomm", "release", device], timeout=5)
        result["message"] = f"Released {device}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return result


def connect_bluetooth_for_upload(config: BluetoothUploadConfig) -> dict:
    """
    Full Bluetooth connection flow for upload:
    1. Pair (if needed)
    2. Bind RFCOMM
    3. Verify device exists

    Returns:
        Status dict with connection status and device path
    """
    result = {
        "success": False,
        "message": "",
        "device": config.rfcomm_device,
        "mac": config.mac_address,
        "steps": {},
    }

    # Step 1: Pair
    pair_result = pair_bluetooth_device(config.mac_address, config.pin)
    result["steps"]["pair"] = pair_result

    if not pair_result["paired"]:
        result["message"] = f"Pair failed: {pair_result['message']}"
        return result

    # Step 2: Setup RFCOMM
    rfcomm_result = setup_rfcomm(
        config.mac_address,
        config.rfcomm_channel,
        config.rfcomm_device,
    )
    result["steps"]["rfcomm"] = rfcomm_result

    if rfcomm_result["success"]:
        result["success"] = True
        result["message"] = f"Connected via {config.rfcomm_device}"
    else:
        result["message"] = f"RFCOMM setup failed: {rfcomm_result['message']}"

    return result


def disconnect_bluetooth(device: str = "/dev/rfcomm0") -> dict:
    """Disconnect and release RFCOMM."""
    return release_rfcomm(device)


def setup_hc05_for_upload(mac: str, channel: int = 1) -> dict:
    """
    Set up HC-05 for upload mode.

    The HC-05 needs to be in AT mode briefly to reconfigure
    the baudrate for bootloader communication (57600),
    then switched back to data mode for normal operation.

    For upload, we connect via RFCOMM and let arduino-cli
    handle the STK500 protocol directly.

    Args:
        mac: MAC address of HC-05
        channel: RFCOMM channel

    Returns:
        Status dict with instructions and device path
    """
    device = "/dev/rfcomm0"

    # Bind RFCOMM
    rfcomm_result = setup_rfcomm(mac, channel, device)

    result = {
        "success": rfcomm_result["success"],
        "message": "",
        "device": device,
        "upload_baudrate": 57600,
        "instructions": [],
    }

    if rfcomm_result["success"]:
        result["instructions"] = [
            "HC-05 must be wired to Arduino pins 0 (TX) and 1 (RX) for bootloader access",
            f"Upload via: arduino-cli upload --port {device} --fqbn arduino:avr:nano",
            "Manual reset: press Arduino RESET button when upload starts",
            "For auto-reset: toggle DTR via the serial port before upload",
        ]
        result["message"] = f"RFCOMM ready at {device}"
    else:
        result["message"] = rfcomm_result["message"]

    return result


def trigger_bootloader_reset(device: str = "/dev/rfcomm0") -> dict:
    """
    Trigger Arduino bootloader reset over Bluetooth.

    Sends a DTR toggle to restart the board into bootloader mode.
    Works if the HC-05 is wired to pins 0/1 and the Arduino
    has auto-reset enabled via the USB serial chip.

    For Nano clones with CH340, the reset may need to be
    triggered manually via the physical RESET button.

    Args:
        device: RFCOMM device path

    Returns:
        Status dict
    """
    result = {"success": False, "message": ""}

    try:
        import serial

        # Open at bootloader baudrate, toggle DTR
        ser = serial.Serial(
            port=device,
            baudrate=57600,
            timeout=2,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            dsrdtr=False,  # Start with DTR low
        )
        time.sleep(0.1)
        ser.set_dtr(True)    # DTR high
        time.sleep(0.25)
        ser.set_dtr(False)   # DTR low — triggers reset on many boards
        ser.close()

        result["success"] = True
        result["message"] = f"DTR toggle sent to {device}"

    except serial.SerialException as e:
        result["message"] = f"Serial error: {e}. Try manual reset button."
    except ImportError:
        result["message"] = "pyserial not installed. pip install pyserial"

    return result


def list_rfcomm_connections() -> dict:
    """List active RFCOMM connections."""
    result = {"connections": [], "active": []}
    try:
        stdout, stderr, code = _run_command(["rfcomm", "list"], timeout=5)
        if code == 0 and stdout.strip():
            for line in stdout.strip().split("\n"):
                match = re.match(r"(\S+):\s+(\S+):\s+(\d+):\s+(\w+)", line)
                if match:
                    device, mac, channel, status = match.groups()
                    info = {
                        "device": device,
                        "mac": mac,
                        "channel": int(channel),
                        "status": status,
                    }
                    result["connections"].append(info)
                    if status == "bound":
                        result["active"].append(info)
        return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        result["message"] = "rfcomm not available"
        return result


def _run_bluetoothctl(args: list[str], timeout: int = 10) -> Optional[str]:
    """Run bluetoothctl command and return stdout."""
    try:
        result = subprocess.run(
            ["bluetoothctl"] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _run_command(cmd: list[str], timeout: int = 10) -> tuple[str, str, int]:
    """Run command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout after {timeout}s", 1


if __name__ == "__main__":
    import json
    # List RFCOMM connections
    print(json.dumps(list_rfcomm_connections(), indent=2))
