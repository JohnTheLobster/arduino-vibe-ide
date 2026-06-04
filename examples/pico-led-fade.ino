/**
 * RP2040 PWM LED Fade
 */
#define LED_PIN 25
void setup() { ledcSetup(0, 5000, 8); ledcAttachPin(LED_PIN, 0); }
void loop() { for (int i = 0; i <= 255; i++) { ledcWrite(0, i); delay(5); } for (int i = 255; i >= 0; i--) { ledcWrite(0, i); delay(5); } }
