"""
Agent Sketch Builder — Natural Language to AgentCore Sketches

Takes a natural language description and generates a complete,
AgentCore-enabled sketch ready for compilation and flashing.

The sketch builder detects hardware needs, selects components,
and produces code that's immediately agent-controllable.
"""

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─── Hardware Knowledge Base ────────────────────────────────────────

HARDWARE_DB = {
    # Sensors
    "temperature": {
        "sensors": [
            {"name": "DS18B20", "type": "temperature", "protocol": "1-wire", "pin": 2, "library": "OneWire, DallasTemperature"},
            {"name": "DHT22", "type": "temperature,humidity", "protocol": "digital", "pin": 2, "library": "DHT sensor library"},
            {"name": "BME280", "type": "temperature,humidity,pressure", "protocol": "I2C", "address": "0x76", "library": "Adafruit_BME280"},
        ]
    },
    "humidity": {
        "sensors": [
            {"name": "DHT22", "type": "humidity", "protocol": "digital", "pin": 2, "library": "DHT sensor library"},
            {"name": "BME280", "type": "humidity", "protocol": "I2C", "address": "0x76", "library": "Adafruit_BME280"},
        ]
    },
    "pressure": {
        "sensors": [
            {"name": "BME280", "type": "pressure", "protocol": "I2C", "address": "0x76", "library": "Adafruit_BME280"},
            {"name": "BMP280", "type": "pressure,temperature", "protocol": "I2C", "address": "0x76", "library": "Adafruit_BMP280"},
        ]
    },
    "motion": {
        "sensors": [
            {"name": "PIR", "type": "motion", "protocol": "digital", "pin": 3, "library": ""},
            {"name": "MPU6050", "type": "accelerometer,gyroscope", "protocol": "I2C", "address": "0x68", "library": "Wire"},
        ]
    },
    "light": {
        "sensors": [
            {"name": "LDR", "type": "light", "protocol": "analog", "pin": "A0", "library": ""},
            {"name": "BH1750", "type": "light", "protocol": "I2C", "address": "0x23", "library": "Wire"},
        ]
    },
    "sound": {
        "sensors": [
            {"name": "Sound Sensor", "type": "sound", "protocol": "analog", "pin": "A0", "library": ""},
        ]
    },
    "distance": {
        "sensors": [
            {"name": "HC-SR04", "type": "distance", "protocol": "digital", "pin": 4, "library": ""},
        ]
    },
    "gas": {
        "sensors": [
            {"name": "MQ-2", "type": "gas,smoke", "protocol": "analog", "pin": "A0", "library": ""},
            {"name": "MQ-135", "type": "gas,air_quality", "protocol": "analog", "pin": "A0", "library": ""},
        ]
    },
    "soil_moisture": {
        "sensors": [
            {"name": "Soil Moisture Sensor", "type": "soil_moisture", "protocol": "analog", "pin": "A0", "library": ""},
        ]
    },
    # Actuators
    "servo": {
        "actuators": [
            {"name": "Servo", "type": "servo", "protocol": "PWM", "pin": 9, "library": "Servo"},
        ]
    },
    "motor": {
        "actuators": [
            {"name": "L298N", "type": "motor", "protocol": "digital", "pin": 5, "library": ""},
        ]
    },
    "relay": {
        "actuators": [
            {"name": "Relay", "type": "relay", "protocol": "digital", "pin": 7, "library": ""},
        ]
    },
    "buzzer": {
        "actuators": [
            {"name": "Buzzer", "type": "buzzer", "protocol": "PWM", "pin": 8, "library": ""},
        ]
    },
    # Displays
    "oled": {
        "displays": [
            {"name": "SSD1306", "type": "oled", "protocol": "I2C", "address": "0x3C", "library": "Adafruit_SSD1306, Adafruit_GFX"},
        ]
    },
    "lcd": {
        "displays": [
            {"name": "LCD1602", "type": "lcd", "protocol": "I2C", "address": "0x27", "library": "LiquidCrystal_I2C"},
        ]
    },
    # LEDs
    "led": {
        "actuators": [
            {"name": "LED", "type": "led", "protocol": "digital", "pin": 13, "library": ""},
        ]
    },
    "led_strip": {
        "actuators": [
            {"name": "WS2812B", "type": "led_strip", "protocol": "digital", "pin": 6, "library": "FastLED"},
            {"name": "SK6812", "type": "led_strip", "protocol": "digital", "pin": 6, "library": "FastLED"},
        ]
    },
    # Communication
    "bluetooth": {
        "communication": [
            {"name": "HC-05", "type": "bluetooth", "protocol": "UART", "pin": "SoftwareSerial", "library": "SoftwareSerial"},
        ]
    },
    "wifi": {
        "communication": [
            {"name": "ESP8266", "type": "wifi", "protocol": "UART", "pin": "SoftwareSerial", "library": "SoftwareSerial"},
            {"name": "ESP32", "type": "wifi", "protocol": "native", "pin": "", "library": "WiFi"},
        ]
    },
}


