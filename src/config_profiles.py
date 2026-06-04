"""
Configuration Profiles for Arduino Vibe IDE.
Manage multiple hardware configurations for different projects and setups.
"""
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROFILES_DIR = os.path.expanduser("~/.arduino-vibe/profiles")
DEFAULT_PROFILE = "default"

@dataclass
class HardwareProfile:
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
    def __init__(self, profiles_dir: str = PROFILES_DIR):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        default_path = self.profiles_dir / f"{DEFAULT_PROFILE}.yaml"
        if not default_path.exists():
            self.create_profile(name=DEFAULT_PROFILE, board_fqbn="arduino:avr:nano", board_name="Arduino Nano")
    def _profile_path(self, name: str) -> Path:
        return self.profiles_dir / f"{name}.yaml"
    def create_profile(self, name: str, board_fqbn: str, **kwargs) -> dict:
        profile = HardwareProfile(name=name, board_fqbn=board_fqbn, **kwargs)
        with open(self._profile_path(name), "w") as f:
            yaml.dump(profile.to_dict(), f, default_flow_style=False)
        return {"status": "created", "name": name}
    def get_profile(self, name: str = DEFAULT_PROFILE) -> Optional[dict]:
        path = self._profile_path(name)
        if not path.exists(): return None
        with open(path) as f: return yaml.safe_load(f)
    def update_profile(self, name: str, **updates) -> dict:
        data = self.get_profile(name)
        if not data: return {"status": "error", "message": f"Profile '{name}' not found"}
        data.update(updates)
        with open(self._profile_path(name), "w") as f: yaml.dump(data, f, default_flow_style=False)
        return {"status": "updated", "name": name}
    def delete_profile(self, name: str) -> dict:
        if name == DEFAULT_PROFILE: return {"status": "error", "message": "Cannot delete default profile"}
        path = self._profile_path(name)
        if not path.exists(): return {"status": "error", "message": f"Profile '{name}' not found"}
        path.unlink()
        return {"status": "deleted", "name": name}
    def list_profiles(self) -> dict:
        profiles = []
        for path in sorted(self.profiles_dir.glob("*.yaml")):
            name = path.stem
            data = self.get_profile(name)
            if data: profiles.append({"name": name, "board_fqbn": data.get("board_fqbn",""), "board_name": data.get("board_name",""), "connection_type": data.get("connection_type","usb")})
        return {"profiles": profiles, "count": len(profiles)}
    def set_active(self, name: str) -> dict:
        data = self.get_profile(name)
        if not data: return {"status": "error", "message": f"Profile '{name}' not found"}
        (self.profiles_dir / "active").write_text(name)
        return {"status": "active", "name": name}
    def get_active(self) -> str:
        p = self.profiles_dir / "active"
        return p.read_text().strip() if p.exists() else DEFAULT_PROFILE

def register_profile_tools(mcp):
    _profiles = ConfigProfiles()
    @mcp.tool()
    def profile_list() -> dict:
        """List all hardware configuration profiles."""
        return _profiles.list_profiles()
    @mcp.tool()
    def profile_get(name: str = "default") -> dict:
        """Get a hardware configuration profile by name."""
        data = _profiles.get_profile(name)
        return {"status": "success", "profile": data} if data else {"status": "error", "message": f"Profile '{name}' not found"}
    @mcp.tool()
    def profile_create(name: str, board_fqbn: str, board_name: str = "") -> dict:
        """Create a new hardware configuration profile."""
        return _profiles.create_profile(name, board_fqbn, board_name=board_name)
    @mcp.tool()
    def profile_update(name: str, **updates) -> dict:
        """Update an existing hardware configuration profile."""
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