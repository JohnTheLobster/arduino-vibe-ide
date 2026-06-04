# Example Sketches

Ready-to-flash example sketches for arduino-vibe-ide.

## Basic
- `blink.ino` — Classic blink (all boards)
- `sensor-read.ino` — Analog sensor with serial plotter output

## ESP32
- `esp32-wifi-webserver.ino` — WiFi web server with LED toggle

## ESP8266
- `esp8266-iot-mqtt.ino` — MQTT client for IoT sensor data

## RP2040
- `pico-led-fade.ino` — PWM LED fade on Raspberry Pi Pico

## Usage

```bash
PYTHONPATH=. python3 src/cli.py upload -f examples/blink.ino -p /dev/ttyACM0
```
