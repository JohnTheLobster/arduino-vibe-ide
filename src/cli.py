#!/usr/bin/env python3
"""
Arduino Vibe IDE — CLI Wizard & Interactive Tool.

Usage:
    arduino-vibe init              Run setup wizard
    arduino-vibe discover          List devices
    arduino-vibe connect --device  Connect to device
    arduino-vibe terminal          Serial terminal
    arduino-vibe sketch "prompt"   Generate sketch
    arduino-vibe upload            Upload sketch
    arduino-vibe project create|save|backup|list|load
    arduino-vibe backup            Quick backup
"""

import json
import os
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.status import Status
from rich import box

# Add src to path
_src_dir = Path(__file__).parent
sys.path.insert(0, str(_src_dir))

from devices import (
    discover_all_devices, scan_usb_serial_ports, scan_bluetooth_devices,
    DeviceInfo, check_modules,
)
from serial_terminal import SerialTerminal
from compiler import (
    compile_sketch, upload_sketch, install_library, list_libraries,
    verify_board, board_detect, board_list,
)
from project import ArduinoProject, PinConfig
from sketch_generator import (
    generate_sketch_from_prompt, build_led_command, LED_PRESET_COLORS,
)

console = Console()
_terminal = SerialTerminal()
_project_mgr = ArduinoProject()


# ─── Banner ───────────────────────────────────────────────────────

