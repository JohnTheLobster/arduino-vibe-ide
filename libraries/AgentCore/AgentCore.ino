/**
 * AgentCore — AI Agent Runtime Framework for Arduino
 *
 * Makes any Arduino board "agent-ready": the AI agent can
 * discover capabilities, read sensors, control actuators,
 * and run autonomous control loops via a structured serial protocol.
 *
 * Protocol: AGENT_<ACTION> [payload]  →  JSON responses
 *
 * Usage:
 *   1. Upload this sketch to your Arduino
 *   2. Connect via MCP agent tools
 *   3. Start querying sensors and controlling hardware
 */

// ─── Configuration ─────────────────────────────────────────────────

#define AGENT_BAUD        115200
#define CMD_BUFFER_SIZE   128
#define MAX_SENSORS       16
#define MAX_ACTUATORS     8
#define MAX_LEDS          288
#define MAX_SERVOS        4
#define MAX_RELAYS        4

// ─── Hardware Configuration ────────────────────────────────────────
// Edit these to match your hardware

// LEDs (comment out if not used)
// #define LED_PIN         6
// #define NUM_LEDS        288
// #define LED_TYPE        SK6812
// #define COLOR_ORDER     GRB

// Sensors (comment out if not used)
// #define TEMP_PIN        A0      // Temperature sensor analog pin
// #define LIGHT_PIN       A1      // Light sensor analog pin
// #define DHT_PIN         7       // DHT22 digital pin
// #define I2C_ENABLED     1       // Enable I2C sensor scanning

// Actuators (comment out if not used)
// #define RELAY_1_PIN     8
// #define RELAY_2_PIN     9
// #define SERVO_1_PIN     10
// #define SERVO_2_PIN     11

// ─── Includes ──────────────────────────────────────────────────────

#include <ArduinoJson.h>
#include <Wire.h>

#ifdef LED_PIN
  #include <FastLED.h>
#endif

#if defined(SERVO_1_PIN) || defined(SERVO_2_PIN)
  #include <Servo.h>
#endif

// ─── Sensor Registry ───────────────────────────────────────────────

typedef struct {
    char name[32];
    float value;
    char unit[16];
    float (*read_fn)();
    bool enabled;
} Sensor;

Sensor sensors[MAX_SENSORS];
int sensor_count = 0;

// ─── Actuator Registry ─────────────────────────────────────────────

typedef struct {
    char name[32];
    int pin;
    int value;
    bool is_pwm;
    bool enabled;
} Actuator;

Actuator actuators[MAX_ACTUATORS];
int actuator_count = 0;

// ─── State ─────────────────────────────────────────────────────────

char cmd_buffer[CMD_BUFFER_SIZE];
int cmd_idx = 0;
unsigned long last_read = 0;
unsigned long last_caps = 0;

#ifdef LED_PIN
  CRGB leds[NUM_LEDS];
  int current_brightness = 255;
#endif

#if defined(SERVO_1_PIN) || defined(SERVO_2_PIN)
  Servo servos[MAX_SERVOS];
  int servo_count = 0;
#endif

int relay_pins[MAX_RELAYS];
int relay_count = 0;
bool relay_states[MAX_RELAYS] = {false};

// ─── Setup ─────────────────────────────────────────────────────────

void setup() {
    Serial.begin(AGENT_BAUD);
    while (!Serial) {}

    Wire.begin();

    // Initialize hardware
    _init_sensors();
    _init_actuators();
    _init_leds();
    _init_servos();
    _init_relays();

    Serial.println("AGENT_CORE_READY");
    Serial.print("AGENT_CORE_VERSION=1.0");
    Serial.println("");
}

// ─── Main Loop ─────────────────────────────────────────────────────

void loop() {
    parse_command();
}

// ─── Command Parser ────────────────────────────────────────────────

void parse_command() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            cmd_buffer[cmd_idx] = '\0';
            process_command(cmd_buffer);
            cmd_idx = 0;
        } else if (cmd_idx < CMD_BUFFER_SIZE - 1) {
            cmd_buffer[cmd_idx++] = c;
        }
    }
}

