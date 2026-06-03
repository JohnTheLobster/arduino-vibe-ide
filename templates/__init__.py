"""
AgentCore Template Library

Pre-built, AgentCore-enabled sketch templates for common hardware setups.
Each template is immediately agent-controllable and ready for flashing.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Template:
    """A pre-built AgentCore sketch template."""
    name: str
    category: str
    description: str
    sketch: str
    sensors: list = field(default_factory=list)
    actuators: list = field(default_factory=list)
    displays: list = field(default_factory=list)
    communication: list = field(default_factory=list)
    libraries: list = field(default_factory=list)
    wiring: Optional[str] = None  # How to wire the components


TEMPLATES = {}


def register_template(template: Template):
    """Register a template in the global registry."""
    TEMPLATES[template.name.lower()] = template


def get_template(name: str) -> Optional[Template]:
    """Get a template by name."""
    return TEMPLATES.get(name.lower())


def list_templates(category: str = None) -> list:
    """List templates, optionally filtered by category."""
    if category:
        return [t for t in TEMPLATES.values() if t.category.lower() == category.lower()]
    return list(TEMPLATES.values())


def search_templates(query: str) -> list:
    """Search templates by query string."""
    query_lower = query.lower()
    return [
        t for t in TEMPLATES.values()
        if query_lower in t.name.lower()
        or query_lower in t.description.lower()
        or query_lower in t.category.lower()
    ]


# ─── Weather Station ──────────────────────────────────────────────

WEATHER_STATION = Template(
    name="Weather Station",
    category="environment",
    description="Complete weather monitoring with temperature, humidity, pressure, and OLED display. Agent-controllable with real-time telemetry.",
    sketch="""/**
 * Weather Station Template
 * AgentCore-enabled weather monitoring system
 * 
 * Wiring:
 * - BME280: VCC->5V, GND->GND, SDA->A4, SCL->A5
 * - OLED: VCC->5V, GND->GND, SDA->A4, SCL->A5, RES->GND
 */

#include <AgentCore.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <Adafruit_SSD1306.h>

// Sensor
Adafruit_BME280 bme;

// Display
#define OLED_ADDR 0x3C
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
    Serial.begin(115200);
    while (!Serial) { }

    Wire.begin();

    // Initialize BME280
    if (!bme.begin(0x76)) {
        Serial.println(F("BME280 not found"));
    }

    // Initialize OLED
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
        Serial.println(F("OLED not found"));
    }
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println(F("Weather Station"));
    display.display();

    // Register sensors
    AgentCore.registerSensor("temperature", []() -> float {
        return bme.readTemperature();
    });
    AgentCore.registerSensor("humidity", []() -> float {
        return bme.readHumidity();
    });
    AgentCore.registerSensor("pressure", []() -> float {
        return bme.readPressure() / 100.0F;
    });

    // Display update callback
    AgentCore.onSensorRead([](const char* name, float value) {
        display.clearDisplay();
        display.setCursor(0, 0);
        display.println(F("Weather Data:"));
        display.print(F("  Temp: "));
        display.print(bme.readTemperature());
        display.print(F(" C"));
        display.print(F("  Hum: "));
        display.print(bme.readHumidity());
        display.print(F(" %"));
        display.print(F("  Press: "));
        display.print(bme.readPressure() / 100.0F);
        display.print(F(" hPa"));
        display.display();
    });

    AgentCore.begin();
    Serial.println(F("AGENT_CORE_READY - Weather Station"));
}

