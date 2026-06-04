/**
 * ESP32 WiFi Web Server
 */
#include <WiFi.h>
#include <WebServer.h>
const char* ssid = "YOUR_SSID"; const char* password = "YOUR_PASSWORD";
WebServer server(80);
const String mainPage = "<!DOCTYPE html><html><body><h1>ESP32</h1><button onclick=\"fetch('/toggle')\">Toggle</button></body></html>";
void handleRoot() { server.send(200, "text/html", mainPage); }
void handleToggle() { digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); server.send(200, "text/plain", "Toggled"); }
void setup() { Serial.begin(115200); pinMode(LED_BUILTIN, OUTPUT); WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); } Serial.println(WiFi.localIP()); server.on("/", handleRoot); server.on("/toggle", handleToggle); server.begin(); }
void loop() { server.handleClient(); }
