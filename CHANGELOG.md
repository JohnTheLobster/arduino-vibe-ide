# Changelog

All notable changes to Arduino Vibe IDE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2] - 2026-06-04

### Added
- **IDE Plugin Integration** — MCP server now installable as IDE plugin via stdio transport
- **37 MCP Tools** — Expanded from 15 to 37 tools including:
  - AgentCore vibe coding (NL prompt → sketch → compile → flash)
  - Template library (weather station, plant monitor, security system, smart home hub, LED controller, IoT gateway)
  - Agent bridge for live hardware feedback loop
  - Sensor reading, LED control, servo control via AgentCore
  - Template search and retrieval
- **Agent Sketch Builder** — Natural language to AgentCore-enabled Arduino sketches
- **Hardware Database** — Keyword-based hardware inference (sensors, actuators, displays, communication)
- **Pre-built Templates** — 6 AgentCore templates with wiring diagrams and library requirements
- **IDE Configuration Files** — Ready-to-use MCP configs for Claude Code, Cursor, and Codex
- **Example Prompts** — Comprehensive usage examples for vibe coding workflows
- **Package Installation** — `pip install -e .` installs CLI + MCP server as global commands
- **MCP Server Entry Point** — `arduino-vibe-mcp` command for IDE integration

### Changed
- **MCP Server** — Expanded from 15 to 37 tools with full AgentCore support
- **Project Structure** — Added `ide-integration/`, `templates/`, and agent modules
- **Build System** — Updated to setuptools.build_meta with package discovery

### Fixed
- **Build Backend** — Fixed setuptools backend for modern pip compatibility
- **Package Discovery** — Added setuptools.packages.find for src and templates modules

### Documentation
- **IDE Setup Guide** — Full installation and configuration instructions
- **Example Prompts** — Ready-to-use prompts for Claude Code, Cursor, and Codex
- **Skill Update** — Updated arduino-mcp-ide skill with IDE plugin integration
- **README** — Updated with MCP tools table and hardware configuration

## [0.1] - 2026-06-01

### Added
- MCP server with 15+ Arduino hardware control tools
- CLI wizard with interactive setup (click + rich)
- USB serial + Bluetooth HC-05 device discovery
- Template-based Arduino C++ sketch generation
- Project management (create, save, backup, load)
- Interactive serial terminal
- Runtime LED control via serial commands (FastLED/SK6812)
- IR remote support (receive/send with code storage)
- Sensor support (DHT, BMP, BME, I2C detection)
- Library management (install, list, search)
- Compilation and upload via arduino-cli
- Board verification and module detection
