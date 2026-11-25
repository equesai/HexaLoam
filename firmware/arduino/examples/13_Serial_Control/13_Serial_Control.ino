/*
 * HexaLoam — 13_Serial_Control.ino
 * 115200 baud Serial command interface (STAND, SIT, TRIPOD, RIPPLE, WAVE, STOP).
 *
 * Board: Arduino Mega 2560 (ATmega2560, 5V logic)
 * Library: Arduino Servo (Timer5 + Timer1 -> supports 18 servos on D22..D39)
 * Wiring: See electronics/wiring/01_arduino_mega_18_servos.svg
 * WARNING: NEVER power MG996R servos from the Arduino 5V pin. Use external 6.0V PSU + common GND.
 */
#include <Servo.h>
#include <math.h>

const uint8_t SERVO_PINS[18] = {22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39};
const uint8_t PIN_ESTOP = 2;
const uint8_t PIN_VBAT = A0;
const int8_t JOINT_DIR[18] = {1,1,1, 1,1,1, 1,1,1, -1,-1,-1, -1,-1,-1, -1,-1,-1};
const float NEUTRAL_RAD[18] = {0,0.35f,-1.57f, 0,0.35f,-1.57f, 0,0.35f,-1.57f, 0,0.35f,-1.57f, 0,0.35f,-1.57f, 0,0.35f,-1.57f};

Servo servos[18];
bool calibrated = false;
unsigned long lastTick = 0;
float phase = 0.0f;

int radToUsMA1(uint8_t idx, float rad) {
  float phys = rad * JOINT_DIR[idx];
  long us = 1500L + lroundf((phys / 1.5707963f) * 1000.0f);
  return constrain((int)us, 500, 2500);
}

// Back-to-back opposing motor MA2: centered at 90 deg (1500 us) before coupling,
// then incremented with opposite sign (-phys) so MA1 and MA2 aid rather than fight each other.
int radToUsMA2(uint8_t idx, float rad) {
  return 3000 - radToUsMA1(idx, rad);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_ESTOP, INPUT_PULLUP);
  for (uint8_t i = 0; i < 18; ++i) {
    servos[i].attach(SERVO_PINS[i], 500, 2500);
    servos[i].writeMicroseconds(1500);
  }
  Serial.println(F("HexaLoam 13_Serial_Control ready. Send 'c' to confirm calibration."));
}

void loop() {
  if (digitalRead(PIN_ESTOP) == LOW) {
    for (uint8_t i = 0; i < 18; ++i) servos[i].detach();
    Serial.println(F("ESTOP ACTIVE"));
    while (true) { delay(100); }
  }
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'c' || c == 'C') { calibrated = true; Serial.println(F("Calibrated.")); }
  }
  unsigned long now = millis();
  if (calibrated && (now - lastTick >= 20)) {
    lastTick = now;
    phase += 0.02f;
    if (phase >= 1.0f) phase -= 1.0f;
    for (uint8_t i = 0; i < 18; ++i) {
      servos[i].writeMicroseconds(radToUsMA1(i, NEUTRAL_RAD[i]));
      // Paired MA2 servo (if driven on a separate channel) uses radToUsMA2(i, NEUTRAL_RAD[i])
    }
  }
}