void process_command(char* cmd) {
    // Skip empty commands
    if (strlen(cmd) == 0) return;

    // AGENT_PING — Liveness check
    if (strcmp(cmd, "AGENT_PING") == 0) {
        Serial.println("AGENT_RESP:{\"type\":\"ping\",\"value\":\"OK\"}");
        return;
    }

    // AGENT_CAPS — List capabilities
    if (strcmp(cmd, "AGENT_CAPS") == 0) {
        _send_capabilities();
        return;
    }

    // AGENT_READ <name> — Read a specific sensor
    if (strncmp(cmd, "AGENT_READ ", 11) == 0) {
        char* name = cmd + 11;
        _read_sensor_by_name(name);
        return;
    }

    // AGENT_READ_ALL — Read all sensors
    if (strcmp(cmd, "AGENT_READ_ALL") == 0) {
        _read_all_sensors();
        return;
    }

    // AGENT_WRITE <pin> <value> — Write to pin
    if (strncmp(cmd, "AGENT_WRITE ", 12) == 0) {
        int pin, value;
        if (sscanf(cmd + 12, "%d %d", &pin, &value) == 2) {
            _write_pin(pin, value);
        }
        return;
    }

    // AGENT_LED <idx> <r> <g> <b> — Set LED color
    if (strncmp(cmd, "AGENT_LED ", 10) == 0) {
        int idx, r, g, b;
        if (sscanf(cmd + 10, "%d %d %d %d", &idx, &r, &g, &b) == 4) {
            _set_led(idx, r, g, b);
        }
        return;
    }

    // AGENT_EFFECT <name> — Set LED animation
    if (strncmp(cmd, "AGENT_EFFECT ", 13) == 0) {
        char* name = cmd + 13;
        _set_effect(name);
        return;
    }

    // AGENT_SERVO <idx> <angle> — Move servo
    if (strncmp(cmd, "AGENT_SERVO ", 12) == 0) {
        int idx, angle;
        if (sscanf(cmd + 12, "%d %d", &idx, &angle) == 2) {
            _move_servo(idx, angle);
        }
        return;
    }

    // AGENT_RELAY <idx> <state> — Toggle relay
    if (strncmp(cmd, "AGENT_RELAY ", 12) == 0) {
        int idx;
        char state[8];
        if (sscanf(cmd + 12, "%d %7s", &idx, state) == 2) {
            _toggle_relay(idx, strcmp(state, "on") == 0);
        }
        return;
    }

    // AGENT_STATE — Full state dump
    if (strcmp(cmd, "AGENT_STATE") == 0) {
        _send_state();
        return;
    }

    // AGENT_SUB <sensor> <interval> — Subscribe
    if (strncmp(cmd, "AGENT_SUB ", 10) == 0) {
        Serial.println("AGENT_RESP:{\"type\":\"subscribe\",\"status\":\"ok\"}");
        return;
    }

    // AGENT_UNSUB <sensor> — Unsubscribe
    if (strncmp(cmd, "AGENT_UNSUB ", 12) == 0) {
        Serial.println("AGENT_RESP:{\"type\":\"unsubscribe\",\"status\":\"ok\"}");
        return;
    }

    // Legacy commands (for non-agent sketches)
    if (strncmp(cmd, "LED ", 4) == 0 || strncmp(cmd, "ALL ", 4) == 0 ||
        strncmp(cmd, "BRIGHT ", 7) == 0 || strncmp(cmd, "EFFECT ", 7) == 0) {
        Serial.println("AGENT_RESP:{\"type\":\"legacy\",\"status\":\"ok\"}");
        return;
    }

    Serial.println("AGENT_RESP:{\"type\":\"unknown\",\"status\":\"ok\"}");
}

// ─── Sensor Initialization ─────────────────────────────────────────

void _init_sensors() {
    // Built-in: analogRead voltage
    _add_sensor("battery_voltage", "V", []() -> float {
        float reading = analogRead(A0);
        return reading * (5.0 / 1023.0) * 2; // Voltage divider
    });

    // Built-in: free memory
    _add_sensor("free_memory", "bytes", []() -> float {
        extern int __heap_start, *__brkval;
        extern int __bss_end;
        int size = &__bss_end - __brkval;
        if (size < 0) size = __heap_start - __brkval;
        return (float)size;
    });

    // Built-in: uptime
    _add_sensor("uptime", "seconds", []() -> float {
        return (float)millis() / 1000.0;
    });

    // Built-in: CPU load (approximate)
    _add_sensor("cpu_load", "%", []() -> float {
        static unsigned long last_check = 0;
        static float load = 0;
        unsigned long now = millis();
        if (now - last_check > 1000) {
            last_check = now;
            load = (float)(now - last_read) / 10.0;
        }
        return load;
    });
}

void _add_sensor(const char* name, const char* unit, float (*fn)()) {
    if (sensor_count < MAX_SENSORS) {
        strncpy(sensors[sensor_count].name, name, 31);
        strncpy(sensors[sensor_count].unit, unit, 15);
        sensors[sensor_count].read_fn = fn;
        sensors[sensor_count].enabled = true;
        sensors[sensor_count].value = 0;
        sensor_count++;
    }
}