# ─── Hardware Inference ────────────────────────────────────────────

KEYWORD_MAP = {
    # Sensors
    "temperature": ["temperature", "thermometer", "temp", "hot", "cold", "weather"],
    "humidity": ["humidity", "moist", "humid", "dry", "weather"],
    "pressure": ["pressure", "barometer", "altitude", "weather"],
    "motion": ["motion", "movement", "pir", "accelerometer", "gyroscope", "imu", "shake"],
    "light": ["light", "lux", "brightness", "dark", "ambient", "photo"],
    "sound": ["sound", "noise", "decibel", "audio", "microphone"],
    "distance": ["distance", "ultrasonic", "proximity", "range"],
    "gas": ["gas", "smoke", "fire", "air quality", "co2"],
    "soil_moisture": ["soil", "plant", "water", "irrigation", "garden"],
    # Actuators
    "servo": ["servo", "rotate", "angle"],
    "motor": ["motor", "drive", "wheel"],
    "relay": ["relay", "switch", "on/off", "ac"],
    "buzzer": ["buzzer", "beep", "alarm", "sound alert"],
    # Displays
    "oled": ["oled", "display", "screen", "show"],
    "lcd": ["lcd", "1602", "character display"],
    # LEDs
    "led": ["led", "indicator", "blink", "light up"],
    "led_strip": ["led strip", "neopixel", "ws2812", "rgb strip", "colorful"],
    # Communication
    "bluetooth": ["bluetooth", "bt", "hc-05", "hc-06"],
    "wifi": ["wifi", "esp", "internet", "web", "iot"],
}


@dataclass
class HardwareSpec:
    """Detected hardware requirements from natural language prompt."""
    name: str
    description: str
    sensors: list = field(default_factory=list)
    actuators: list = field(default_factory=list)
    displays: list = field(default_factory=list)
    communication: list = field(default_factory=list)
    libraries: list = field(default_factory=list)
    board: str = "avr:uno"


def infer_hardware(prompt: str) -> HardwareSpec:
    """
    Infer hardware needs from a natural language prompt.

    Example: 'weather station with oled display' ->
      HardwareSpec(
        name='Weather Station',
        sensors=[BME280 (temp/humidity/pressure)],
        displays=[SSD1306 OLED],
        libraries=['Adafruit_BME280', 'Adafruit_SSD1306', 'Adafruit_GFX', 'Wire']
      )
    """
    prompt_lower = prompt.lower()

    spec = HardwareSpec(
        name=_extract_name(prompt),
        description=prompt,
    )

    # Detect hardware categories
    for category, keywords in KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                _add_hardware(spec, category)
                break

    # Default sensor if nothing detected
    if not spec.sensors and not spec.actuators and not spec.displays:
        spec.sensors.append(
            HARDWARE_DB["temperature"]["sensors"][0]
        )

    return spec


def _extract_name(prompt: str) -> str:
    """Extract project name from prompt."""
    # Take first meaningful phrase
    words = prompt.split()
    name = " ".join(words[:8]).strip().title()
    return name if name else "Arduino Project"