void loop() {
    AgentCore.process();
}
""",
    sensors=["BME280"],
    displays=["SSD1306"],
    libraries=["Wire", "Adafruit_BME280", "Adafruit_SSD1306", "Adafruit_GFX"],
    wiring="BME280: VCC->5V, GND->GND, SDA->A4, SCL->A5\nOLED: VCC->5V, GND->GND, SDA->A4, SCL->A5, RES->GND"
)
register_template(WEATHER_STATION)


# ─── Smart Plant Monitor ──────────────────────────────────────────

SMART_PLANT = Template(
    name="Smart Plant Monitor",
    category="agriculture",
    description="Soil moisture and temperature monitoring with automatic relay control for water pump. Agent can monitor plant health and trigger irrigation.",
    sketch="""/**
 * Smart Plant Monitor Template
 * AgentCore-enabled plant care system
 * 
 * Wiring:
 * - DHT22: VCC->5V, GND->GND, Data->D2
 * - Soil Moisture: VCC->5V, GND->GND, AOUT->A0
 * - Relay (Water Pump): VCC->5V, GND->GND, IN->D7, Signal->LED
 */

#include <AgentCore.h>
#include <DHT.h>

// Sensors
#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define SOIL_MOISTURE_PIN A0

// Actuators
#define RELAY_PIN 7  // Water pump
#define LED_PIN 13   // Status LED

void setup() {
    Serial.begin(115200);
    while (!Serial) { }

    dht.begin();
    pinMode(SOIL_MOISTURE_PIN, INPUT);
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);

    // Register sensors
    AgentCore.registerSensor("temperature", []() -> float {
        return dht.readTemperature();
    });
    AgentCore.registerSensor("humidity", []() -> float {
        return dht.readHumidity();
    });
    AgentCore.registerSensor("soil_moisture", []() -> float {
        return analogRead(SOIL_MOISTURE_PIN);
    });

    // Register actuators
    AgentCore.registerActuator("water_pump", [](float value) {
        digitalWrite(RELAY_PIN, value > 0.5 ? HIGH : LOW);
        digitalWrite(LED_PIN, value > 0.5 ? HIGH : LOW);
    });
    AgentCore.registerActuator("status_led", [](float value) {
        digitalWrite(LED_PIN, value > 0.5 ? HIGH : LOW);
    });

    AgentCore.begin();
    Serial.println(F("AGENT_CORE_READY - Smart Plant Monitor"));
}

void loop() {
    AgentCore.process();
}
""",
    sensors=["DHT22", "Soil Moisture Sensor"],
    actuators=["Relay", "LED"],
    libraries=["DHT sensor library"],
    wiring="DHT22: VCC->5V, GND->GND, Data->D2\nSoil Moisture: VCC->5V, GND->GND, AOUT->A0\nRelay: VCC->5V, GND->GND, IN->D7"
)
register_template(SMART_PLANT)


# ─── Security System ──────────────────────────────────────────────

SECURITY_SYSTEM = Template(
    name="Security System",
    category="security",
    description="Motion detection with PIR sensor, buzzer alarm, and LED indicator. Agent can monitor security events and control alarm thresholds.",
    sketch="""/**
 * Security System Template
 * AgentCore-enabled security monitoring
 * 
 * Wiring:
 * - PIR Sensor: VCC->5V, GND->GND, OUT->D3
 * - Buzzer: VCC->5V, GND->GND, Signal->D8
 * - LED: D13 (built-in)
 * - Push Button (optional): D4->GND (with 10k pullup)
 */

#include <AgentCore.h>

// Sensors
#define PIR_PIN 3
#define BUTTON_PIN 4

// Actuators
#define BUZZER_PIN 8
#define LED_PIN 13

