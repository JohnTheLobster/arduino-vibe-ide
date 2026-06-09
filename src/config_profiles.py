"""
Configuration Profiles for Arduino Vibe IDE.
Manage multiple hardware configurations for different projects and setups.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

PROFILES_DIR = os.path.expanduser("~/.arduino-vibe/profiles")
DEFAULT_PROFILE = "default"

_SAFE_PROFILE_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def _safe_profile_name(name: str) -> str:
    """Sanitize a profile name for filesystem use, rejecting traversal."""
    if not name or not name.strip():
        raise ValueError("Profile name cannot be empty")
    cleaned = _SAFE_PROFILE_RE.sub("", name.strip())
    if not cleaned:
        raise ValueError(f"Profile name '{name}' has no valid characters")
    return cleaned


@dataclass
class HardwareProfile:
    """A named hardware configuration profile."""
    name: str
    board_fqbn: str
    board_name: str = ""
    connection_type: str = "usb"
    usb_port: str = ""
    bluetooth_mac: str = ""
    bluetooth_pin: str = ""
    baudrate: int = 115200
    led_pin: int = -1
    num_leds: int = 0
    led_type: str = ""
    custom_pins: dict = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict) -> "HardwareProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ConfigProfiles:
    """File-backed CRUD store for hardware profiles."""

    def __init__(self, profiles_dir: str = PROFILES_DIR):
        self.profiles_dir = Path(profiles_dir).resolve()
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        default_path = self.profiles_dir / f"{DEFAULT_PROFILE}.yaml"
        if not default_path.exists():
            self.create_profile(
                name=DEFAULT_PROFILE,
                board_fqbn="arduino:avr:nano",
                board_name="Arduino Nano",
            )

    def _profile_path(self, name: str) -> Path:
        safe = _safe_profile_name(name)
        path = (self.profiles_dir / f"{safe}.yaml").resolve()
        # Reject paths that escape the profiles directory.
        if self.profiles_dir not in path.parents:
            raise ValueError(f"Resolved path escapes profiles_dir: {name}")
        return path

    def create_profile(self, name: str, board_fqbn: str, **kwargs) -> dict:
        try:
            path = self._profile_path(name)
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        profile = HardwareProfile(name=name, board_fqbn=board_fqbn, **kwargs)
        with open(path, "w") as f:
            yaml.dump(profile.to_dict(), f, default_flow_style=False)
        return {"status": "created", "name": name}

    def get_profile(self, name: str = DEFAULT_PROFILE) -> Optional[dict]:
        try:
            path = self._profile_path(name)
        except ValueError:
            return None
        if not path.exists():
            return None
        with open(path) as f:
            return yaml.safe_load(f)

    def update_profile(self, name: str, **updates) -> dict:
        """Update fields of an existing profile. Unknown/None values are dropped."""
        data = self.get_profile(name)
        if not data:
            return {"status": "error", "message": f"Profile '{name}' not found"}
        valid_fields = set(HardwareProfile.__dataclass_fields__.keys())
        clean_updates = {k: v for k, v in updates.items() if k in valid_fields and v is not None}
        data.update(clean_updates)
        try:
            path = self._profile_path(name)
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        return {"status": "updated", "name": name, "applied": list(clean_updates.keys())}

    def delete_profile(self, name: str) -> dict:
        if name == DEFAULT_PROFILE:
            return {"status": "error", "message": "Cannot delete default profile"}
        try:
            path = self._profile_path(name)
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        if not path.exists():
            return {"status": "error", "message": f"Profile '{name}' not found"}
        path.unlink()
        return {"status": "deleted", "name": name}

    def list_profiles(self) -> dict:
        profiles = []
        for path in sorted(self.profiles_dir.glob("*.yaml")):
            name = path.stem
            data = self.get_profile(name)
            if data:
                profiles.append({
                    "name": name,
                    "board_fqbn": data.get("board_fqbn", ""),
                    "board_name": data.get("board_name", ""),
                    "connection_type": data.get("connection_type", "usb"),
                })
        return {"profiles": profiles, "count": len(profiles)}

    def set_active(self, name: str) -> dict:
        data = self.get_profile(name)
        if not data:
            return {"status": "error", "message": f"Profile '{name}' not found"}
        (self.profiles_dir / "active").write_text(_safe_profile_name(name))
        return {"status": "active", "name": name}

    def get_active(self) -> str:
        p = self.profiles_dir / "active"
        if not p.exists():
            return DEFAULT_PROFILE
        return p.read_text().strip() or DEFAULT_PROFILE


def register_profile_tools(mcp):
    """Register hardware-profile MCP tools on the given FastMCP server."""
    _profiles = ConfigProfiles()

    @mcp.tool()
    def profile_list() -> dict:
        """List all hardware configuration profiles."""
        return _profiles.list_profiles()

    @mcp.tool()
    def profile_get(name: str = "default") -> dict:
        """Get a hardware configuration profile by name."""
        data = _profiles.get_profile(name)
        if data:
            return {"status": "success", "profile": data}
        return {"status": "error", "message": f"Profile '{name}' not found"}

    @mcp.tool()
    def profile_create(name: str, board_fqbn: str, board_name: str = "") -> dict:
        """Create a new hardware configuration profile."""
        return _profiles.create_profile(name, board_fqbn, board_name=board_name)

    @mcp.tool()
    def profile_update(
        name: str,
        board_fqbn: str = "",
        board_name: str = "",
        connection_type: str = "",
        usb_port: str = "",
        bluetooth_mac: str = "",
        bluetooth_pin: str = "",
        baudrate: int = 0,
        led_pin: int = -2,
        num_leds: int = -1,
        led_type: str = "",
        notes: str = "",
    ) -> dict:
        """Update fields of an existing hardware profile.

        Pass only the fields you want to change. Empty strings, 0 baudrate,
        led_pin=-2, and num_leds=-1 are treated as 'unchanged'.
        """
        updates: dict = {}
        if board_fqbn:
            updates["board_fqbn"] = board_fqbn
        if board_name:
            updates["board_name"] = board_name
        if connection_type:
            updates["connection_type"] = connection_type
        if usb_port:
            updates["usb_port"] = usb_port
        if bluetooth_mac:
            updates["bluetooth_mac"] = bluetooth_mac
        if bluetooth_pin:
            updates["bluetooth_pin"] = bluetooth_pin
        if baudrate:
            updates["baudrate"] = baudrate
        if led_pin != -2:
            updates["led_pin"] = led_pin
        if num_leds >= 0:
            updates["num_leds"] = num_leds
        if led_type:
            updates["led_type"] = led_type
        if notes:
            updates["notes"] = notes
        return _profiles.update_profile(name, **updates)

    @mcp.tool()
    def profile_delete(name: str) -> dict:
        """Delete a hardware configuration profile."""
        return _profiles.delete_profile(name)

    @mcp.tool()
    def profile_set_active(name: str) -> dict:
        """Set the active hardware configuration profile."""
        return _profiles.set_active(name)

    @mcp.tool()
    def profile_get_active() -> dict:
        """Get the currently active hardware configuration profile."""
        name = _profiles.get_active()
        return {"active": name, "profile": _profiles.get_profile(name)}
