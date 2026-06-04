/**
 * Sensor Read - Analog Sensor with Serial Output
 * Reads an analog sensor on A0 and prints values for serial plotter.
 */
#define SENSOR_PIN A0
void setup() { Serial.begin(115200); while (!Serial) { } Serial.println("SENSOR_READY"); }
void loop() {
  int value = analogRead(SENSOR_PIN);
  float voltage = value * (5.0 / 1023.0);
  Serial.print(value); Serial.print(","); Serial.println(voltage);
  delay(100);
}
