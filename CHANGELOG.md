# CHANGELOG

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