def _add_hardware(spec: HardwareSpec, category: str):
    """Add hardware to spec based on category."""
    if category not in HARDWARE_DB:
        return

    db_entry = HARDWARE_DB[category]

    if "sensors" in db_entry:
        sensor = db_entry["sensors"][0]
        spec.sensors.append(sensor)
        if sensor.get("library"):
            for lib in sensor["library"].split(", "):
                if lib not in spec.libraries:
                    spec.libraries.append(lib)

    if "actuators" in db_entry:
        actuator = db_entry["actuators"][0]
        spec.actuators.append(actuator)
        if actuator.get("library"):
            for lib in actuator["library"].split(", "):
                if lib not in spec.libraries:
                    spec.libraries.append(lib)

    if "displays" in db_entry:
        display = db_entry["displays"][0]
        spec.displays.append(display)
        if display.get("library"):
            for lib in display["library"].split(", "):
                if lib not in spec.libraries:
                    spec.libraries.append(lib)

    if "communication" in db_entry:
        comm = db_entry["communication"][0]
        spec.communication.append(comm)
        if comm.get("library"):
            for lib in comm["library"].split(", "):
                if lib not in spec.libraries:
                    spec.libraries.append(lib)


# ─── Sketch Generation ─────────────────────────────────────────────

def generate_agentcore_sketch(spec: HardwareSpec) -> str:
    """
    Generate a complete AgentCore-enabled sketch from a hardware spec.

    The generated sketch:
    - Includes AgentCore runtime
    - Registers all sensors and actuators
    - Implements read/write handlers
    - Is immediately agent-controllable
    """
    # Build includes
    includes = _build_includes(spec)

    # Build sensor definitions
    sensor_defs = _build_sensor_defs(spec)

    # Build actuator definitions
    actuator_defs = _build_actuator_defs(spec)

    # Build display definitions
    display_defs = _build_display_defs(spec)

    # Build communication
    comm_defs = _build_comm_defs(spec)

    # Build setup code
    setup_code = _build_setup(spec)

    # Build read/write handlers
    read_handlers = _build_read_handlers(spec)
    write_handlers = _build_write_handlers(spec)

    sketch = f"""/**
 * {spec.name}
 * Generated by Arduino Vibe IDE
 * Description: {spec.description}
 */

#include <AgentCore.h>
{includes}

// ─── Sensor Configuration ──────────────────────────────────────────
{sensor_defs}

// ─── Actuator Configuration ────────────────────────────────────────
{actuator_defs}

// ─── Display Configuration ─────────────────────────────────────────
{display_defs}

// ─── Communication ─────────────────────────────────────────────────
{comm_defs}

// ─── Setup ──────────────────────────────────────────────────────────
void setup() {{
{setup_code}
}}

// ─── Loop ──────────────────────────────────────────────────────────
void loop() {{
    AgentCore.process();
}}

// ─── Sensor Read Handlers ──────────────────────────────────────────
{read_handlers}

// ─── Actuator Write Handlers ───────────────────────────────────────
{write_handlers}
"""
    return sketch


def _build_includes(spec: HardwareSpec) -> str:
    """Build #include statements."""
    includes = ""
    for lib in spec.libraries:
        lib_clean = lib.strip()
        if lib_clean == "Wire":
            includes += f"#include <Wire.h>\n"
        elif lib_clean == "SoftwareSerial":
            includes += f"#include <SoftwareSerial.h>\n"
        elif lib_clean == "Servo":
            includes += f"#include <Servo.h>\n"
        else:
            includes += f"#include <{lib_clean}.h>\n"
    return includes if includes else "// (no additional includes needed)"


def _build_sensor_defs(spec: HardwareSpec) -> str:
    """Build sensor object declarations."""
    defs = ""
    for sensor in spec.sensors:
        name = sensor["name"]
        if name == "BME280" or name == "BMP280":
            defs += f"Adafruit_{name} {name.lower()};\n"
        elif name == "DS18B20":
            defs += f"OneWire oneWire({sensor['pin']});\n"
            defs += f"DallasTemperature sensors_ow(&oneWire);\n"
        elif name == "DHT22":
            defs += f"#define DHTPIN {sensor['pin']}\n"
            defs += f"#define DHTTYPE DHT22\n"
            defs += f"DHT dht(DHTPIN, DHTTYPE);\n"
        elif name == "HC-SR04":
            defs += f"#define TRIG_PIN {sensor['pin']}\n"
            defs += f"#define ECHO_PIN {sensor['pin'] + 1}\n"
        elif name == "MPU6050":
            defs += f"// MPU6050 at 0x68\n"
        else:
            defs += f"#define {name.upper()}_PIN {sensor['pin']}\n"
    return defs if defs else "// (no sensors configured)"