def show_banner():
    """Display the Arduino Vibe IDE banner."""
    banner = """
    ╔══════════════════════════════════════════╗
    ║   ⚡  Arduino Vibe IDE  v1.0.0  ⚡       ║
    ║   AI-Powered Hardware Vibe Coding        ║
    ╚══════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


# ─── Helpers ──────────────────────────────────────────────────────

def device_table(devices: list[DeviceInfo]) -> Table:
    """Create a rich table for device listing."""
    table = Table(
        title="Discovered Devices",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("ID", style="cyan", width=20)
    table.add_column("Type", style="green", width=12)
    table.add_column("Name", width=25)
    table.add_column("Path", style="yellow", width=20)
    table.add_column("Board", width=18)
    table.add_column("Status", style="bold")

    for i, dev in enumerate(devices, 1):
        status = "✅" if dev.path and not dev.path.startswith("bt:bluetoothctl") else "⚠️"
        type_label = "🔌 USB" if dev.device_type == "usb_serial" else "📡 BT"
        board = dev.board_hint or dev.board_hint or "—"

        table.add_row(
            str(i),
            dev.device_id,
            type_label,
            dev.name or "—",
            dev.path or "—",
            board,
            status,
        )

    return table


def sketch_display(code: str, max_lines: int = 30):
    """Display generated sketch with syntax highlighting."""
    lines = code.split("\n")
    if len(lines) > max_lines:
        display_code = "\n".join(lines[:max_lines]) + f"\n// ... ({len(lines) - max_lines} more lines)"
    else:
        display_code = code

    syntax = Syntax(display_code, "cpp", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="📝 Generated Sketch", border_style="green"))


# ─── Commands ─────────────────────────────────────────────────────

@click.group()
def cli():
    """Arduino Vibe IDE — AI-powered hardware vibe coding."""
    pass


@cli.command(name="init")
def run_setup_wizard():
    """Interactive setup wizard for Arduino Vibe IDE."""
    console.print()
    console.print(Panel(
        "[bold cyan]⚡ Arduino Vibe IDE — Setup Wizard[/bold cyan]\n\n"
        "[dim]Configure your hardware connection and start vibe coding.[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))
    console.print()

    # Step 1: Connection type
    console.print("[bold yellow]Step 1/4:[/bold yellow] [bold]Connection Type[/bold]")
    console.print("  [dim]How is your Arduino connected?[/dim]")
    console.print("  [cyan](1) USB Serial[/cyan]    [magenta](2) Bluetooth HC-05[/magenta]")

    conn_type = Prompt.ask(
        "  Select connection type",
        default="1",
        choices=["1", "2"],
    )
    is_bluetooth = conn_type == "2"

    # Step 2: Device discovery
    console.print()
    console.print("[bold yellow]Step 2/4:[/bold yellow] [bold]Device Discovery[/bold]")
    console.print("  [dim]Scanning for Arduino devices...[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning USB ports...", total=None)

        if not is_bluetooth:
            usb_devices = scan_usb_serial_ports()
            progress.update(task, description="[green]Found USB devices")
            time.sleep(0.5)
            all_devices = usb_devices
        else:
            progress.update(task, description="[cyan]Scanning Bluetooth...")
            bt_devices = scan_bluetooth_devices()
            progress.update(task, description="[green]Found Bluetooth devices")
            time.sleep(0.5)
            all_devices = bt_devices

    if all_devices:
        table = device_table(all_devices)
        console.print(table)
        console.print()

        choice = IntPrompt.ask(
            "  Select device",
            default=1,
            choices=[str(i) for i in range(1, len(all_devices) + 1)],
        )
        selected = all_devices[choice - 1]

        console.print(f"  [green]✓ Selected:[/green] [cyan]{selected.name}[/cyan] "
                      f"([yellow]{selected.path}[/yellow])")
    else:
        console.print("  [yellow]⚠ No devices found[/yellow]")
        selected = DeviceInfo(
            device_id="manual",
            device_type="usb_serial" if not is_bluetooth else "bluetooth",
            path="",
            name="Manual Configuration",
        )

    # Step 3: Board verification
    console.print()
    console.print("[bold yellow]Step 3/4:[/bold yellow] [bold]Board Verification[/bold]")

    board_options = {
        "1": "Arduino Nano (clone)",
        "2": "Arduino Uno",
        "3": "Arduino Mega 2560",
        "4": "Arduino Leonardo",
        "5": "Arduino Micro",
        "6": "Other (specify FQBN)",
    }

    console.print("  [dim]Select your board type:[/dim]")
    for k, v in board_options.items():
        style = "cyan" if k == "1" else "dim"
        console.print(f"  [{style}]{k}[/] {v}")

    board_choice = Prompt.ask(
        "  Select board",
        default="1",
        choices=list(board_options.keys()),
    )

    board_fqbn_map = {
        "1": "arduino:avr:nano",
        "2": "arduino:avr:uno",
        "3": "arduino:avr:mega",
        "4": "arduino:avr:leonardo",
        "5": "arduino:avr:micro",
    }

    if board_choice == "6":
        board_fqbn = Prompt.ask("  Enter board FQBN", default="arduino:avr:nano")
    else:
        board_fqbn = board_fqbn_map.get(board_choice, "arduino:avr:nano")

    # Try to verify
    if selected.path and selected.path != "manual":
        console.print("  [dim]Verifying board connection...[/dim]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Checking board...", total=None)
            verification = verify_board(port=selected.path, fqbn=board_fqbn)
            progress.update(task, description="[green]Verification complete")
            time.sleep(0.5)

        if verification.get("verification") in ("verified", "recognized"):
            console.print(f"  [green]✓ Board verified:[/green] {verification.get('message', 'Arduino board')}")
        elif verification.get("verification") == "assumed":
            console.print(f"  [yellow]⚠ Board assumed:[/yellow] {board_fqbn}")
        else:
            console.print(f"  [yellow]⚠ Board detection:[/yellow] {verification.get('message', 'Unknown')}")
    else:
        console.print(f"  [dim]Board:[/dim] [cyan]{board_fqbn}[/cyan] [dim](manual config)[/dim]")

    # Step 4: Module detection
    console.print()
    console.print("[bold yellow]Step 4/4:[/bold yellow] [bold]Module Detection[/bold]")

    if selected.path and selected.path not in ("manual", ""):
        if Confirm.ask("  Scan for connected modules (HC-05, sensors, etc.)?", default=True):
            console.print("  [dim]Probing device...[/dim]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Checking modules...", total=None)
                modules = check_modules(selected.path)
                progress.update(task, description="[green]Scan complete")
                time.sleep(0.5)

            if modules.get("modules"):
                console.print("  [green]✓ Detected modules:[/green]")
                for mod in modules["modules"]:
                    mod_type = mod.get("type", "Unknown")
                    mod_status = mod.get("status", "")
                    console.print(f"    [cyan]• {mod_type}[/cyan] — {mod_status}")
                    if "version" in mod:
                        console.print(f"      [dim]Version: {mod['version']}[/dim]")
                    if "name" in mod:
                        console.print(f"      [dim]Name: {mod['name']}[/dim]")
            else:
                console.print("  [yellow]⚠ No modules detected[/yellow]")
        else:
            console.print("  [dim]Module scan skipped[/dim]")
    else:
        console.print("  [dim]Module scan: skipped (no device selected)[/dim]")

    # Results summary
    console.print()
    summary = Table(box=box.ROUNDED, title="✅ Setup Complete", title_style="bold green")
    summary.add_column("Setting", style="cyan", width=18)
    summary.add_column("Value", style="white")

    summary.add_row("Connection", "Bluetooth" if is_bluetooth else "USB Serial")
    summary.add_row("Device", selected.name or "Manual")
    if selected.path:
        summary.add_row("Device Path", selected.path)
    summary.add_row("Board", board_fqbn)
    if selected.mac_address:
        summary.add_row("BT MAC", selected.mac_address)
    if selected.bt_pin:
        summary.add_row("BT PIN", selected.bt_pin)

    console.print(summary)

    # Save config
    config = {
        "connection_type": "bluetooth" if is_bluetooth else "usb",
        "device_path": selected.path,
        "device_name": selected.name,
        "board_fqbn": board_fqbn,
        "bt_mac": selected.mac_address,
        "bt_pin": selected.bt_pin,
    }

    config_path = _src_dir.parent / "config.yaml"
    try:
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        console.print(f"\n  [green]✓ Config saved:[/green] {config_path}")
    except ImportError:
        # Fallback to JSON
        config_json = _src_dir.parent / "config.json"
        with open(config_json, "w") as f:
            json.dump(config, f, indent=2)
        console.print(f"\n  [green]✓ Config saved:[/green] {config_json}")

    console.print("\n[dim]Ready to vibe code! Run:[/dim] [cyan]arduino-vibe sketch \"your idea\"[/cyan]\n")


@cli.command(name="discover")
def discover_devices():
    """Discover and list all Arduino-compatible devices."""
    console.print()
    console.print(Panel(
        "[bold cyan]🔍 Device Discovery[/bold cyan]\n\n"
        "[dim]Scanning for Arduino-compatible devices...[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning USB serial ports...", total=None)
        usb_devices = scan_usb_serial_ports()
        progress.update(task, description="[green]USB scan complete")
        time.sleep(0.3)

        task = progress.add_task("[cyan]Scanning Bluetooth devices...", total=None)
        bt_devices = scan_bluetooth_devices()
        progress.update(task, description="[green]Bluetooth scan complete")
        time.sleep(0.3)

    all_devices = usb_devices + bt_devices

    if all_devices:
        console.print()
        table = device_table(all_devices)
        console.print(table)
        console.print(f"\n[dim]Total: {len(all_devices)} devices found "
                      f"({len(usb_devices)} USB, {len(bt_devices)} BT)[/dim]")
    else:
        console.print("\n[yellow]⚠ No devices found[/yellow]")
        console.print("[dim]Check connections and try again.[/dim]")


@cli.command(name="connect")
@click.option("--device", "-d", help="Device ID or path to connect to")
@click.option("--baudrate", "-b", default=115200, help="Baud rate")
def connect_device(device: str, baudrate: int):
    """Connect to an Arduino device."""
    global _terminal

    if not device:
        # Interactive selection
        all_devices = discover_all_devices()
        if all_devices:
            table = device_table(all_devices)
            console.print(table)
            choice = IntPrompt.ask(
                "  Select device",
                choices=[str(i) for i in range(1, len(all_devices) + 1)],
            )
            device = all_devices[choice - 1].path
        else:
            console.print("[yellow]⚠ No devices found. Run: arduino-vibe discover[/yellow]")
            return

    console.print()
    console.print(f"  [dim]Connecting to [/dim][cyan]{device}[/cyan] [dim]at {baudrate} baud...[/dim]")

    _terminal = SerialTerminal()
    result = _terminal.open(device, baudrate)

    if result["status"] == "connected":
        console.print(f"  [green]✓ Connected![/green] [dim]({device}, {baudrate} baud)[/dim]")
    else:
        console.print(f"  [red]✗ Connection failed:[/red] {result['message']}")


@cli.command(name="terminal")
@click.option("--device", "-d", help="Device path")
@click.option("--baudrate", "-b", default=115200, help="Baud rate")
def serial_terminal_cmd(device: str, baudrate: int):
    """Open an interactive serial terminal."""
    global _terminal

    if not device:
        device = "/dev/ttyACM0"
        console.print(f"  [dim]Using default device:[/dim] [cyan]{device}[/cyan]")

    _terminal = SerialTerminal()
    result = _terminal.open(device, baudrate)

    if result["status"] != "connected":
        console.print(f"  [red]✗ Connection failed:[/red] {result['message']}")
        return

    console.print(Panel(
        f"[green]Connected to {device} at {baudrate} baud[/green]\n\n"
        "[dim]Type commands and press Enter. Press Ctrl+C to exit.[/dim]",
        border_style="green",
        box=box.ROUNDED,
    ))

    try:
        while True:
            line = Prompt.ask("[bold]>>>" )
            if line == "exit" or line == "quit":
                break

            write_result = _terminal.write(line + "\n")
            if write_result["status"] == "sent":
                console.print(f"  [dim]sent: {line}[/dim]")

            # Read response
            resp = _terminal.read(256)
            if resp["status"] == "received" and resp["data"]:
                data = resp["data"].rstrip()
                for d_line in data.split("\n"):
                    if d_line.strip():
                        console.print(f"  [green]{d_line}[/green]")

    except KeyboardInterrupt:
        console.print("\n[dim]Terminal closed.[/dim]")

    _terminal.close()


@cli.command(name="sketch")
@click.argument("prompt", required=False)
@click.option("--board", "-b", default="arduino:avr:nano", help="Target board FQBN")
@click.option("--led-pin", default=6, help="LED data pin")
@click.option("--num-leds", default=288, help="Number of LEDs")
@click.option("--led-type", default="SK6812", help="LED type (SK6812, WS2812B, NEOPIXEL)")
@click.option("--output", "-o", help="Output file path")
def generate_sketch_cmd(
    prompt: str, board: str, led_pin: int, num_leds: int,
    led_type: str, output: str
):
    """Generate an Arduino sketch from a prompt."""
    if not prompt:
        prompt = Prompt.ask(
            "Describe your Arduino project",
            default="LED controller with FastLED and SK6812",
        )

    console.print()
    console.print(Panel(
        f"[bold cyan]🤖 Generating Sketch[/bold cyan]\n\n"
        f"[dim]Prompt:[/dim] [cyan]{prompt}[/cyan]\n"
        f"[dim]Board:[/dim] [yellow]{board}[/yellow]",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    hardware_context = {
        "led_pin": led_pin,
        "num_leds": num_leds,
        "led_type": led_type,
    }

    with Status("Generating sketch...", spinner="dots"):
        sketch = generate_sketch_from_prompt(
            prompt=prompt,
            board=board,
            hardware_context=hardware_context,
        )
        time.sleep(0.5)

    if output:
        output_path = os.path.abspath(output)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(sketch)
        console.print(f"\n  [green]✓ Saved to:[/green] {output_path}")

    sketch_display(sketch)
    console.print(f"\n[dim]Sketch size: {len(sketch)} bytes[/dim]\n")


@cli.command(name="compile")
@click.argument("sketch_path")
@click.option("--fqbn", "-f", default="", help="Board FQBN")
@click.option("--port", "-p", default="", help="Serial port")
def compile_sketch_cmd(sketch_path: str, fqbn: str, port: str):
    """Compile an Arduino sketch."""
    console.print()
    console.print(f"  [dim]Compiling:[/dim] [cyan]{sketch_path}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Compiling sketch...", total=None)
        result = compile_sketch(sketch_path, fqbn, port)
        progress.update(task, description="[green]Compilation complete")
        time.sleep(0.3)

    if result.success:
        console.print(f"  [green]✓ Compilation successful![/green]")
        if result.size_bytes:
            console.print(f"  [dim]Binary size:[/dim] [cyan]{result.size_bytes} bytes[/cyan]")
        if result.output:
            console.print(f"  [dim]Output:[/dim] {result.output[:200]}")
    else:
        console.print(f"  [red]✗ Compilation failed:[/red]")
        for error in result.errors:
            console.print(f"    [red]{error}[/red]")
        if result.output:
            console.print(f"\n  [dim]Full output:[/dim]")
            console.print(result.output[:500])


@cli.command(name="upload")
@click.argument("sketch_path", required=False)
@click.option("--fqbn", "-f", default="", help="Board FQBN")
@click.option("--port", "-p", default="", help="Serial port")
def upload_sketch_cmd(sketch_path: str, fqbn: str, port: str):
    """Compile and upload an Arduino sketch."""
    if not sketch_path:
        sketch_path = Prompt.ask("Sketch path (.ino file or directory)")

    console.print()
    console.print(f"  [dim]Uploading:[/dim] [cyan]{sketch_path}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Compiling and uploading...", total=None)
        result = upload_sketch(sketch_path, fqbn, port)
        if result.success:
            progress.update(task, description="[green]Upload complete")
        else:
            progress.update(task, description="[red]Upload failed")
        time.sleep(0.3)

    if result.success:
        console.print(f"\n  [green]✓ Upload successful![/green]")
        if result.message:
            console.print(f"  [dim]{result.message}[/dim]")
    else:
        console.print(f"\n  [red]✗ Upload failed:[/red] {result.error}")
        if result.output:
            console.print(f"\n  [dim]Output:[/dim]")
            console.print(result.output[:500])


@cli.command(name="verify")
@click.option("--port", "-p", default="", help="Serial port")
@click.option("--fqbn", "-f", default="", help="Board FQBN")
def verify_board_cmd(port: str, fqbn: str):
    """Verify a connected Arduino board."""
    console.print()
    console.print(Panel(
        "[bold cyan]🔍 Board Verification[/bold cyan]\n\n"
        "[dim]Checking connected Arduino board...[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    result = verify_board(port=port, fqbn=fqbn)

    if result.get("detected"):
        table = Table(box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("FQBN", result.get("fqbn", "—"))
        table.add_row("Name", result.get("name", "—"))
        table.add_row("Port", result.get("port", "—"))
        table.add_row("Protocol", result.get("protocol", "—"))
        table.add_row("Verification", result.get("verification", "—"))
        table.add_row("Message", result.get("message", "—"))

        console.print(table)
    else:
        console.print(f"\n  [yellow]⚠ No board detected[/yellow]")
        if result.get("error"):
            console.print(f"  [dim]{result['error']}[/dim]")


@cli.command(name="modules")
@click.argument("device_path")
def check_modules_cmd(device_path: str):
    """Check connected modules (HC-05, sensors, etc.)."""
    console.print()
    console.print(f"  [dim]Probing device:[/dim] [cyan]{device_path}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning for modules...", total=None)
        result = check_modules(device_path)
        progress.update(task, description="[green]Scan complete")
        time.sleep(0.3)

    if result.get("modules"):
        console.print("\n  [green]✓ Detected modules:[/green]")
        for mod in result["modules"]:
            console.print(f"    [cyan]• {mod.get('type', 'Unknown')}[/cyan]")
            for k, v in mod.items():
                if k != "type":
                    console.print(f"      [dim]{k}:[/dim] {v}")
    else:
        console.print("\n  [yellow]⚠ No modules detected[/yellow]")

    if result.get("i2c_modules"):
        console.print("\n  [green]✓ I2C devices:[/green]")
        for mod in result["i2c_modules"]:
            console.print(f"    [cyan]• {mod.get('name', 'Unknown')}[/cyan] [dim]({mod.get('address', '?')})[/dim]")


@cli.command(name="library")
@click.argument("name")
def install_library_cmd(name: str):
    """Install an Arduino library."""
    console.print()
    console.print(f"  [dim]Installing library:[/dim] [cyan]{name}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Installing {name}...", total=None)
        result = install_library(name)
        if result.get("success"):
            progress.update(task, description=f"[green]Installed {name}")
        else:
            progress.update(task, description=f"[red]Install failed")
        time.sleep(0.3)

    if result.get("success"):
        console.print(f"\n  [green]✓ Library installed:[/green] {name}")
    else:
        console.print(f"\n  [red]✗ Install failed:[/red] {result.get('message', 'Unknown error')}")


@cli.command(name="libraries")
def list_libraries_cmd():
    """List installed Arduino libraries."""
    result = list_libraries()

    if result.get("libraries"):
        table = Table(
            title="Installed Libraries",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="yellow")
        table.add_column("Description", width=40)

        for lib in result["libraries"]:
            table.add_row(
                lib.get("name", "—"),
                lib.get("version", "—"),
                lib.get("sentence", "—")[:50],
            )

        console.print(table)
    else:
        console.print("[yellow]⚠ No libraries found or arduino-cli error[/yellow]")


# ─── Project Management ───────────────────────────────────────────

@click.group(name="project")
def project_cli():
    """Manage Arduino Vibe IDE projects."""
    pass


@project_cli.command(name="create")
@click.option("--name", "-n", prompt="Project name", help="Project name")
@click.option("--board", "-b", default="arduino:avr:nano", help="Board FQBN")
@click.option("--description", "-d", default="", help="Description")
@click.option("--library", "-l", multiple=True, help="Required libraries")
@click.option("--notes", default="", help="Project notes")
def project_create(name: str, board: str, description: str, library: tuple, notes: str):
    """Create a new project."""
    console.print()
    console.print(Panel(
        f"[bold cyan]📦 New Project: {name}[/bold cyan]\n\n"
        f"[dim]Board:[/dim] [yellow]{board}[/yellow]",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    result = _project_mgr.create(
        name=name,
        board=board,
        board_fqbn=board,
        description=description,
        libraries=list(library),
        notes=notes,
    )

    if result.get("status") == "created":
        console.print(f"\n  [green]✓ Project created![/green]")
        console.print(f"  [dim]Directory:[/dim] [cyan]{result['project_dir']}[/cyan]")
        console.print(f"  [dim]Sketch:[/dim] [cyan]{result['sketch_path']}[/cyan]")
    else:
        console.print(f"\n  [red]✗ Error:[/red] {result}")


@project_cli.command(name="save")
@click.option("--name", "-n", prompt="Project name", help="Project name")
@click.option("--sketch", "-s", default="", help="Sketch file path")
@click.option("--notes", default="", help="Notes to append")
def project_save(name: str, sketch: str, notes: str):
    """Save project state."""
    result = _project_mgr.save(name, sketch, notes)

    if result.get("status") == "saved":
        console.print(f"  [green]✓ Project saved:[/green] [cyan]{name}[/cyan]")
        console.print(f"  [dim]Updated:[/dim] {result.get('updated_at', '—')}")
    else:
        console.print(f"  [red]✗ Error:[/red] {result.get('message', result)}")


@project_cli.command(name="backup")
@click.option("--name", "-n", prompt="Project name", help="Project name")
def project_backup(name: str):
    """Backup a project."""
    console.print(f"  [dim]Backing up:[/dim] [cyan]{name}[/cyan]")

    result = _project_mgr.backup(name)

    if result.get("status") == "backed_up":
        console.print(f"  [green]✓ Backup created![/green]")
        console.print(f"  [dim]File:[/dim] [cyan]{result['backup_path']}[/cyan]")
        console.print(f"  [dim]Size:[/dim] {result['size_bytes']} bytes")
    else:
        console.print(f"  [red]✗ Error:[/red] {result.get('message', result)}")


@project_cli.command(name="list")
def project_list():
    """List all projects."""
    result = _project_mgr.list_projects()
    projects = result.get("projects", [])

    if projects:
        table = Table(
            title="Arduino Vibe IDE Projects",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Name", style="cyan")
        table.add_column("Board", style="yellow")
        table.add_column("Connection", width=12)
        table.add_column("Libraries", width=20)
        table.add_column("Pins", width=6)
        table.add_column("Updated", width=20)
        table.add_column("Sketch", width=6)

        for p in projects:
            sketch_status = "✅" if p.get("has_sketch") else "⚠️"
            libs = ", ".join(p.get("libraries", [])[:2])
            if len(p.get("libraries", [])) > 2:
                libs += "..."

            table.add_row(
                p["name"],
                p.get("board", "—"),
                p.get("connection_type", "—"),
                libs or "—",
                str(p.get("pins_count", 0)),
                p.get("updated_at", "—")[:19] if p.get("updated_at") else "—",
                sketch_status,
            )

        console.print(table)
        console.print(f"\n[dim]Total: {result['total']} projects[/dim]")
    else:
        console.print("[yellow]⚠ No projects found[/yellow]")
        console.print(f"[dim]Projects directory:[/dim] [_project_mgr.project_dir]")


@project_cli.command(name="load")
@click.option("--name", "-n", prompt="Project name", help="Project name")
def project_load(name: str):
    """Load a project."""
    result = _project_mgr.load(name)

    if result.get("status") == "loaded":
        meta = result.get("metadata", {})
        console.print(Panel(
            f"[bold cyan]{meta.get('name', name)}[/bold cyan]\n\n"
            f"[dim]Board:[/dim] {meta.get('board', '—')}\n"
            f"[dim]Connection:[/dim] {meta.get('connection_type', '—')}\n"
            f"[dim]Description:[/dim] {meta.get('description', '—')}\n"
            f"[dim]Libraries:[/dim] {', '.join(meta.get('libraries', [])) or '—'}\n"
            f"[dim]Created:[/dim] {meta.get('created_at', '—')[:19]}\n"
            f"[dim]Updated:[/dim] {meta.get('updated_at', '—')[:19]}",
            title="📦 Project",
            border_style="cyan",
            box=box.ROUNDED,
        ))

        if result.get("sketch"):
            console.print("\n[dim]Sketch content:[/dim]")
            sketch_display(result["sketch"])

        if result.get("backups"):
            console.print(f"\n[dim]Backups ({len(result['backups'])}):[/dim]")
            for b in result["backups"][-3:]:
                console.print(f"  [cyan]{b['name']}[/cyan] [dim]({b['size']} bytes)[/dim]")

        if result.get("notes"):
            console.print(f"\n[dim]Notes:[/dim]")
            console.print(result["notes"])
    else:
        console.print(f"  [red]✗ Error:[/red] {result.get('message', result)}")


@cli.command(name="backup")
@click.option("--name", "-n", prompt="Project name", help="Project name")
def quick_backup(name: str):
    """Quick backup of a project."""
    console.print(f"  [dim]Backing up:[/dim] [cyan]{name}[/cyan]")

    result = _project_mgr.backup(name)

    if result.get("status") == "backed_up":
        console.print(f"  [green]✓ Backup created![/green]")
        console.print(f"  [dim]File:[/dim] [cyan]{result['backup_path']}[/cyan]")
        console.print(f"  [dim]Size:[/dim] {result['size_bytes']} bytes")
    else:
        console.print(f"  [red]✗ Error:[/red] {result.get('message', result)}")


# ─── LED Control ──────────────────────────────────────────────────

@cli.command(name="led")
@click.option("--device", "-d", default="/dev/ttyACM0", help="Serial port")
@click.option("--baudrate", "-b", default=115200, help="Baud rate")
@click.option("--command", "-c", default="ALL", help="Command (LED, ALL, BRIGHT, EFFECT, COLOR)")
@click.option("--led", "-l", default=-1, help="LED index")
@click.option("--red", "-r", default=255, help="Red (0-255)")
@click.option("--green", "-g", default=255, help="Green (0-255)")
@click.option("--blue", "-e", default=255, help="Blue (0-255)")
@click.option("--brightness", default=-1, help="Brightness (0-255)")
@click.option("--effect", default="", help="Effect name")
@click.option("--speed", default=-1, help="Animation speed (1-255)")
@click.option("--color", default="", help="Preset color name")
def led_control(
    device: str, baudrate: int, command: str, led: int,
    red: int, green: int, blue: int, brightness: int,
    effect: str, speed: int, color: str
):
    """Control LEDs on connected Arduino."""
    cmd_string = build_led_command(
        command=command,
        led_index=led,
        red=red,
        green=green,
        blue=blue,
        brightness=brightness,
        effect=effect,
        speed=speed,
    )

    if color:
        rgb = LED_PRESET_COLORS.get(color.lower(), (255, 255, 255))
        red, green, blue = rgb
        cmd_string = f"COLOR {red} {green} {blue}"

    if cmd_string:
        result = send_serial(device, cmd_string, baudrate)
        if result.get("status") == "sent":
            console.print(f"  [green]✓ Sent:[/green] [cyan]{cmd_string}[/cyan]")
        else:
            console.print(f"  [red]✗ Error:[/red] {result.get('message', 'Unknown')}")
    else:
        console.print("  [yellow]⚠ Check parameters[/yellow]")


# ─── Main ─────────────────────────────────────────────────────────

# Register subcommands
cli.add_command(project_cli)


if __name__ == "__main__":
    cli()