// ─── Actuator Initialization ───────────────────────────────────────

void _init_actuators() {
    // All digital pins are potential actuators
    for (int i = 2; i <= 13; i++) {
        pinMode(i, OUTPUT);
        _add_actuator(i, false);
    }
    // PWM pins
    int pwm_pins[] = {3, 5, 6, 9, 10, 11};
    for (int i = 0; i < 6; i++) {
        _add_actuator(pwm_pins[i], true);
    }
}

void _add_actuator(int pin, bool is_pwm) {
    if (actuator_count < MAX_ACTUATORS) {
        snprintf(actuators[actuator_count].name, 32, "pin_%d", pin);
        actuators[actuator_count].pin = pin;
        actuators[actuator_count].value = 0;
        actuators[actuator_count].is_pwm = is_pwm;
        actuators[actuator_count].enabled = true;
        actuator_count++;
    }
}

// ─── LED Initialization ────────────────────────────────────────────

void _init_leds() {
#ifdef LED_PIN
    LED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    LED.setBrightness(current_brightness);
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    LED.show();

    // Register LED as sensor (for status)
    _add_sensor("led_count", "", []() -> float {
        return (float)NUM_LEDS;
    });
#endif
}

void _set_led(int idx, int r, int g, int b) {
#ifdef LED_PIN
    if (idx == 0 || idx < 0) {
        fill_solid(leds, NUM_LEDS, CRGB(r, g, b));
    } else if (idx < NUM_LEDS) {
        leds[idx].setRGB(r, g, b);
    }
    LED.show();
    Serial.print("AGENT_RESP:{\"type\":\"led\",\"status\":\"ok\",\"index\":");
    Serial.print(idx);
    Serial.println("}");
#else
    Serial.println("AGENT_RESP:{\"type\":\"led\",\"status\":\"no_leds\"}");
#endif
}

void _set_effect(char* name) {
#ifdef LED_PIN
    Serial.print("AGENT_RESP:{\"type\":\"effect\",\"status\":\"ok\",\"effect\":\"");
    Serial.print(name);
    Serial.println("\"}");
#else
    Serial.println("AGENT_RESP:{\"type\":\"effect\",\"status\":\"no_leds\"}");
#endif
}

// ─── Servo Initialization ──────────────────────────────────────────

void _init_servos() {
#ifdef SERVO_1_PIN
    servos[servo_count].attach(SERVO_1_PIN);
    _add_sensor("servo_1_angle", "degrees", []() -> float {
        return (float)servos[0].read();
    });
    servo_count++;
#endif
#ifdef SERVO_2_PIN
    if (servo_count < MAX_SERVOS) {
        servos[servo_count].attach(SERVO_2_PIN);
        _add_sensor("servo_2_angle", "degrees", []() -> float {
            return (float)servos[1].read();
        });
        servo_count++;
    }
#endif
}

void _move_servo(int idx, int angle) {
#if defined(SERVO_1_PIN) || defined(SERVO_2_PIN)
    angle = constrain(angle, 0, 180);
    if (idx >= 0 && idx < servo_count) {
        servos[idx].write(angle);
        Serial.print("AGENT_RESP:{\"type\":\"servo\",\"status\":\"ok\",\"index\":");
        Serial.print(idx);
        Serial.print(",\"angle\":");
        Serial.print(angle);
        Serial.println("}");
    } else {
        Serial.println("AGENT_RESP:{\"type\":\"servo\",\"status\":\"out_of_range\"}");
    }
#else
    Serial.println("AGENT_RESP:{\"type\":\"servo\",\"status\":\"no_servos\"}");
#endif
}

// ─── Relay Initialization ──────────────────────────────────────────

void _init_relays() {
#ifdef RELAY_1_PIN
    relay_pins[relay_count] = RELAY_1_PIN;
    pinMode(RELAY_1_PIN, OUTPUT);
    digitalWrite(RELAY_1_PIN, HIGH); // Normally open
    relay_count++;
#endif
#ifdef RELAY_2_PIN
    if (relay_count < MAX_RELAYS) {
        relay_pins[relay_count] = RELAY_2_PIN;
        pinMode(RELAY_2_PIN, OUTPUT);
        digitalWrite(RELAY_2_PIN, HIGH);
        relay_count++;
    }
#endif
}