// State
bool motion_detected = false;
bool alarm_active = false;
unsigned long last_motion = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial) { }

    pinMode(PIR_PIN, INPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);

    // Register sensors
    AgentCore.registerSensor("motion", []() -> float {
        return digitalRead(PIR_PIN);
    });
    AgentCore.registerSensor("button", []() -> float {
        return !digitalRead(BUTTON_PIN);  // Active low
    });

    // Register actuators
    AgentCore.registerActuator("buzzer", [](float value) {
        digitalWrite(BUZZER_PIN, value > 0.5 ? HIGH : LOW);
    });
    AgentCore.registerActuator("alarm_led", [](float value) {
        digitalWrite(LED_PIN, value > 0.5 ? HIGH : LOW);
    });

    // Motion callback
    AgentCore.onSensorRead([](const char* name, float value) {
        if (strcmp(name, "motion") == 0 && value > 0.5) {
            if (!alarm_active) {
                alarm_active = true;
                last_motion = millis();
                digitalWrite(BUZZER_PIN, HIGH);
                digitalWrite(LED_PIN, HIGH);
                Serial.println(F("MOTION_DETECTED"));
            } else {
                last_motion = millis();  // Reset timeout
            }
        }
    });

    AgentCore.begin();
    Serial.println(F("AGENT_CORE_READY - Security System"));
}

void loop() {
    AgentCore.process();

    // Auto-dismiss alarm after 30s of no motion
    if (alarm_active && millis() - last_motion > 30000) {
        alarm_active = false;
        digitalWrite(BUZZER_PIN, LOW);
        digitalWrite(LED_PIN, LOW);
        Serial.println(F("ALARM_DISMISSED"));
    }
}
""",
    sensors=["PIR"],
    actuators=["Buzzer", "LED"],
    libraries=[],
    wiring="PIR: VCC->5V, GND->GND, OUT->D3\nBuzzer: VCC->5V, GND->GND, Signal->D8\nLED: D13 (built-in)"
)
register_template(SECURITY_SYSTEM)


# ─── Smart Home Hub ───────────────────────────────────────────────

SMART_HOME = Template(
    name="Smart Home Hub",
    category="automation",
    description="Multi-sensor home automation hub with temperature, motion, light monitoring and relay control for lights, fans, and appliances.",
    sketch="""/**
 * Smart Home Hub Template
 * AgentCore-enabled home automation center
 * 
 * Wiring:
 * - DHT22: VCC->5V, GND->GND, Data->D2
 * - PIR: VCC->5V, GND->GND, OUT->D3
 * - LDR (Light): A0->5V, A1->GND, Wiper->A2
 * - Relay 1 (Light): IN->D7
 * - Relay 2 (Fan): IN->D8
 * - Relay 3 (AC): IN->D9
 * - OLED: SDA->A4, SCL->A5
 */

#include <AgentCore.h>
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_SSD1306.h>

// Sensors
#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define PIR_PIN 3
#define LIGHT_PIN A2

// Actuators
#define RELAY_LIGHT 7
#define RELAY_FAN 8
#define RELAY_AC 9

// Display
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
    Serial.begin(115200);
    while (!Serial) { }

    Wire.begin();
    dht.begin();
    pinMode(PIR_PIN, INPUT);
    pinMode(LIGHT_PIN, INPUT);
    pinMode(RELAY_LIGHT, OUTPUT);
    pinMode(RELAY_FAN, OUTPUT);
    pinMode(RELAY_AC, OUTPUT);

    // Initialize display
    if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.println(F("Smart Home Hub"));
        display.display();
    }

    // Register sensors
    AgentCore.registerSensor("temperature", []() -> float {
        return dht.readTemperature();
    });
    AgentCore.registerSensor("humidity", []() -> float {
        return dht.readHumidity();
    });
    AgentCore.registerSensor("motion", []() -> float {
        return digitalRead(PIR_PIN);
    });
    AgentCore.registerSensor("light", []() -> float {
        return analogRead(LIGHT_PIN);
    });

    // Register actuators
    AgentCore.registerActuator("light_relay", [](float value) {
        digitalWrite(RELAY_LIGHT, value > 0.5 ? HIGH : LOW);
    });
    AgentCore.registerActuator("fan_relay", [](float value) {
        digitalWrite(RELAY_FAN, value > 0.5 ? HIGH : LOW);
    });
    AgentCore.registerActuator("ac_relay", [](float value) {
        digitalWrite(RELAY_AC, value > 0.5 ? HIGH : LOW);
    });

    AgentCore.begin();
    Serial.println(F("AGENT_CORE_READY - Smart Home Hub"));
}