def _build_actuator_defs(spec: HardwareSpec) -> str:
    """Build actuator object declarations."""
    defs = ""
    for actuator in spec.actuators:
        name = actuator["name"]
        pin = actuator.get("pin", 9)
        if name == "Servo":
            defs += f"Servo servo1;\n"
            defs += f"#define SERVO_PIN {pin}\n"
        elif name == "LED":
            defs += f"#define LED_PIN {pin}\n"
        elif name in ("WS2812B", "SK6812"):
            defs += f"#define LED_STRIP_PIN {pin}\n"
            defs += f"#define NUM_STRIP_LEDS 16\n"
        elif name == "Relay":
            defs += f"#define RELAY_PIN {pin}\n"
        else:
            defs += f"#define {name.upper()}_PIN {pin}\n"
    return defs if defs else "// (no actuators configured)"


def _build_display_defs(spec: HardwareSpec) -> str:
    """Build display object declarations."""
    defs = ""
    for display in spec.displays:
        name = display["name"]
        if name == "SSD1306":
            defs += f"#define OLED_ADDR 0x3C\n"
            defs += f"Adafruit_SSD1306 display(128, 64, &Wire, -1);\n"
        elif name == "LCD1602":
            defs += f"#define LCD_ADDR 0x27\n"
            defs += f"LiquidCrystal_I2C lcd(0x27, 16, 2);\n"
    return defs if defs else "// (no display configured)"


def _build_comm_defs(spec: HardwareSpec) -> str:
    """Build communication module declarations."""
    defs = ""
    for comm in spec.communication:
        name = comm["name"]
        if name == "HC-05":
            defs += f"#define BT_RX 10\n"
            defs += f"#define BT_TX 11\n"
            defs += f"SoftwareSerial bluetooth(BT_RX, BT_TX);\n"
    return defs if defs else "// (no communication module)"


def _build_setup(spec: HardwareSpec) -> str:
    """Build setup() code."""
    code = """    Serial.begin(115200);
    while (!Serial) { }

    // Register sensors with AgentCore
"""
    for sensor in spec.sensors:
        name = sensor["name"]
        if name == "BME280":
            code += f"    Wire.begin();\n"
            code += f"    bool bme_ok = bme280.begin(0x76);\n"
            code += f"    if (!bme_ok) {{ Serial.println(F(\"BME280 not found\")); }}\n"
            code += f"    AgentCore.registerSensor(\"temperature\", read_temperature);\n"
            code += f"    AgentCore.registerSensor(\"humidity\", read_humidity);\n"
            code += f"    AgentCore.registerSensor(\"pressure\", read_pressure);\n"
        elif name == "DHT22":
            code += f"    dht.begin();\n"
            code += f"    AgentCore.registerSensor(\"temperature\", read_temperature);\n"
            code += f"    AgentCore.registerSensor(\"humidity\", read_humidity);\n"
        elif name == "DS18B20":
            code += f"    sensors_ow.begin();\n"
            code += f"    AgentCore.registerSensor(\"temperature\", read_temperature);\n"
        elif name == "HC-SR04":
            code += f"    pinMode(TRIG_PIN, OUTPUT);\n"
            code += f"    pinMode(ECHO_PIN, INPUT);\n"
            code += f"    AgentCore.registerSensor(\"distance\", read_distance);\n"
        else:
            code += f"    pinMode({name.upper()}_PIN, INPUT);\n"
            code += f'    AgentCore.registerSensor("{name.lower()}", read_{name.lower()});\n'

    code += "\n    // Register actuators with AgentCore\n"
    for actuator in spec.actuators:
        name = actuator["name"]
        pin = actuator.get("pin", 9)
        if name == "Servo":
            code += f"    servo1.attach(SERVO_PIN);\n"
            code += f'    AgentCore.registerActuator("servo1", write_servo);\n'
        elif name == "LED":
            code += f"    pinMode(LED_PIN, OUTPUT);\n"
            code += f'    AgentCore.registerActuator("led1", write_led);\n'
        elif name in ("WS2812B", "SK6812"):
            code += f'    AgentCore.registerActuator("led_strip", write_led_strip);\n'
        elif name == "Relay":
            code += f"    pinMode(RELAY_PIN, OUTPUT);\n"
            code += f'    AgentCore.registerActuator("relay1", write_relay);\n'
        else:
            code += f"    pinMode({name.upper()}_PIN, OUTPUT);\n"
            code += f'    AgentCore.registerActuator("{name.lower()}", write_{name.lower()});\n'

    code += "\n    // Initialize displays\n"
    for display in spec.displays:
        name = display["name"]
        if name == "SSD1306":
            code += f"    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {{\n"
            code += f"        Serial.println(F(\"OLED not found\"));\n"
            code += f"    }}\n"
            code += f"    display.clearDisplay();\n"
            code += f"    display.setTextSize(1);\n"
            code += f"    display.setTextColor(SSD1306_WHITE);\n"
            code += f"    display.println(F(\"{spec.name}\"));\n"
            code += f"    display.display();\n"

    code += "\n    // Initialize communication\n"
    for comm in spec.communication:
        name = comm["name"]
        if name == "HC-05":
            code += f"    bluetooth.begin(9600);\n"

    code += '\n    AgentCore.begin();\n'
    code += f'    Serial.println(F("AGENT_CORE_READY - {spec.name}"));\n'

    return code


