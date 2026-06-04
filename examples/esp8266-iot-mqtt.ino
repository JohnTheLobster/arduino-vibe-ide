/**
 * ESP8266 MQTT Client
 */
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
const char* ssid = "YOUR_SSID"; const char* password = "YOUR_PASSWORD"; const char* mqtt_server = "YOUR_MQTT_BROKER";
WiFiClient espClient; PubSubClient client(espClient);
void setup() { Serial.begin(115200); WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) delay(500); client.setServer(mqtt_server, 1883); }
void loop() { while (!client.connected()) { if (client.connect("ESP8266Client")) { client.subscribe("home/commands"); } delay(500); } client.publish("home/sensor", String(analogRead(A0)).c_str()); client.loop(); delay(2000); }