void loop() {
    AgentCore.process();
}
""",
    sensors=["DHT22", "PIR", "LDR"],
    actuators=["Relay"],
    displays=["SSD1306"],
    libraries=["Wire", "DHT sensor library", "Adafruit_SSD1306", "Adafruit_GFX"],
    wiring="DHT22: VCC->5V, GND->GND, Data->D2\nPIR: VCC->5V, GND->GND, OUT->D3\nLDR: A0->5V, A1->GND, Wiper->A2\nRelays: IN->D7/8/9\nOLED: SDA->A4, SCL->A5"
)
register_template(SMART_HOME)


# ─── LED Controller ──────────────────────────────────────────────

LED_CONTROLLER = Template(
    name="LED Controller",
    category="lighting",
    description="Addressable LED strip controller with FastLED effects. Agent can control colors, brightness, patterns, and animations.",
    sketch="""/**
 * LED Controller Template
 * AgentCore-enabled LED strip control
 * 
 * Wiring:
 * - LED Strip (WS2812B/NeoPixel): VCC->5V, GND->GND, DIN->D6
 * - Potentiometer: 5V->5V, GND->GND, Wiper->A0
 * - Push Button: D4->GND (with 10k pullup)
 */

#include <AgentCore.h>
#include <FastLED.h>

// LED Configuration
#define LED_PIN 6
#define NUM_LEDS 64
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define BRIGHTNESS 128

CRGB leds[NUM_LEDS];

// Effects
enum Effect {
    EFFECT_SOLID,
    EFFECT_RAINBOW,
    EFFECT_PULSE,
    EFFECT_FIRE,
    EFFECT_WAVE,
    EFFECT_RUNNING,
};

Effect current_effect = EFFECT_SOLID;
CRGB current_color = CRGB::White;
uint8_t speed = 50;

void setup() {
    Serial.begin(115200);
    while (!Serial) { }

    LED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    LED.setBrightness(BRIGHTNESS);
    fill_solid(leds, NUM_LEDS, current_color);
    LED.show();

    // Register sensors
    AgentCore.registerSensor("brightness_pot", []() -> float {
        return analogRead(A0) / 1023.0F;
    });
    AgentCore.registerSensor("button", []() -> float {
        return !digitalRead(4);  // Active low
    });

    // Register actuators
    AgentCore.registerActuator("led_color", [](float value) {
        // Parse RGB from packed value
        int r = (int)value / 65536;
        int g = ((int)value / 256) % 256;
        int b = (int)value % 256;
        current_color = CRGB(r, g, b);
    });
    AgentCore.registerActuator("led_brightness", [](float value) {
        LED.setBrightness((uint8_t)value);
    });
    AgentCore.registerActuator("led_effect", [](float value) {
        current_effect = (Effect)((int)value);
    });
    AgentCore.registerActuator("led_speed", [](float value) {
        speed = (uint8_t)constrain((int)value, 1, 255);
    });

    AgentCore.begin();
    Serial.println(F("AGENT_CORE_READY - LED Controller"));
}