def _build_read_handlers(spec: HardwareSpec) -> str:
    """Build sensor read handler functions."""
    handlers = ""
    for sensor in spec.sensors:
        name = sensor["name"]
        if name == "BME280":
            handlers += f"""
float read_temperature() {{
    return bme280.readTemperature();
}}

float read_humidity() {{
    return bme280.readHumidity();
}}

float read_pressure() {{
    return bme280.readPressure() / 100.0F;
}}
"""
        elif name == "DHT22":
            handlers += f"""
float read_temperature() {{
    return dht.readTemperature();
}}

float read_humidity() {{
    return dht.readHumidity();
}}
"""
        elif name == "DS18B20":
            handlers += f"""
float read_temperature() {{
    sensors_ow.requestTemperatures();
    return sensors_ow.getTempCByIndex(0);
}}
"""
        elif name == "HC-SR04":
            handlers += f"""
float read_distance() {{
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    long duration = pulseIn(ECHO_PIN, HIGH, 30000);
    return duration * 0.034 / 2.0;
}}
"""
        elif name == "PIR":
            handlers += f"""
float read_motion() {{
    return digitalRead(PIR_PIN);
}}
"""
        else:
            handlers += f"""
float read_{name.lower()}() {{
    return analogRead({name.upper()}_PIN);
}}
"""
    return handlers


def _build_write_handlers(spec: HardwareSpec) -> str:
    """Build actuator write handler functions."""
    handlers = ""
    for actuator in spec.actuators:
        name = actuator["name"]
        if name == "Servo":
            handlers += f"""
void write_servo(float value) {{
    int angle = constrain((int)value, 0, 180);
    servo1.write(angle);
}}
"""
        elif name == "LED":
            handlers += f"""
void write_led(float value) {{
    int brightness = constrain((int)value, 0, 255);
    if (brightness > 0) {{
        analogWrite(LED_PIN, brightness);
    }} else {{
        digitalWrite(LED_PIN, LOW);
    }}
}}
"""
        elif name in ("WS2812B", "SK6812"):
            handlers += f"""
void write_led_strip(float value) {{
    // Parse RGB from value (packed as R*65536 + G*256 + B)
    int r = (int)value / 65536;
    int g = ((int)value / 256) % 256;
    int b = (int)value % 256;
    // TODO: integrate FastLED for LED strip control
    for (int i = 0; i < NUM_STRIP_LEDS; i++) {{
        leds[i].setRGB(r, g, b);
    }}
    LED.show();
}}
"""
        elif name == "Relay":
            handlers += f"""
void write_relay(float value) {{
    digitalWrite(RELAY_PIN, value > 0.5 ? HIGH : LOW);
}}
"""
        else:
            handlers += f"""
void write_{name.lower()}(float value) {{
    if (value > 0.5) {{
        digitalWrite({name.upper()}_PIN, HIGH);
    }} else {{
        digitalWrite({name.upper()}_PIN, LOW);
    }}
}}
"""
    return handlers


