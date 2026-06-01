"""
Arduino CLI wrapper for Arduino Vibe IDE.
Handles compilation, upload, board management, and library installation.
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Default arduino-cli path
ARDUINO_CLI = os.environ.get("ARDUINO_CLI", "/home/john/bin/arduino-cli")

# Default user data directory
ARDUINO_DATA_DIR = os.environ.get(
    "ARDUINO_DATA_DIR",
    os.path.expanduser("~/.arduino15")
)

# Default board configurations
BOARD_CONFIGS = {
    "nano": {
        "fqbn": "arduino:avr:nano",
        "cpu": "ATmega328P (Old Bootloader)",
        "variants": {
            "old_bootloader": "arduino:avr:nano",
            "new_bootloader": "arduino:avr:nano",
        },
    },
    "uno": {
        "fqbn": "arduino:avr:uno",
        "cpu": "ATmega328P",
    },
    "mega": {
        "fqbn": "arduino:avr:mega",
        "cpu": "ATmega2560",
    },
    "leonardo": {
        "fqbn": "arduino:avr:leonardo",
        "cpu": "ATmega32U4",
    },
    "micro": {
        "fqbn": "arduino:avr:micro",
        "cpu": "ATmega32U4",
    },
    "pro_micro": {
        "fqbn": "arduino:avr:promicro",
        "cpu": "ATmega32U4",
    },
}


@dataclass
class CompileResult:
    """Result of a compilation."""
    success: bool
    output: str = ""
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    binary_path: str = ""
    size_bytes: int = 0
    flash_usage_percent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "errors": self.errors,
            "warnings": self.warnings,
            "binary_path": self.binary_path,
            "size_bytes": self.size_bytes,
            "flash_usage_percent": self.flash_usage_percent,
        }


@dataclass
class UploadResult:
    """Result of an upload."""
    success: bool
    output: str = ""
    message: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "message": self.message,
            "error": self.error,
        }


def _find_arduino_cli() -> str:
    """Find arduino-cli binary."""
    candidates = [
        ARDUINO_CLI,
        "arduino-cli",
        "/usr/local/bin/arduino-cli",
        "/usr/bin/arduino-cli",
    ]
    for path in candidates:
        if shutil.which(path) or os.path.exists(path):
            return path
    return ARDUINO_CLI  # Return default even if not found (error will occur)


def _run_arduino_cli(args: list[str], timeout: int = 120) -> tuple[str, str, int]:
    """
    Run arduino-cli command.

    Returns:
        (stdout, stderr, return_code)
    """
    cli = _find_arduino_cli()
    cmd = [cli, "--json"] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "ARDUINO_DATA_DIR": ARDUINO_DATA_DIR},
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", f"arduino-cli not found at {cli}", 1
    except subprocess.TimeoutExpired:
        return "", f"arduino-cli timed out after {timeout}s", 2


def board_list() -> dict:
    """List available board platforms."""
    stdout, stderr, code = _run_arduino_cli(["board", "list", "all"])
    if code != 0:
        return {"boards": [], "error": stderr}

    try:
        data = json.loads(stdout)
        boards = []
        for item in data:
            boards.append({
                "fqbn": item.get("Fqbn", ""),
                "name": item.get("Name", ""),
                "port": item.get("Port", {}).get("Address", ""),
                "protocol": item.get("Port", {}).get("Protocol", ""),
                "type": item.get("Port", {}).get("Type", ""),
            })
        return {"boards": boards}
    except json.JSONDecodeError:
        return {"boards": [], "raw_output": stdout}


def board_detect(port: str = "") -> dict:
    """
    Detect Arduino board connected at port.
    Returns board FQBN and info.
    """
    stdout, stderr, code = _run_arduino_cli(["board", "list"])
    if code != 0:
        return {"detected": False, "error": stderr}

    try:
        data = json.loads(stdout)
        for item in data:
            p = item.get("Port")
            # Port can be a dict or a string (address only)
            port_addr = p.get("Address", p) if isinstance(p, dict) else (p or "")
            protocol = p.get("Protocol", "") if isinstance(p, dict) else ""
            if port and port_addr == port:
                return {
                    "detected": True,
                    "fqbn": item.get("Fqbn", ""),
                    "name": item.get("Name", ""),
                    "port": port_addr,
                    "protocol": protocol,
                }

        # If no specific port, return first detected Arduino
        for item in data:
            fqbn = item.get("Fqbn", "")
            if fqbn.startswith("arduino:"):
                p = item.get("Port")
                port_addr = p.get("Address", p) if isinstance(p, dict) else (p or "")
                return {
                    "detected": True,
                    "fqbn": fqbn,
                    "name": item.get("Name", ""),
                    "port": port_addr,
                }

        return {"detected": False, "message": "No Arduino board detected"}

    except json.JSONDecodeError:
        return {"detected": False, "raw_output": stdout}


def verify_board(port: str = "", fqbn: str = "") -> dict:
    """
    Verify a connected Arduino board.
    Returns board info and verification status.
    """
    result = board_detect(port)

    if result.get("detected"):
        detected_fqbn = result.get("fqbn", "")

        # Match against known configs
        for board_name, config in BOARD_CONFIGS.items():
            if board_name in detected_fqbn.lower() or config["fqbn"] in detected_fqbn:
                result["board_config"] = config
                result["verification"] = "verified"
                result["message"] = f"Verified: {config.get('cpu', 'Arduino board')}"
                return result

        result["verification"] = "recognized"
        result["message"] = f"Recognized as: {detected_fqbn}"
        return result

    if fqbn:
        result["detected"] = True
        result["fqbn"] = fqbn
        result["verification"] = "assumed"
        result["message"] = f"Assumed board: {fqbn}"
        return result

    return result


def compile_sketch(
    sketch_path: str,
    fqbn: str = "",
    port: str = "",
    extra_flags: list[str] = None,
) -> CompileResult:
    """
    Compile an Arduino sketch.

    Args:
        sketch_path: Path to .ino file or sketch directory
        fqbn: Board FQBN (e.g., "arduino:avr:nano"). If empty, auto-detect.
        port: Serial port for auto-detection
        extra_flags: Additional compiler flags

    Returns:
        CompileResult with success status and output
    """
    sketch_path = os.path.abspath(sketch_path)

    if not os.path.exists(sketch_path):
        return CompileResult(
            success=False,
            errors=[f"Sketch not found: {sketch_path}"],
        )

    # Auto-detect FQBN if not provided
    if not fqbn:
        detection = board_detect(port)
        if detection.get("detected"):
            fqbn = detection.get("fqbn", "arduino:avr:nano")
        else:
            fqbn = "arduino:avr:nano"  # Default fallback

    # Ensure core is installed
    _install_core("arduino:avr")

    # Build command
    args = ["compile", "--fqbn", fqbn]
    if extra_flags:
        for flag in extra_flags:
            args.extend(["--build-property", flag])
    args.append(sketch_path)

    stdout, stderr, code = _run_arduino_cli(args, timeout=180)

    result = CompileResult(
        success=code == 0,
        output=stdout + stderr,
    )

    # Parse output for useful info
    combined = stdout + stderr
    for line in combined.split("\n"):
        if "Sketch uses" in line:
            result.output = line.strip()
            # Extract size info
            size_match = line.split("bytes of")
            if len(size_match) > 1:
                try:
                    size_str = size_match[1].split(" ")[0]
                    result.size_bytes = int(size_str)
                except ValueError:
                    pass

        if "error:" in line or "Error:" in line:
            result.errors.append(line.strip())

        if "warning:" in line or "Warning:" in line:
            result.warnings.append(line.strip())

    # Check for binary output
    build_cache = os.path.join(
        ARDUINO_DATA_DIR, "cache", "arduino-cli", "sketches"
    )
    if os.path.exists(build_cache):
        for root, dirs, files in os.walk(build_cache):
            for f in files:
                if f.endswith(".elf") or f.endswith(".hex"):
                    result.binary_path = os.path.join(root, f)
                    if os.path.exists(result.binary_path):
                        result.size_bytes = os.path.getsize(result.binary_path)

    return result


def upload_sketch(
    sketch_path: str,
    fqbn: str = "",
    port: str = "",
) -> UploadResult:
    """
    Compile and upload an Arduino sketch.

    Args:
        sketch_path: Path to .ino file or sketch directory
        fqbn: Board FQBN
        port: Serial port for upload

    Returns:
        UploadResult with success status
    """
    sketch_path = os.path.abspath(sketch_path)

    # First compile
    compile_result = compile_sketch(sketch_path, fqbn, port)
    if not compile_result.success:
        return UploadResult(
            success=False,
            output=compile_result.output,
            message="Compilation failed",
            error="; ".join(compile_result.errors),
        )

    # Auto-detect FQBN if not provided
    if not fqbn:
        detection = board_detect(port)
        if detection.get("detected"):
            fqbn = detection.get("fqbn", "arduino:avr:nano")
        else:
            fqbn = "arduino:avr:nano"

    # Upload
    args = ["upload", "--fqbn", fqbn]
    if port:
        args.extend(["--port", port])
    args.append(sketch_path)

    stdout, stderr, code = _run_arduino_cli(args, timeout=180)

    combined = stdout + stderr
    success = code == 0

    message = ""
    error = ""
    for line in combined.split("\n"):
        if "Upload complete" in line or "Done uploading" in line:
            message = "Upload successful"
        if "error:" in line or "Error:" in line:
            error = line.strip()

    if success and not message:
        message = "Upload completed"

    return UploadResult(
        success=success,
        output=combined,
        message=message or f"Exit code: {code}",
        error=error,
    )


def install_library(library_name: str) -> dict:
    """
    Install an Arduino library from the library index.

    Args:
        library_name: Library name (e.g., "FastLED", "IRremote")

    Returns:
        Status dict
    """
    args = ["lib", "install", library_name]
    stdout, stderr, code = _run_arduino_cli(args, timeout=120)

    combined = stdout + stderr
    success = code == 0

    return {
        "success": success,
        "library": library_name,
        "output": combined,
        "status": "installed" if success else "error",
        "message": f"Library {library_name} installed" if success else f"Error: {combined}",
    }


def list_libraries() -> dict:
    """List installed Arduino libraries."""
    stdout, stderr, code = _run_arduino_cli(["lib", "list", "--json"])
    if code != 0:
        return {"libraries": [], "error": stderr}

    try:
        data = json.loads(stdout)
        libraries = []
        for item in data:
            libraries.append({
                "name": item.get("Name", ""),
                "version": item.get("Version", ""),
                "location": item.get("Location", ""),
                "authors": item.get("Authors", []),
                "sentence": item.get("Sentence", ""),
            })
        return {"libraries": libraries}
    except json.JSONDecodeError:
        return {"libraries": [], "raw_output": stdout}


def _install_core(fqbn_prefix: str = "arduino:avr") -> bool:
    """Install Arduino core if not present."""
    stdout, stderr, code = _run_arduino_cli(
        ["core", "update-index"], timeout=60
    )
    if code != 0:
        return False

    stdout, stderr, code = _run_arduino_cli(
        ["core", "install", fqbn_prefix], timeout=120
    )
    return code == 0


def board_manager_update() -> dict:
    """Update board manager index."""
    stdout, stderr, code = _run_arduino_cli(
        ["core", "update-index"], timeout=120
    )
    return {
        "success": code == 0,
        "output": stdout + stderr,
        "message": "Board manager updated" if code == 0 else f"Error: {stderr}",
    }


def search_library(query: str) -> dict:
    """Search Arduino library index."""
    stdout, stderr, code = _run_arduino_cli(
        ["lib", "search", query, "--json"], timeout=60
    )
    if code != 0:
        return {"results": [], "error": stderr}

    try:
        data = json.loads(stdout)
        results = []
        for item in data:
            results.append({
                "name": item.get("Name", ""),
                "version": item.get("Version", ""),
                "authors": item.get("Authors", []),
                "sentence": item.get("Sentence", ""),
                "paragraph": item.get("Paragraph", ""),
            })
        return {"results": results[:20]}
    except json.JSONDecodeError:
        return {"results": [], "raw_output": stdout}


def get_sketch_config(sketch_path: str) -> dict:
    """Get configuration info for a sketch."""
    sketch_path = os.path.abspath(sketch_path)
    config = {
        "path": sketch_path,
        "exists": os.path.exists(sketch_path),
        "is_directory": os.path.isdir(sketch_path),
        "files": [],
        "size_bytes": 0,
    }

    if os.path.isdir(sketch_path):
        for f in os.listdir(sketch_path):
            full = os.path.join(sketch_path, f)
            config["files"].append({
                "name": f,
                "size": os.path.getsize(full),
                "is_sketch": f.endswith(".ino"),
            })
            config["size_bytes"] += os.path.getsize(full)
    elif os.path.isfile(sketch_path):
        config["files"].append({"name": os.path.basename(sketch_path)})
        config["size_bytes"] = os.path.getsize(sketch_path)

    return config


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list-boards":
            print(json.dumps(board_list(), indent=2))
        elif cmd == "detect":
            port = sys.argv[2] if len(sys.argv) > 2 else ""
            print(json.dumps(board_detect(port), indent=2))
        elif cmd == "libraries":
            print(json.dumps(list_libraries(), indent=2))
        elif cmd == "compile" and len(sys.argv) > 2:
            result = compile_sketch(sys.argv[2])
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Usage: python compiler.py [list-boards|detect|libraries|compile <path>]")
    else:
        print(f"arduino-cli: {_find_arduino_cli()}")
        print(f"Data dir: {ARDUINO_DATA_DIR}")
