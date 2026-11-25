// HexaLoam Generic ESP32 Robot Actuator Slave Firmware (v1.0.0)
// Supports Config B (Standalone 18-DOF), Config C (Single ESP32 18-DOF), Config D (Dual ESP32 9-DOF)
#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>
#include "hexaloam_joint_map.h"

#ifndef HEXALOAM_CTRL_ID
#define HEXALOAM_CTRL_ID 1
#endif
#ifndef HEXALOAM_NUM_JOINTS
#define HEXALOAM_NUM_JOINTS 18
#endif
#ifndef HEXALOAM_JOINT_OFFSET
#define HEXALOAM_JOINT_OFFSET 0
#endif
#ifndef HEXALOAM_DUAL_PCA
#define HEXALOAM_DUAL_PCA 1
#endif
#ifndef HEXALOAM_BAUD
#define HEXALOAM_BAUD 460800
#endif

constexpr uint8_t PIN_SDA = 21;
constexpr uint8_t PIN_SCL = 22;
constexpr uint8_t PIN_ESTOP = 4;
constexpr uint8_t PIN_VBAT = 34;
constexpr uint32_t WATCHDOG_TIMEOUT_MS = 500;
constexpr float PCA_OSC_HZ = 25000000.0f;

Adafruit_PWMServoDriver pcaA(0x40);
#if HEXALOAM_DUAL_PCA
Adafruit_PWMServoDriver pcaB(0x41);
#endif
Preferences prefs;

struct JointState {
  float target_rad;
  float current_rad;
  float velocity_rad_s;
  float zero_offset_rad;
  int8_t direction;
  uint16_t min_us;
  uint16_t max_us;
};

JointState joints[HEXALOAM_NUM_JOINTS];
bool armed = false;
bool estop_latched = false;
bool watchdog_fault = false;
uint32_t last_cmd_ms = 0;
uint32_t last_tick_ms = 0;
float max_vel_rad_s = 4.5f;

uint16_t crc16_ccitt(const uint8_t* data, size_t len) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < len; ++i) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (uint8_t b = 0; b < 8; ++b) {
      crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) : (crc << 1);
    }
  }
  return crc;
}

uint16_t us_to_pca_ticks(uint16_t us) {
  float ticks = (static_cast<float>(us) / 20000.0f) * 4096.0f;
  if (ticks < 0) ticks = 0;
  if (ticks > 4095) ticks = 4095;
  return static_cast<uint16_t>(ticks);
}

void write_joint_pwm(uint8_t local_idx, float rad) {
  const auto& meta = hexaloam::JOINT_MAP[HEXALOAM_JOINT_OFFSET + local_idx];
  JointState& st = joints[local_idx];
  float clamped = constrain(rad, meta.min_rad, meta.max_rad);
  float phys = (clamped * st.direction) + st.zero_offset_rad;
  // Back-to-back dual-motor joint (MA1 & MA2): both centered at 90 deg (1500 us) before coupling.
  // MA1 increments +phys while MA2 increments -phys so both rotate the joint in the same physical direction.
  float norm_ma1 = (phys + 1.5707963f) / 3.1415926f;
  float norm_ma2 = (-phys + 1.5707963f) / 3.1415926f;
  uint16_t us_ma1 = static_cast<uint16_t>(constrain(st.min_us + norm_ma1 * (st.max_us - st.min_us), st.min_us, st.max_us));
  uint16_t us_ma2 = static_cast<uint16_t>(constrain(st.min_us + norm_ma2 * (st.max_us - st.min_us), st.min_us, st.max_us));
  uint16_t ticks_ma1 = us_to_pca_ticks(us_ma1);
  (void)us_ma2; // Output on paired/mirrored MA2 channel or hardware-inverted bus when 36-ch expansion is attached
#if HEXALOAM_DUAL_PCA
  if (meta.pca_board == 'A') pcaA.setPWM(meta.pca_channel, 0, ticks_ma1);
  else pcaB.setPWM(meta.pca_channel, 0, ticks_ma1);
#else
  pcaA.setPWM(meta.pca_channel, 0, ticks_ma1);
#endif
}