# ─── Sketch Builder MCP Tools ──────────────────────────────────────

def build_sketch_from_prompt(prompt: str, board: str = "avr:uno") -> dict:
    """
    Build a complete AgentCore sketch from a natural language prompt.

    Returns:
        {
            "status": "success" | "error",
            "sketch": "...",
            "hardware": {
                "sensors": [...],
                "actuators": [...],
                "displays": [...],
                "libraries": [...]
            },
            "compile_ready": True
        }
    """
    try:
        spec = infer_hardware(prompt)
        spec.board = board
        sketch = generate_agentcore_sketch(spec)

        return {
            "status": "success",
            "name": spec.name,
            "sketch": sketch,
            "hardware": {
                "sensors": spec.sensors,
                "actuators": spec.actuators,
                "displays": spec.displays,
                "communication": spec.communication,
                "libraries": spec.libraries,
            },
            "board": board,
            "compile_ready": True,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def compile_sketch(sketch: str, board: str = "avr:uno", output_dir: str = None) -> dict:
    """
    Compile a sketch using arduino-cli.

    Returns:
        {
            "status": "success" | "error",
            "output": "...",
            "hex_file": "path/to/output.hex",
            "size": 12345
        }
    """
    try:
        # Create temp directory for compilation
        if output_dir:
            temp_dir = Path(output_dir)
        else:
            temp_dir = Path(tempfile.mkdtemp(prefix="sketch_"))

        # Write sketch
        sketch_path = temp_dir / "sketch.ino"
        sketch_path.write_text(sketch)

        # Get arduino-cli path
        cli_path = os.environ.get("ARDUINO_CLI", "arduino-cli")

        # Compile
        result = subprocess.run(
            [cli_path, "compile", "--fqbn", board, str(temp_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            # Find output file
            build_path = temp_dir / "build"
            hex_files = list(build_path.glob("*.hex")) if build_path.exists() else []

            return {
                "status": "success",
                "output": result.stdout[-500:],
                "build_path": str(build_path),
                "hex_file": hex_files[0] if hex_files else None,
            }
        else:
            return {
                "status": "error",
                "error": result.stderr[-1000:],
                "build_path": str(build_path),
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "Compilation timed out (120s)",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def flash_sketch(hex_file: str, port: str) -> dict:
    """
    Flash a compiled sketch to the board.

    Returns:
        {
            "status": "success" | "error",
            "output": "...",
            "port": "...",
        }
    """
    try:
        cli_path = os.environ.get("ARDUINO_CLI", "arduino-cli")

        # Detect board from port
        detect = subprocess.run(
            [cli_path, "board", "detect"],
            capture_output=True, text=True
        )

        # Upload
        result = subprocess.run(
            [cli_path, "upload", "--port", port, str(hex_file)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            return {
                "status": "success",
                "output": result.stdout[-500:],
                "port": port,
            }
        else:
            return {
                "status": "error",
                "error": result.stderr[-1000:],
                "port": port,
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ─── MCP Tool Registration ─────────────────────────────────────────

def register_sketch_builder_tools(mcp):
    """Register sketch builder MCP tools."""

    @mcp.tool()
    def agent_build_sketch(
        prompt: str,
        board: str = "avr:uno",
    ) -> str:
        """
        Build an AgentCore sketch from a natural language prompt.

        Example: 'weather station with oled display'
        Example: 'smart plant monitor with soil moisture and relay'
        Example: 'motion activated led alarm with buzzer'

        Args:
            prompt: Natural language description of what you want to build
            board: Arduino board FQBN (default: avr:uno)

        Returns:
            JSON with sketch code, detected hardware, and compile status
        """
        result = build_sketch_from_prompt(prompt, board)
        if result["status"] == "success":
            # Return summary + sketch truncated
            summary = {
                "status": "success",
                "name": result["name"],
                "hardware": {
                    "sensors": [s["name"] for s in result["hardware"]["sensors"]],
                    "actuators": [a["name"] for a in result["hardware"]["actuators"]],
                    "displays": [d["name"] for d in result["hardware"]["displays"]],
                    "libraries": result["hardware"]["libraries"],
                },
                "board": result["board"],
                "sketch_size": len(result["sketch"]),
                "compile_ready": result["compile_ready"],
            }
            return json.dumps(summary, indent=2)
        else:
            return json.dumps(result, indent=2)

    @mcp.tool()
    def agent_compile_sketch(
        prompt: str,
        board: str = "avr:uno",
        output_dir: str = None,
    ) -> str:
        """
        Build and compile an AgentCore sketch from a natural language prompt.

        Args:
            prompt: Natural language description
            board: Arduino board FQBN (default: avr:uno)
            output_dir: Optional output directory for build artifacts

        Returns:
            JSON with compilation result
        """
        build_result = build_sketch_from_prompt(prompt, board)
        if build_result["status"] != "success":
            return json.dumps(build_result, indent=2)

        compile_result = compile_sketch(
            build_result["sketch"],
            board,
            output_dir,
        )
        return json.dumps(compile_result, indent=2)

    @mcp.tool()
    def agent_flash_sketch(
        hex_file: str,
        port: str,
    ) -> str:
        """
        Flash a compiled sketch hex file to an Arduino board.

        Args:
            hex_file: Path to the compiled .hex file
            port: Serial port (e.g., /dev/ttyUSB0)

        Returns:
            JSON with flash result
        """
        result = flash_sketch(hex_file, port)
        return json.dumps(result, indent=2)

    @mcp.tool()
    def agent_build_and_flash(
        prompt: str,
        board: str = "avr:uno",
        port: str = None,
    ) -> str:
        """
        Full pipeline: build sketch from prompt, compile, and flash to board.

        Args:
            prompt: Natural language description
            board: Arduino board FQBN (default: avr:uno)
            port: Serial port (auto-detected if None)

        Returns:
            JSON with full pipeline result
        """
        # Build
        build_result = build_sketch_from_prompt(prompt, board)
        if build_result["status"] != "success":
            return json.dumps({
                "stage": "build",
                **build_result,
            }, indent=2)

        # Compile
        compile_result = compile_sketch(build_result["sketch"], board)
        if compile_result["status"] != "success":
            return json.dumps({
                "stage": "compile",
                **compile_result,
            }, indent=2)

        # Detect port if not provided
        if not port:
            detect = subprocess.run(
                ["arduino-cli", "board", "list"],
                capture_output=True, text=True
            )
            lines = detect.stdout.strip().split("\n")
            for line in lines[1:]:
                if "tty" in line:
                    port = line.split()[-1]
                    break

        if not port:
            return json.dumps({
                "stage": "flash",
                "status": "error",
                "error": "No port detected. Connect your board or specify --port",
            }, indent=2)

        # Flash
        flash_result = flash_sketch(compile_result.get("hex_file") or "", port)
        return json.dumps({
            "stage": "flash",
            **flash_result,
        }, indent=2)


if __name__ == "__main__":
    # Test sketch builder
    test_prompts = [
        "weather station with oled display",
        "smart plant monitor with soil moisture and relay",
        "motion activated led alarm with buzzer",
        "temperature controlled fan with servo",
    ]

    for prompt in test_prompts:
        print(f"\n{'='*60}")
        print(f"PROMPT: {prompt}")
        result = build_sketch_from_prompt(prompt)
        print(f"Name: {result.get('name', 'N/A')}")
        print(f"Sensors: {[s['name'] for s in result['hardware']['sensors']]}")
        print(f"Actuators: {[a['name'] for a in result['hardware']['actuators']]}")
        print(f"Libraries: {result['hardware']['libraries']}")
        print(f"Sketch size: {len(result['sketch'])} chars")
        print(result['sketch'][:500])
