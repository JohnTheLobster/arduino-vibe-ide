"""
Project management for Arduino Vibe IDE.
Create, save, load, backup, and list Arduino projects.
"""

import json
import os
import shutil
import tarfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Default project directory
PROJECTS_DIR = os.environ.get(
    "ARDUINO_VIBE_PROJECTS",
    os.path.expanduser("~/projects/arduino-vibe-ide/projects")
)


@dataclass
class PinConfig:
    """Pin configuration for hardware."""
    pin: int
    name: str = ""
    function: str = ""  # "led_data", "sensor", "servo", etc.
    mode: str = "OUTPUT"  # "INPUT", "OUTPUT", "INPUT_PULLUP"
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PinConfig":
        return cls(**data)


@dataclass
class ProjectMetadata:
    """Arduino project metadata."""
    name: str
    description: str = ""
    board: str = "arduino:avr:nano"
    board_fqbn: str = "arduino:avr:nano"
    connection_type: str = "usb"  # "usb" | "bluetooth"
    device_path: str = ""
    bt_mac: str = ""
    bt_pin: str = ""
    bt_rfcord_channel: int = 1
    libraries: list = field(default_factory=list)
    pins: list = field(default_factory=list)
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    sketch_path: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "board": self.board,
            "board_fqbn": self.board_fqbn,
            "connection_type": self.connection_type,
            "device_path": self.device_path,
            "bt_mac": self.bt_mac,
            "bt_pin": self.bt_pin,
            "bt_rfcord_channel": self.bt_rfcord_channel,
            "libraries": self.libraries,
            "pins": [p.to_dict() if isinstance(p, PinConfig) else p for p in self.pins],
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sketch_path": self.sketch_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectMetadata":
        pins = []
        for p in data.get("pins", []):
            if isinstance(p, dict):
                pins.append(PinConfig.from_dict(p))
            else:
                pins.append(p)
        data["pins"] = pins
        return cls(**data)