void loop() {
    AgentCore.process();

    // Update LED effects
    uint32_t now = millis();
    switch (current_effect) {
        case EFFECT_SOLID:
            fill_solid(leds, NUM_LEDS, current_color);
            break;
        case EFFECT_RAINBOW:
            for (int i = 0; i < NUM_LEDS; i++) {
                leds[i] = CHSV((i * 256 / NUM_LEDS + now / 20) % 256, 255, BRIGHTNESS);
            }
            break;
        case EFFECT_PULSE:
            fill_solid(leds, NUM_LEDS, current_color);
            for (int i = 0; i < NUM_LEDS; i++) {
                leds[i].nscale8(sin8(now / 32));
            }
            break;
        case EFFECT_WAVE:
            for (int i = 0; i < NUM_LEDS; i++) {
                leds[i] = CHSV(sin8((i * 8 + now / 16) & 0xFF), 255, BRIGHTNESS);
            }
            break;
    }
    LED.show();
    delay(10);
}
""",
    actuators=["WS2812B"],
    libraries=["FastLED"],
    wiring="LED Strip: VCC->5V, GND->GND, DIN->D6\nPotentiometer: 5V->5V, GND->GND, Wiper->A0\nButton: D4->GND (10k pullup)"
)
register_template(LED_CONTROLLER)


# ─── IoT Gateway ──────────────────────────────────────────────────

IOT_GATEWAY = Template(
    name="IoT Gateway",
    category="connectivity",
    description="WiFi-enabled IoT gateway with ESP8266/ESP32. Connects sensors to the internet, supports MQTT and HTTP APIs.",
    sketch="""/**
 * IoT Gateway Template
 * AgentCore-enabled WiFi IoT bridge
 * 
 * Wiring (ESP8266):
 * - ESP8266: VCC->3.3V, GND->GND, TX->D10, RX->D11
 * - DHT22: VCC->3.3V, GND->GND, Data->D2
 * - BME280: VCC->3.3V, GND->GND, SDA->D4, SCL->D5
 * - LED: D13
 */

#include <AgentCore.h>
#include <SoftwareSerial.h>
#include <DHT.h>
#include <Adafruit_BME280.h>
#include <Wire.h>

// WiFi (ESP8266)
SoftwareSerial esp8266(10, 11);  // RX, TX

// Sensors
#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

Adafruit_BME280 bme;

// WiFi credentials (set via AgentCore)
char wifi_ssid[32] = "YOUR_SSID";
char wifi_pass[64] = "YOUR_PASSWORD";
char mqtt_server[64] = "YOUR_MQTT_SERVER";
int mqtt_port = 1883;

// LED indicator
#define LED_PIN 13

void setup() {
    Serial.begin(115200);
    while (!Serial) { }

    esp8266.begin(9600);
    Wire.begin(D4, D5);
    dht.begin();

    pinMode(LED_PIN, OUTPUT);

    // Initialize BME280
    bme.begin(0x76);

    // Register sensors
    AgentCore.registerSensor("temperature", []() -> float {
        return dht.readTemperature();
    });
    AgentCore.registerSensor("humidity", []() -> float {
        return dht.readHumidity();
    });
    AgentCore.registerSensor("pressure", []() -> float {
        return bme.readPressure() / 100.0F;
    });

    // Register WiFi controls
    AgentCore.registerCommand("wifi_connect", [](const char* args) -> bool {
        esp8266.print("AT+CIPSTART=\\"TCP,\\",\\"", mqtt_server);
        esp8666.print("\",");
        esp8266.println(mqtt_port);
        return true;
    });

    AgentCore.begin();
    Serial.println(F("AGENT_CORE_READY - IoT Gateway"));
}

void loop() {
    AgentCore.process();

    // WiFi status LED
    digitalWrite(LED_PIN, (millis() / 1000) % 2);
}
""",
    sensors=["DHT22", "BME280"],
    communication=["ESP8266"],
    libraries=["SoftwareSerial", "DHT sensor library", "Adafruit_BME280", "Wire"],
    wiring="ESP8266: VCC->3.3V, GND->GND, TX->D10, RX->D11\nDHT22: VCC->3.3V, GND->GND, Data->D2\nBME280: VCC->3.3V, GND->GND, SDA->D4, SCL->D5"
)
register_template(IOT_GATEWAY)


# ─── Template Library Registration ────────────────────────────────

# All templates are registered during module import
__all__ = [
    "TEMPLATES",
    "register_template",
    "get_template",
    "list_templates",
    "search_templates",
    "WEATHER_STATION",
    "SMART_PLANT",
    "SECURITY_SYSTEM",
    "SMART_HOME",
    "LED_CONTROLLER",
    "IOT_GATEWAY",
]
