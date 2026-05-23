/*
 * ESP32-S3 security sensor node prototype.
 *
 * Hardware:
 * - TCRT5000 infrared reflection module on a digital GPIO pin.
 * - GY-521 / MPU6050 on I2C.
 *
 * This sketch is intentionally self-contained and has not been tested on real
 * hardware in this repository session. It implements the board-side logic that
 * mirrors the Python alarm model: level 1 for infrared proximity and level 3
 * for exhibit movement.
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include "mbedtls/md.h"
#include "time.h"

// ========================= User configuration =========================
const char *WIFI_SSID = "YOUR_WIFI_SSID";
const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char *MQTT_HOST = "YOUR_HUAWEI_IOTDA_HOST";
const uint16_t MQTT_PORT = 8883;
const bool MQTT_USE_TLS = true;

const char *DEVICE_ID = "YOUR_DEVICE_ID";
const char *DEVICE_SECRET = "YOUR_DEVICE_SECRET";

// Optional: paste values from Huawei's device connection key file.
// If both values are non-empty, they are used directly instead of dynamic HMAC.
const char *MQTT_CLIENT_ID = "";
const char *MQTT_PASSWORD = "";

const char *SERVICE_ID = "Security";

const int TCRT_DO_PIN = 18;
const bool TCRT_ACTIVE_LOW = true;

const int MPU_SDA_PIN = 21;
const int MPU_SCL_PIN = 22;
const uint8_t MPU6050_ADDR = 0x68;

const uint8_t IR_TRIGGER_SAMPLES = 2;
const uint8_t IR_CLEAR_SAMPLES = 3;

const float ACCEL_DELTA_THRESHOLD_G = 0.35f;
const float GYRO_THRESHOLD_DPS = 80.0f;
const uint8_t MPU_TRIGGER_SAMPLES = 2;
const uint8_t MPU_CLEAR_SAMPLES = 5;
const bool LATCH_IMU_ALARM_UNTIL_SERIAL_RESET = true;
// =====================================================================

enum AlarmLevel {
  ALARM_SAFE = 0,
  ALARM_IR = 1,
  ALARM_VISION = 2,
  ALARM_IMU = 3,
};

struct MPUReading {
  float ax_g;
  float ay_g;
  float az_g;
  float gx_dps;
  float gy_dps;
  float gz_dps;
};

struct MPUStatus {
  bool moved;
  bool triggered_now;
  bool cleared_now;
  float accel_magnitude_g;
  float accel_delta_g;
  float gyro_magnitude_dps;
};

WiFiClient plainClient;
WiFiClientSecure secureClient;
PubSubClient mqttClient;

bool irDetected = false;
bool imuMoved = false;
bool imuLatched = false;
uint8_t irTriggerCount = 0;
uint8_t irClearCount = 0;
uint8_t mpuTriggerCount = 0;
uint8_t mpuClearCount = 0;
float mpuBaselineAccelG = 1.0f;
AlarmLevel lastReportedLevel = ALARM_SAFE;
bool lastReportedIr = false;
bool lastReportedImu = false;

String mqttTopic() {
  return String("$oc/devices/") + DEVICE_ID + "/sys/properties/report";
}

String utcHourTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo, 5000)) {
    return "";
  }
  char buffer[16];
  strftime(buffer, sizeof(buffer), "%Y%m%d%H", &timeinfo);
  return String(buffer);
}

String isoEventTime() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo, 1000)) {
    return "";
  }
  char buffer[32];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}

String hmacSha256Hex(const String &key, const String &message) {
  byte digest[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t mdType = MBEDTLS_MD_SHA256;

  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(mdType), 1);
  mbedtls_md_hmac_starts(&ctx, reinterpret_cast<const unsigned char *>(key.c_str()), key.length());
  mbedtls_md_hmac_update(&ctx, reinterpret_cast<const unsigned char *>(message.c_str()), message.length());
  mbedtls_md_hmac_finish(&ctx, digest);
  mbedtls_md_free(&ctx);

  char output[65];
  for (int i = 0; i < 32; i++) {
    sprintf(output + (i * 2), "%02x", digest[i]);
  }
  output[64] = '\0';
  return String(output);
}

String resolvedClientId() {
  if (strlen(MQTT_CLIENT_ID) > 0) {
    return String(MQTT_CLIENT_ID);
  }
  String timestamp = utcHourTimestamp();
  return String(DEVICE_ID) + "_0_0_" + timestamp;
}

String resolvedPassword() {
  if (strlen(MQTT_PASSWORD) > 0) {
    return String(MQTT_PASSWORD);
  }
  String timestamp = utcHourTimestamp();
  return hmacSha256Hex(timestamp, DEVICE_SECRET);
}

void setupWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Wi-Fi connected, IP=");
  Serial.println(WiFi.localIP());
}

void setupTimeForHuaweiAuth() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  String timestamp = utcHourTimestamp();
  if (timestamp.length() == 0) {
    Serial.println("Warning: NTP time unavailable. Dynamic Huawei MQTT auth may fail.");
  } else {
    Serial.print("UTC auth timestamp=");
    Serial.println(timestamp);
  }
}

void reconnectMqtt() {
  while (!mqttClient.connected()) {
    String clientId = resolvedClientId();
    String password = resolvedPassword();
    Serial.print("Connecting MQTT as ");
    Serial.println(DEVICE_ID);

    if (mqttClient.connect(clientId.c_str(), DEVICE_ID, password.c_str())) {
      Serial.println("MQTT connected");
    } else {
      Serial.print("MQTT failed, state=");
      Serial.println(mqttClient.state());
      delay(5000);
    }
  }
}

void writeMpuRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

int16_t readInt16() {
  uint8_t high = Wire.read();
  uint8_t low = Wire.read();
  return static_cast<int16_t>((high << 8) | low);
}

bool readMpu(MPUReading &reading) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  if (Wire.requestFrom(MPU6050_ADDR, static_cast<uint8_t>(14)) != 14) {
    return false;
  }

  int16_t rawAx = readInt16();
  int16_t rawAy = readInt16();
  int16_t rawAz = readInt16();
  readInt16();  // temperature, unused
  int16_t rawGx = readInt16();
  int16_t rawGy = readInt16();
  int16_t rawGz = readInt16();

  reading.ax_g = rawAx / 16384.0f;
  reading.ay_g = rawAy / 16384.0f;
  reading.az_g = rawAz / 16384.0f;
  reading.gx_dps = rawGx / 131.0f;
  reading.gy_dps = rawGy / 131.0f;
  reading.gz_dps = rawGz / 131.0f;
  return true;
}

float vectorMagnitude(float x, float y, float z) {
  return sqrtf(x * x + y * y + z * z);
}

void setupMpu6050() {
  Wire.begin(MPU_SDA_PIN, MPU_SCL_PIN);
  writeMpuRegister(0x6B, 0x00);  // wake up
  writeMpuRegister(0x1A, 0x03);  // DLPF
  writeMpuRegister(0x1B, 0x00);  // gyro +/-250 dps
  writeMpuRegister(0x1C, 0x00);  // accel +/-2g
  delay(100);

  MPUReading reading;
  if (readMpu(reading)) {
    mpuBaselineAccelG = vectorMagnitude(reading.ax_g, reading.ay_g, reading.az_g);
    Serial.print("MPU6050 baseline accel=");
    Serial.println(mpuBaselineAccelG, 3);
  } else {
    Serial.println("Warning: failed to read MPU6050 during setup");
  }
}

bool updateIrDetector() {
  bool rawLevel = digitalRead(TCRT_DO_PIN) == HIGH;
  bool rawActive = TCRT_ACTIVE_LOW ? !rawLevel : rawLevel;

  if (rawActive) {
    irTriggerCount++;
    irClearCount = 0;
    if (!irDetected && irTriggerCount >= IR_TRIGGER_SAMPLES) {
      irDetected = true;
      return true;
    }
  } else {
    irTriggerCount = 0;
    if (irDetected) {
      irClearCount++;
      if (irClearCount >= IR_CLEAR_SAMPLES) {
        irDetected = false;
      }
    }
  }
  return false;
}

MPUStatus updateMpuDetector(const MPUReading &reading) {
  MPUStatus status;
  status.accel_magnitude_g = vectorMagnitude(reading.ax_g, reading.ay_g, reading.az_g);
  status.accel_delta_g = fabsf(status.accel_magnitude_g - mpuBaselineAccelG);
  status.gyro_magnitude_dps = vectorMagnitude(reading.gx_dps, reading.gy_dps, reading.gz_dps);
  status.triggered_now = false;
  status.cleared_now = false;

  bool candidate = status.accel_delta_g >= ACCEL_DELTA_THRESHOLD_G ||
                   status.gyro_magnitude_dps >= GYRO_THRESHOLD_DPS;
  if (candidate) {
    mpuTriggerCount++;
    mpuClearCount = 0;
    if (!imuMoved && mpuTriggerCount >= MPU_TRIGGER_SAMPLES) {
      imuMoved = true;
      imuLatched = true;
      status.triggered_now = true;
    }
  } else {
    mpuTriggerCount = 0;
    if (imuMoved && !LATCH_IMU_ALARM_UNTIL_SERIAL_RESET) {
      mpuClearCount++;
      if (mpuClearCount >= MPU_CLEAR_SAMPLES) {
        imuMoved = false;
        status.cleared_now = true;
      }
    }
  }

  status.moved = imuMoved || imuLatched;
  return status;
}

AlarmLevel currentAlarmLevel() {
  if (imuMoved || imuLatched) {
    return ALARM_IMU;
  }
  if (irDetected) {
    return ALARM_IR;
  }
  return ALARM_SAFE;
}

bool shouldPublish(AlarmLevel level) {
  return level != lastReportedLevel ||
         irDetected != lastReportedIr ||
         (imuMoved || imuLatched) != lastReportedImu;
}

void publishAlarmState(const char *message, bool force = false) {
  if (!mqttClient.connected()) {
    reconnectMqtt();
  }
  mqttClient.loop();

  AlarmLevel level = currentAlarmLevel();
  if (!force && !shouldPublish(level)) {
    return;
  }

  StaticJsonDocument<384> doc;
  JsonArray services = doc.createNestedArray("services");
  JsonObject service = services.createNestedObject();
  service["service_id"] = SERVICE_ID;
  JsonObject properties = service.createNestedObject("properties");
  properties["alarm_level"] = static_cast<int>(level);
  properties["ir_status"] = irDetected ? 1 : 0;
  properties["vision_status"] = 0;
  properties["imu_status"] = (imuMoved || imuLatched) ? 1 : 0;
  properties["message"] = message;
  String eventTime = isoEventTime();
  if (eventTime.length() > 0) {
    service["event_time"] = eventTime;
  }

  char payload[384];
  serializeJson(doc, payload, sizeof(payload));
  String topic = mqttTopic();

  bool ok = mqttClient.publish(topic.c_str(), payload, true);
  Serial.print("Publish ");
  Serial.print(ok ? "OK" : "FAILED");
  Serial.print(": ");
  Serial.println(payload);

  if (ok) {
    lastReportedLevel = level;
    lastReportedIr = irDetected;
    lastReportedImu = imuMoved || imuLatched;
  }
}

void handleSerialCommands() {
  if (!Serial.available()) {
    return;
  }
  char command = Serial.read();
  if (command == 'r' || command == 'R') {
    irDetected = false;
    imuMoved = false;
    imuLatched = false;
    irTriggerCount = 0;
    irClearCount = 0;
    mpuTriggerCount = 0;
    mpuClearCount = 0;
    publishAlarmState("manual serial reset", true);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(TCRT_DO_PIN, INPUT_PULLUP);
  setupMpu6050();
  setupWifi();
  setupTimeForHuaweiAuth();

  if (MQTT_USE_TLS) {
    secureClient.setInsecure();  // Prototype only. Use Huawei root CA in production.
    mqttClient.setClient(secureClient);
  } else {
    mqttClient.setClient(plainClient);
  }
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setBufferSize(512);
  reconnectMqtt();
  publishAlarmState("esp32-s3 sensor node startup", true);
}

void loop() {
  handleSerialCommands();
  if (!mqttClient.connected()) {
    reconnectMqtt();
  }
  mqttClient.loop();

  bool irTriggeredNow = updateIrDetector();
  MPUReading reading;
  bool mpuOk = readMpu(reading);
  MPUStatus mpuStatus;
  bool mpuTriggeredNow = false;
  if (mpuOk) {
    mpuStatus = updateMpuDetector(reading);
    mpuTriggeredNow = mpuStatus.triggered_now;
  }

  if (mpuTriggeredNow) {
    publishAlarmState("MPU6050 movement detected");
  } else if (irTriggeredNow) {
    publishAlarmState("TCRT5000 proximity detected");
  } else {
    publishAlarmState("sensor state changed");
  }

  delay(100);
}