class ArduinoProject:
    """Manages an Arduino Vibe IDE project."""

    def __init__(self, project_dir: str = PROJECTS_DIR):
        self.project_dir = os.path.abspath(project_dir)
        os.makedirs(self.project_dir, exist_ok=True)

    def create(self, name: str, **kwargs) -> dict:
        """
        Create a new project.

        Args:
            name: Project name
            **kwargs: board, description, libraries, pins, notes, etc.

        Returns:
            Project metadata dict
        """
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        project_path = os.path.join(self.project_dir, safe_name)

        # Create project structure
        sketch_dir = os.path.join(project_path, "sketch")
        os.makedirs(sketch_dir, exist_ok=True)
        os.makedirs(os.path.join(project_path, "backup"), exist_ok=True)

        now = datetime.now().isoformat()

        metadata = ProjectMetadata(
            name=name,
            description=kwargs.get("description", ""),
            board=kwargs.get("board", "arduino:avr:nano"),
            board_fqbn=kwargs.get("board_fqbn", "arduino:avr:nano"),
            connection_type=kwargs.get("connection_type", "usb"),
            device_path=kwargs.get("device_path", ""),
            bt_mac=kwargs.get("bt_mac", ""),
            bt_pin=kwargs.get("bt_pin", ""),
            libraries=kwargs.get("libraries", []),
            pins=[
                PinConfig.from_dict(p) if isinstance(p, dict) else p
                for p in kwargs.get("pins", [])
            ],
            notes=kwargs.get("notes", ""),
            created_at=now,
            updated_at=now,
            sketch_path=os.path.join(sketch_dir, f"{safe_name}.ino"),
        )

        # Save metadata
        meta_path = os.path.join(project_path, "project.json")
        with open(meta_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Create empty sketch
        sketch_path = metadata.sketch_path
        with open(sketch_path, "w") as f:
            f.write(_generate_default_sketch(name))

        return {
            "status": "created",
            "project_name": name,
            "project_dir": project_path,
            "sketch_path": sketch_path,
            "metadata": metadata.to_dict(),
        }

    def save(self, name: str, sketch_path: str = "", notes: str = "") -> dict:
        """
        Save/update project state.

        Args:
            name: Project name
            sketch_path: Path to sketch to save
            notes: Additional notes

        Returns:
            Status dict
        """
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        project_path = os.path.join(self.project_dir, safe_name)
        meta_path = os.path.join(project_path, "project.json")

        if not os.path.exists(meta_path):
            return {
                "status": "not_found",
                "message": f"Project not found: {name}",
            }

        with open(meta_path) as f:
            metadata = ProjectMetadata.from_dict(json.load(f))

        now = datetime.now().isoformat()
        metadata.updated_at = now
        if notes:
            metadata.notes = notes

        # Save sketch if provided
        if sketch_path and os.path.exists(sketch_path):
            dest = metadata.sketch_path
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(sketch_path, dest)

        # Update metadata
        with open(meta_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        return {
            "status": "saved",
            "project_name": name,
            "project_dir": project_path,
            "sketch_path": metadata.sketch_path,
            "updated_at": now,
        }

    def backup(self, name: str) -> dict:
        """
        Create a full backup of a project.

        Args:
            name: Project name

        Returns:
            Backup info with tarball path
        """
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        project_path = os.path.join(self.project_dir, safe_name)

        if not os.path.exists(project_path):
            return {
                "status": "not_found",
                "message": f"Project not found: {name}",
            }

        backup_dir = os.path.join(project_path, "backup")
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tarball_name = f"{safe_name}_{timestamp}.tar.gz"
        tarball_path = os.path.join(backup_dir, tarball_name)

        # Create tarball with project contents
        with tarfile.open(tarball_path, "w:gz") as tar:
            # Add sketch files
            sketch_dir = os.path.join(project_path, "sketch")
            if os.path.exists(sketch_dir):
                for root, dirs, files in os.walk(sketch_dir):
                    for f in files:
                        full_path = os.path.join(root, f)
                        arcname = os.path.relpath(full_path, project_path)
                        tar.add(full_path, arcname=arcname)

            # Add metadata
            meta_path = os.path.join(project_path, "project.json")
            if os.path.exists(meta_path):
                tar.add(meta_path, arcname="project.json")

            # Add notes file if exists
            notes_path = os.path.join(project_path, "notes.md")
            if os.path.exists(notes_path):
                tar.add(notes_path, arcname="notes.md")

            # Add library list
            lib_path = os.path.join(project_path, "libraries.txt")
            if os.path.exists(lib_path):
                tar.add(lib_path, arcname="libraries.txt")

        return {
            "status": "backed_up",
            "project_name": name,
            "backup_path": tarball_path,
            "backup_name": tarball_name,
            "size_bytes": os.path.getsize(tarball_path),
            "timestamp": timestamp,
        }

    def list_projects(self) -> dict:
        """
        List all projects.

        Returns:
            List of project summaries
        """
        projects = []

        if not os.path.exists(self.project_dir):
            return {"projects": [], "total": 0}

        for entry in sorted(os.listdir(self.project_dir)):
            project_path = os.path.join(self.project_dir, entry)
            meta_path = os.path.join(project_path, "project.json")

            if not os.path.isfile(meta_path):
                continue

            try:
                with open(meta_path) as f:
                    metadata = json.load(f)

                projects.append({
                    "name": metadata.get("name", entry),
                    "board": metadata.get("board", ""),
                    "connection_type": metadata.get("connection_type", ""),
                    "libraries": metadata.get("libraries", []),
                    "pins_count": len(metadata.get("pins", [])),
                    "created_at": metadata.get("created_at", ""),
                    "updated_at": metadata.get("updated_at", ""),
                    "path": project_path,
                    "has_sketch": os.path.exists(metadata.get("sketch_path", "")),
                })

            except (json.JSONDecodeError, KeyError):
                continue

        return {"projects": projects, "total": len(projects)}

    def load(self, name: str) -> dict:
        """
        Load a project.

        Args:
            name: Project name

        Returns:
            Full project data
        """
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        project_path = os.path.join(self.project_dir, safe_name)
        meta_path = os.path.join(project_path, "project.json")

        if not os.path.exists(meta_path):
            return {
                "status": "not_found",
                "message": f"Project not found: {name}",
            }

        with open(meta_path) as f:
            metadata = json.load(f)

        # Load sketch
        sketch_content = ""
        sketch_path = metadata.get("sketch_path", "")
        if os.path.exists(sketch_path):
            with open(sketch_path) as f:
                sketch_content = f.read()

        # Load notes
        notes_content = ""
        notes_path = os.path.join(project_path, "notes.md")
        if os.path.exists(notes_path):
            with open(notes_path) as f:
                notes_content = f.read()

        # List backups
        backups = []
        backup_dir = os.path.join(project_path, "backup")
        if os.path.exists(backup_dir):
            for f in sorted(os.listdir(backup_dir)):
                if f.endswith(".tar.gz"):
                    full = os.path.join(backup_dir, f)
                    backups.append({
                        "name": f,
                        "size": os.path.getsize(full),
                        "path": full,
                    })

        return {
            "status": "loaded",
            "metadata": metadata,
            "sketch": sketch_content,
            "notes": notes_content,
            "backups": backups,
            "project_dir": project_path,
        }

    def delete(self, name: str) -> dict:
        """Delete a project."""
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        project_path = os.path.join(self.project_dir, safe_name)

        if not os.path.exists(project_path):
            return {
                "status": "not_found",
                "message": f"Project not found: {name}",
            }

        shutil.rmtree(project_path)
        return {
            "status": "deleted",
            "project_name": name,
            "project_dir": project_path,
        }


def _generate_default_sketch(name: str) -> str:
    """Generate a default Arduino sketch template."""
    return f"""/**
 * {name}
 * Generated by Arduino Vibe IDE
 * Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
 */

void setup() {{
    Serial.begin(115200);
    // Initialize hardware here
    Serial.println("{{{name}}} initialized");
}}

void loop() {{
    // Main loop
    delay(100);
}}
"""


if __name__ == "__main__":
    import sys

    project = ArduinoProject()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            print(json.dumps(project.list_projects(), indent=2))
        elif cmd == "create" and len(sys.argv) > 2:
            result = project.create(sys.argv[2])
            print(json.dumps(result, indent=2))
        else:
            print(f"Usage: python project.py [list|create <name>]")
    else:
        print(f"Projects directory: {PROJECTS_DIR}")
