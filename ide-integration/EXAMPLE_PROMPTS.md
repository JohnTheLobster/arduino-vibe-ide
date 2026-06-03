# Arduino Vibe IDE - Example Prompts for Claude Code

## Basic Sketch Generation
```
claude code "Generate an Arduino sketch that blinks an LED on pin 13 every second"
claude code "Create a sketch to read temperature from a DHT22 sensor and print to serial"
claude code "Build a servo motor control sketch with serial command interface"
```

## LED Control
```
claude code "Generate a rainbow LED animation for an SK6812 strip on pin 6 with 288 LEDs"
claude code "Create a pulse animation that changes color from red to blue"
claude code "Build an IR remote control sketch for LED strip with preset colors"
```

## AgentCore Templates
```
claude code "Show me the weather station template"
claude code "Get the smart plant monitor template and explain the wiring"
claude code "List all available templates and their hardware requirements"
```

## Compilation and Upload
```
claude code "Compile the sketch at /home/john/projects/arduino/my-sketch.ino"
claude code "Compile and upload my LED animation sketch to /dev/ttyACM0"
claude code "Build and flash the weather station template to my Arduino Nano"
```

## Device Discovery
```
claude code "List all connected Arduino devices"
claude code "Verify the board connected at /dev/ttyACM0"
claude code "Check what modules are connected to my Arduino"
```

## AgentCore Bridge
```
claude code "Connect to AgentCore device at /dev/ttyACM0 and ping it"
claude code "Read all sensors from my AgentCore device"
claude code "Get the capabilities of my connected Arduino"
claude code "Control LED on pin 13 to turn on"
```

## Project Management
```
claude code "Create a new project called 'Smart Garden' for arduino:avr:nano"
claude code "Save my current sketch to the Smart Garden project"
claude code "List all my Arduino projects"
claude code "Backup the Smart Garden project"
```

## Full Vibe Coding Workflow
```
claude code "I have an Arduino Nano with an SK6812 LED strip on pin 6. 
Generate a sketch that creates a fire effect animation with 
rainbow colors and 150 speed. Compile it and upload to /dev/ttyACM0"

claude code "Build a smart plant monitor using the AgentCore template. 
It should read soil moisture and temperature, display on OLED, 
and trigger irrigation when moisture is low. Compile and flash to my Nano."

claude code "Create a weather station that reads temperature, humidity, 
and pressure from a BME280 sensor. Display readings on an OLED screen. 
Add serial commands to adjust update interval. Compile and upload."
```

## Using MCP Tools Directly
```
claude code "Use generate_sketch with prompt 'blink LED' and board 'arduino:avr:nano'"
claude code "Use compile_sketch_tool on /home/john/projects/arduino/test.ino"
claude code "Use upload_sketch_tool with sketch at /home/john/projects/arduino/test.ino and port /dev/ttyACM0"
claude code "Use list_templates_tool to see all templates"
claude code "Use get_template_tool with name 'weather-station'"
claude code "Use agent_build_sketch with prompt 'temperature sensor' and board 'arduino:avr:nano'"
```
