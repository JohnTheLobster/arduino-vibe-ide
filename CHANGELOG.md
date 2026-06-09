# CHANGELOG

## v0.2.2 — Quality & Hardening (2026-06-09)

### Fixed
- **Critical: `verify_board` / `check_modules` infinite recursion** — MCP tool wrappers in `src/server.py` shadowed their own imported implementations, calling themselves until the stack overflowed. Renamed wrappers to `*_tool` and preserved the public MCP tool names via `@mcp.tool(name=...)`.
- **Typo: `rfcord_channel` → `rfcomm_channel`** — corrected the misspelled field on `DeviceInfo` (`src/devices.py`) and `ProjectMetadata.bt_rfcord_channel` (`src/project.py`). Legacy `project.json` files are auto-migrated on load.
- **Missing `send_serial` import in `src/cli.py`** — `arduino-vibe led` would crash with `NameError`. Added the import.
- **Broken `__main__` block in `src/serial_terminal.py`** — `sys.argv` was used before `import sys`; lifted the import to module scope.
- **`devices._run_command` swallowed failures as text** — returning `"Error: ..."` strings was mis-parsed by callers as bluetoothctl output. Now returns `None` on failure.
- **No-op MAC comparison** in `_resolve_rfcomm_path` — `mac.upper().replace(":", ":")` collapsed to a redundant compare; simplified.
- **Dead variable** in `set_leds` (`src/server.py`) — removed.

### Security
- **Path-traversal protection for projects** — `ArduinoProject.create/save/backup/load/delete` now sanitize names through a strict `[a-z0-9_]` allowlist and verify the resolved path stays under `project_dir`. Empty/whitespace/punctuation-only names are rejected with a structured error instead of creating stray directories.
- **Path-traversal protection for profiles** — same allowlist + resolve-and-check applied to `ConfigProfiles` (`src/config_profiles.py`).

### Changed
- **`profile_update` MCP tool signature** — FastMCP cannot expose `**kwargs` to clients. Replaced with explicit optional parameters (`board_fqbn`, `board_name`, `connection_type`, `usb_port`, `bluetooth_mac`, `bluetooth_pin`, `baudrate`, `led_pin`, `num_leds`, `led_type`, `notes`). The underlying `ConfigProfiles.update_profile()` still accepts `**kwargs` for backwards compat.
- **`ConfigProfiles.update_profile` now ignores unknown fields** rather than silently writing them to disk.
- **Version bumped to 0.2.2** in `pyproject.toml`, `src/__init__.py`, and the CLI banner (was a stale `v1.0.0`).
- **`src/config_profiles.py`** — reformatted from single-line dataclass methods to readable multi-line bodies; added module/class docstrings.

### Added
- **`tests/test_project.py`** — 10 tests covering `_safe_project_name`, traversal guard, empty-name rejection, and the legacy `bt_rfcord_channel` migration.
- **`tests/test_devices.py`** — 3 tests covering the renamed `rfcomm_channel` field and `discover_devices_json` shape.
- **2 new `test_config_profiles.py` cases** — unknown-field filtering on `update_profile`, traversal-safe `create_profile`.
- Total test suite: **51 tests passing** (up from 35).

---

## v0.2.1 — Multi-Board Support & Serial Plotter (2026-06-04)

### Added
- **Multi-board support** — ESP32, ESP8266, RP2040 families added to `BOARD_CONFIGS`
  - ESP32: `esp32`, `esp32dev`, `esp32s3`
  - ESP8266: `esp8266`, `nodemcu`
  - RP2040: `rp2040`, `rpipico`, `rpipicow`
  - Dynamic board core installation via `arduino-cli core install` with additional URLs
- **Serial Plotter** — New `src/serial_plotter.py` module
  - Threaded, non-blocking serial reading with background worker
  - Flexible numeric parsing (comma/tab/space delimiters, labeled values)
  - Per-channel statistics (min, max, avg, latest)
  - MCP tools: `serial_plotter_open`, `serial_plotter_read`, `serial_plotter_summary`, `serial_plotter_close`
- **Configuration Profiles** — New `src/config_profiles.py` module
  - YAML-based hardware profiles stored in `~/.arduino-vibe/profiles/`
  - Full CRUD: create, update, delete, list, set active
  - Stores FQBN, connection type, baudrate, LED pins, custom pin mappings
  - 7 MCP tools: `profile_list`, `profile_get`, `profile_create`, `profile_update`, `profile_delete`, `profile_set_active`, `profile_get_active`
- **Error Recovery** — Connection resilience for serial communication
  - `check_connection()` — Verify serial link is alive
  - `reconnect()` — Auto-reconnect to last known port
  - `retry_write()` — Write with automatic retry and reconnect logic
  - MCP tools: `serial_check_connection`, `serial_reconnect`
- **SPIFFS/LittleFS Upload** — Filesystem upload for embedded web servers
  - `upload_spiffs_tool()` — Upload SPIFFS to ESP32/ESP8266
  - `upload_littlefs_tool()` — Upload LittleFS to ESP32
- **Test Suite** — Comprehensive pytest coverage (35 tests, all passing)
  - `test_compiler.py` — Board configurations, compilation, upload
  - `test_serial_terminal.py` — Serial terminal open/read/write/close
  - `test_config_profiles.py` — Profile CRUD and management
  - `test_serial_plotter.py` — Data parsing and plotter operations
- **Example Sketches** — 6 examples across supported platforms
  - `blink.ino` — Classic blink (all boards)
  - `sensor-read.ino` — Analog sensor with serial plotter output
  - `esp32-wifi-webserver.ino` — WiFi web server with LED toggle
  - `esp8266-iot-mqtt.ino` — MQTT client for IoT data
  - `pico-led-fade.ino` — RP2040 PWM LED fade

### Changed
- `src/compiler.py` — Dynamic board detection and FQBN resolution for all families
- `src/server.py` — Registered plotter, profile, and error recovery MCP tools
- `src/serial_terminal.py` — Updated for compatibility with new features