void enter_safe_stop() {
  armed = false;
  for (uint8_t i = 0; i < HEXALOAM_NUM_JOINTS; ++i) {
#if HEXALOAM_DUAL_PCA
    const auto& meta = hexaloam::JOINT_MAP[HEXALOAM_JOINT_OFFSET + i];
    if (meta.pca_board == 'A') pcaA.setPWM(meta.pca_channel, 0, 0);
    else pcaB.setPWM(meta.pca_channel, 0, 0);
#else
    pcaA.setPWM(hexaloam::JOINT_MAP[HEXALOAM_JOINT_OFFSET + i].pca_channel, 0, 0);
#endif
  }
}

void send_binary_resp(uint16_t seq, uint8_t resp_cmd, const uint8_t* payload, uint16_t len) {
  uint8_t buf[32];
  buf[0] = 0xAA; buf[1] = 0x55;
  buf[2] = 1; buf[3] = HEXALOAM_CTRL_ID;
  buf[4] = seq & 0xFF; buf[5] = (seq >> 8) & 0xFF;
  buf[6] = resp_cmd;
  buf[7] = len & 0xFF; buf[8] = (len >> 8) & 0xFF;
  if (len > 0 && payload) memcpy(&buf[9], payload, len);
  uint16_t crc = crc16_ccitt(&buf[2], 7 + len);
  buf[9 + len] = crc & 0xFF;
  buf[10 + len] = (crc >> 8) & 0xFF;
  Serial.write(buf, 11 + len);
}

void handle_binary_packet(const uint8_t* body, uint16_t len) {
  uint8_t ctrl_id = body[1];
  uint16_t seq = body[2] | (static_cast<uint16_t>(body[3]) << 8);
  uint8_t cmd = body[4];
  uint16_t plen = body[5] | (static_cast<uint16_t>(body[6]) << 8);
  const uint8_t* payload = &body[7];
  if (ctrl_id != HEXALOAM_CTRL_ID && ctrl_id != 0xFF) return;
  last_cmd_ms = millis();
  watchdog_fault = false;

  switch (cmd) {
    case 0x01: // HELLO
    case 0x30: // HEARTBEAT
      send_binary_resp(seq, 0x80, nullptr, 0);
      break;
    case 0x10: // ARM
      if (estop_latched || digitalRead(PIN_ESTOP) == LOW) {
        uint8_t err = 6; send_binary_resp(seq, 0x81, &err, 1);
      } else {
        armed = true;
        send_binary_resp(seq, 0x80, nullptr, 0);
      }
      break;
    case 0x11: // DISARM
      enter_safe_stop();
      send_binary_resp(seq, 0x80, nullptr, 0);
      break;
    case 0x40: // EMERGENCY_STOP
      estop_latched = true;
      enter_safe_stop();
      send_binary_resp(seq, 0x80, nullptr, 0);
      break;
    case 0x41: // CLEAR_FAULT
      if (digitalRead(PIN_ESTOP) == HIGH) estop_latched = false;
      watchdog_fault = false;
      send_binary_resp(seq, 0x80, nullptr, 0);
      break;
    case 0x13: // SET_JOINTS
      if (!armed || estop_latched) {
        uint8_t err = 4; send_binary_resp(seq, 0x81, &err, 1); break;
      }
      if (plen >= 5) {
        uint8_t count = payload[4];
        for (uint8_t i = 0; i < count && i < HEXALOAM_NUM_JOINTS; ++i) {
          int16_t mrad = static_cast<int16_t>(payload[5 + 2 * i] | (payload[6 + 2 * i] << 8));
          joints[i].target_rad = static_cast<float>(mrad) / 1000.0f;
        }
        send_binary_resp(seq, 0x80, nullptr, 0);
      } else {
        uint8_t err = 2; send_binary_resp(seq, 0x81, &err, 1);
      }
      break;
    default: {
      uint8_t err = 3; send_binary_resp(seq, 0x81, &err, 1);
      break;
    }
  }
}