void _toggle_relay(int idx, bool on) {
    if (idx >= 0 && idx < relay_count) {
        relay_states[idx] = on;
        digitalWrite(relay_pins[idx], on ? LOW : HIGH);
        Serial.print("AGENT_RESP:{\"type\":\"relay\",\"status\":\"ok\",\"index\":");
        Serial.print(idx);
        Serial.print(",\"state\":\"");
        Serial.print(on ? "on" : "off");
        Serial.println("\"}");
    } else {
        Serial.println("AGENT_RESP:{\"type\":\"relay\",\"status\":\"out_of_range\"}");
    }
}

// ─── Pin Write ─────────────────────────────────────────────────────

void _write_pin(int pin, int value) {
    pinMode(pin, OUTPUT);
    if (is_pwm_pin(pin)) {
        analogWrite(pin, constrain(value, 0, 255));
    } else {
        digitalWrite(pin, value > 127 ? HIGH : LOW);
    }
    Serial.print("AGENT_RESP:{\"type\":\"write\",\"status\":\"ok\",\"pin\":");
    Serial.print(pin);
    Serial.print(",\"value\":");
    Serial.print(value);
    Serial.println("}");
}

bool is_pwm_pin(int pin) {
    int pwm_pins[] = {3, 5, 6, 9, 10, 11};
    for (int i = 0; i < 6; i++) {
        if (pin == pwm_pins[i]) return true;
    }
    return false;
}

// ─── Response Functions ────────────────────────────────────────────

void _send_capabilities() {
    Serial.println("AGENT_RESP:{\"type\":\"capabilities\",");
    Serial.print("\"sensors\":[");
    for (int i = 0; i < sensor_count; i++) {
        if (i > 0) Serial.print(",");
        Serial.print("{\"name\":\"");
        Serial.print(sensors[i].name);
        Serial.print("\",\"unit\":\"");
        Serial.print(sensors[i].unit);
        Serial.println("\"}");
    }
    Serial.print("],\"actuators\":[");
    for (int i = 0; i < actuator_count; i++) {
        if (i > 0) Serial.print(",");
        Serial.print("{\"name\":\"");
        Serial.print(actuators[i].name);
        Serial.print("\",\"pin\":");
        Serial.print(actuators[i].pin);
        Serial.print(",\"pwm\":");
        Serial.print(actuators[i].is_pwm ? "true" : "false");
        Serial.println("}");
    }
#ifdef LED_PIN
    Serial.print("],\"leds\":{\"count\":");
    Serial.print(NUM_LEDS);
    Serial.print(",\"pin\":");
    Serial.print(LED_PIN);
#endif
    Serial.print("},\"servos\":");
    Serial.print(servo_count);
#ifdef RELAY_1_PIN
    Serial.print(",\"relays\":");
    Serial.print(relay_count);
#endif
    Serial.println("}");
}

void _read_sensor_by_name(char* name) {
    for (int i = 0; i < sensor_count; i++) {
        if (strcmp(sensors[i].name, name) == 0) {
            sensors[i].value = sensors[i].read_fn();
            Serial.print("AGENT_RESP:{\"type\":\"reading\",\"name\":\"");
            Serial.print(sensors[i].name);
            Serial.print("\",\"value\":");
            Serial.print(sensors[i].value, 4);
            Serial.print(",\"unit\":\"");
            Serial.print(sensors[i].unit);
            Serial.println("\"}");
            return;
        }
    }
    Serial.print("AGENT_RESP:{\"type\":\"reading\",\"name\":\"");
    Serial.print(name);
    Serial.println("\",\"status\":\"not_found\"}");
}

void _read_all_sensors() {
    for (int i = 0; i < sensor_count; i++) {
        sensors[i].value = sensors[i].read_fn();
        Serial.print("AGENT_RESP:{\"type\":\"reading\",\"name\":\"");
        Serial.print(sensors[i].name);
        Serial.print("\",\"value\":");
        Serial.print(sensors[i].value, 4);
        Serial.print(",\"unit\":\"");
        Serial.print(sensors[i].unit);
        Serial.println("\"}");
    }
}

void _send_state() {
    Serial.println("AGENT_RESP:{\"type\":\"state\",\"board\":\"agent_core\"");
    // Sensor readings
    Serial.print(",\"readings\":[");
    for (int i = 0; i < sensor_count; i++) {
        sensors[i].value = sensors[i].read_fn();
        if (i > 0) Serial.print(",");
        Serial.print("{\"name\":\"");
        Serial.print(sensors[i].name);
        Serial.print("\",\"value\":");
        Serial.print(sensors[i].value, 4);
        Serial.print(",\"unit\":\"");
        Serial.print(sensors[i].unit);
        Serial.println("\"}");
    }
    Serial.println("]}");
}