void setup() {
  Serial.begin(HEXALOAM_BAUD);
  pinMode(PIN_ESTOP, INPUT_PULLUP);
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);
  pcaA.begin();
  pcaA.setOscillatorFrequency(PCA_OSC_HZ);
  pcaA.setPWMFreq(hexaloam::SERVO_PWM_HZ);
#if HEXALOAM_DUAL_PCA
  pcaB.begin();
  pcaB.setOscillatorFrequency(PCA_OSC_HZ);
  pcaB.setPWMFreq(hexaloam::SERVO_PWM_HZ);
#endif
  prefs.begin("hexaloam", false);
  for (uint8_t i = 0; i < HEXALOAM_NUM_JOINTS; ++i) {
    const auto& meta = hexaloam::JOINT_MAP[HEXALOAM_JOINT_OFFSET + i];
    joints[i] = {meta.neutral_rad, meta.neutral_rad, 0.0f, 0.0f, meta.direction, hexaloam::SERVO_MIN_US, hexaloam::SERVO_MAX_US};
  }
  enter_safe_stop();
  last_cmd_ms = millis();
  last_tick_ms = millis();
}

void loop() {
  uint32_t now = millis();
  if (digitalRead(PIN_ESTOP) == LOW) {
    estop_latched = true;
    enter_safe_stop();
  }
  if (armed && (now - last_cmd_ms > WATCHDOG_TIMEOUT_MS)) {
    watchdog_fault = true;
    enter_safe_stop();
  }

  // Binary frame parser
  static uint8_t rx_buf[256];
  static uint16_t rx_idx = 0;
  while (Serial.available()) {
    uint8_t b = Serial.read();
    if (rx_idx == 0 && b != 0xAA) {
      if (b == '{') {
        String line = Serial.readStringUntil('\n');
        JsonDocument doc;
        if (deserializeJson(doc, "{" + line) == DeserializationError::Ok) {
          const char* cmd = doc["cmd"] | "";
          last_cmd_ms = now;
          if (strcmp(cmd, "HELLO") == 0) Serial.println("{\"status\":\"OK\",\"fw\":\"1.0.0\",\"robot\":\"HexaLoam\"}");
          else if (strcmp(cmd, "ARM") == 0) { armed = !estop_latched; Serial.println("{\"status\":\"ARMED\"}"); }
          else if (strcmp(cmd, "DISARM") == 0) { enter_safe_stop(); Serial.println("{\"status\":\"DISARMED\"}"); }
          else if (strcmp(cmd, "EMERGENCY_STOP") == 0) { estop_latched = true; enter_safe_stop(); Serial.println("{\"status\":\"ESTOP\"}"); }
        }
      }
      continue;
    }
    rx_buf[rx_idx++] = b;
    if (rx_idx == 2 && b != 0x55) { rx_idx = 0; continue; }
    if (rx_idx >= 11) {
      uint16_t plen = rx_buf[7] | (static_cast<uint16_t>(rx_buf[8]) << 8);
      uint16_t total = 11 + plen;
      if (total > sizeof(rx_buf)) { rx_idx = 0; continue; }
      if (rx_idx == total) {
        uint16_t crc_rx = rx_buf[9 + plen] | (static_cast<uint16_t>(rx_buf[10 + plen]) << 8);
        if (crc_rx == crc16_ccitt(&rx_buf[2], 7 + plen)) {
          handle_binary_packet(&rx_buf[2], 7 + plen);
        }
        rx_idx = 0;
      }
    }
  }

  if (armed && (now - last_tick_ms >= 20)) {
    float dt = (now - last_tick_ms) / 1000.0f;
    last_tick_ms = now;
    float max_step = max_vel_rad_s * dt;
    for (uint8_t i = 0; i < HEXALOAM_NUM_JOINTS; ++i) {
      float diff = joints[i].target_rad - joints[i].current_rad;
      if (fabs(diff) > max_step) diff = (diff > 0 ? max_step : -max_step);
      joints[i].current_rad += diff;
      write_joint_pwm(i, joints[i].current_rad);
    }
  }
}
