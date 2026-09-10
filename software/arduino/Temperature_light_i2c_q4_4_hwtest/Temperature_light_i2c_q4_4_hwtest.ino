#include "FPGA.h"
#include "DHT20.h"
#include <Wire.h>
#include <math.h>

const unsigned long SAMPLE_INTERVAL_MS = 10000;
const unsigned long WAIT_CHUNK_MS = 250;
const unsigned long DHT_RETRY_DELAY_MS = 90;
const uint8_t DHT_READ_ATTEMPTS = 3;
const char BUILD_DESCRIPTION[] =
    "Build: Quartus 25.1 ultralowpower light Q4.4 sequential MAC + 1 MHz NN clock + stable SAMD delay wait, DHT20 humidity, I2C light sensor";

const float TEMP_MIN = 24.612081304273765f;
const float TEMP_MAX = 37.95430094132428f;
const float TEMP_FALLBACK_VALUE = (TEMP_MIN + TEMP_MAX) * 0.5f;
const float LIGHT_MIN = 163.7478016239505f;
const float LIGHT_MAX = 1027.5785826547694f;
const float LIGHT_FALLBACK_VALUE = (LIGHT_MIN + LIGHT_MAX) * 0.5f;

bool csvOutput = false;
DHT20 sensor1;
uint8_t consecutiveDhtErrors = 0;
uint16_t dhtErrorCount = 0;
bool dhtHasValidSample = false;
float lastTemperature = TEMP_FALLBACK_VALUE;
float lastHumidity = 0.0f;

float temperatureHistory[4] = {0, 0, 0, 0};
float lightHistory[4] = {0, 0, 0, 0};

enum LightSensorKind : uint8_t {
  LIGHT_SENSOR_NONE = 0,
  LIGHT_SENSOR_TSL2561,
  LIGHT_SENSOR_BH1750,
  LIGHT_SENSOR_VEML7700,
  LIGHT_SENSOR_SI114X
};

struct LightSensorState {
  LightSensorKind kind = LIGHT_SENSOR_NONE;
  uint8_t address = 0;
  float lastValue = LIGHT_FALLBACK_VALUE;
  uint16_t failures = 0;
};

LightSensorState lightSensor;

const char* lightSensorName(LightSensorKind kind) {
  switch (kind) {
    case LIGHT_SENSOR_TSL2561:
      return "TSL2561";
    case LIGHT_SENSOR_BH1750:
      return "BH1750";
    case LIGHT_SENSOR_VEML7700:
      return "VEML7700";
    case LIGHT_SENSOR_SI114X:
      return "SI114x";
    default:
      return "none";
  }
}

const char* dht20StatusMessage(int status) {
  switch (status) {
    case DHT20_OK:
      return "OK";
    case DHT20_ERROR_CHECKSUM:
      return "checksum error";
    case DHT20_ERROR_CONNECT:
      return "connection error";
    case DHT20_MISSING_BYTES:
      return "missing bytes";
    case DHT20_ERROR_BYTES_ALL_ZERO:
      return "all bytes zero";
    case DHT20_ERROR_READ_TIMEOUT:
      return "read timeout";
    case DHT20_ERROR_LASTREAD:
      return "read too soon";
    default:
      return "unknown error";
  }
}

static bool i2cPing(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

static bool i2cWrite8(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

static bool i2cWrite16LE(uint8_t address, uint8_t reg, uint16_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(uint8_t(value & 0xFF));
  Wire.write(uint8_t(value >> 8));
  return Wire.endTransmission() == 0;
}

static bool i2cCommand(uint8_t address, uint8_t command) {
  Wire.beginTransmission(address);
  Wire.write(command);
  return Wire.endTransmission() == 0;
}

static bool i2cRead8(uint8_t address, uint8_t reg, uint8_t& value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  if (Wire.requestFrom(address, uint8_t(1)) != 1) {
    return false;
  }
  value = Wire.read();
  return true;
}

static bool i2cRead16LE(uint8_t address, uint8_t reg, uint16_t& value) {
  uint8_t low = 0;
  uint8_t high = 0;
  if (!i2cRead8(address, reg, low) || !i2cRead8(address, reg + 1, high)) {
    return false;
  }
  value = uint16_t(low) | (uint16_t(high) << 8);
  return true;
}

static bool i2cRead16BE(uint8_t address, uint16_t& value) {
  if (Wire.requestFrom(address, uint8_t(2)) != 2) {
    return false;
  }
  value = (uint16_t(Wire.read()) << 8) | Wire.read();
  return true;
}

static bool initTsl2561(uint8_t address) {
  if (!i2cPing(address)) {
    return false;
  }
  if (!i2cWrite8(address, 0x80, 0x03)) {
    return false;
  }
  delay(20);
  if (!i2cWrite8(address, 0x81, 0x02)) {
    return false;
  }
  uint8_t id = 0;
  return i2cRead8(address, 0x8A, id);
}

static bool initBh1750(uint8_t address) {
  if (!i2cPing(address)) {
    return false;
  }
  return i2cCommand(address, 0x01) && i2cCommand(address, 0x07) && i2cCommand(address, 0x10);
}

static bool initVeml7700(uint8_t address) {
  if (!i2cPing(address)) {
    return false;
  }
  return i2cWrite16LE(address, 0x00, 0x0000);
}

static bool writeSi114xParam(uint8_t address, uint8_t parameter, uint8_t value) {
  if (!i2cWrite8(address, 0x17, value)) {
    return false;
  }
  if (!i2cWrite8(address, 0x18, uint8_t(parameter | 0xA0))) {
    return false;
  }
  delay(2);
  uint8_t readback = 0;
  return i2cRead8(address, 0x2E, readback);
}

static bool initSi114x(uint8_t address) {
  if (!i2cPing(address)) {
    return false;
  }

  uint8_t partId = 0;
  if (!i2cRead8(address, 0x00, partId) || partId != 0x45) {
    return false;
  }

  i2cWrite8(address, 0x08, 0x00);
  i2cWrite8(address, 0x09, 0x00);
  i2cWrite8(address, 0x04, 0x00);
  i2cWrite8(address, 0x05, 0x00);
  i2cWrite8(address, 0x06, 0x00);
  i2cWrite8(address, 0x03, 0x00);
  i2cWrite8(address, 0x21, 0xFF);
  if (!i2cWrite8(address, 0x18, 0x01)) {
    return false;
  }
  delay(100);
  if (!i2cWrite8(address, 0x07, 0x17)) {
    return false;
  }
  delay(10);

  if (!writeSi114xParam(address, 0x01, 0x10)) {
    return false;
  }
  if (!writeSi114xParam(address, 0x10, 0x07)) {
    return false;
  }
  if (!writeSi114xParam(address, 0x11, 0x00)) {
    return false;
  }
  if (!writeSi114xParam(address, 0x12, 0x20)) {
    return false;
  }

  return true;
}

static bool readTsl2561(float& lightValue) {
  uint16_t ch0 = 0;
  uint16_t ch1 = 0;
  if (!i2cRead16LE(lightSensor.address, 0x8C, ch0) || !i2cRead16LE(lightSensor.address, 0x8E, ch1)) {
    return false;
  }
  if (ch0 == 0) {
    lightValue = 0.0f;
    return true;
  }

  float ratio = float(ch1) / float(ch0);
  float lux = 0.0f;
  if (ratio <= 0.5f) {
    lux = 0.0304f * ch0 - 0.062f * ch0 * pow(ratio, 1.4f);
  } else if (ratio <= 0.61f) {
    lux = 0.0224f * ch0 - 0.031f * ch1;
  } else if (ratio <= 0.80f) {
    lux = 0.0128f * ch0 - 0.0153f * ch1;
  } else if (ratio <= 1.30f) {
    lux = 0.00146f * ch0 - 0.00112f * ch1;
  }
  lightValue = lux > 0.0f ? lux : 0.0f;
  return true;
}

static bool readBh1750(float& lightValue) {
  uint16_t raw = 0;
  if (!i2cRead16BE(lightSensor.address, raw)) {
    initBh1750(lightSensor.address);
    return false;
  }
  lightValue = float(raw) / 1.2f;
  return true;
}

static bool readVeml7700(float& lightValue) {
  uint16_t raw = 0;
  if (!i2cRead16LE(lightSensor.address, 0x04, raw)) {
    return false;
  }
  lightValue = float(raw) * 0.0576f;
  return true;
}

static bool readSi114x(float& lightValue) {
  if (!i2cWrite8(lightSensor.address, 0x18, 0x06)) {
    return false;
  }
  delay(30);

  uint16_t raw = 0;
  if (!i2cRead16LE(lightSensor.address, 0x22, raw)) {
    return false;
  }
  lightValue = float(raw);
  return true;
}

static bool detectLightSensor() {
  const uint8_t tslAddresses[] = {0x29, 0x39, 0x49};
  for (unsigned index = 0; index < sizeof(tslAddresses); ++index) {
    if (initTsl2561(tslAddresses[index])) {
      lightSensor.kind = LIGHT_SENSOR_TSL2561;
      lightSensor.address = tslAddresses[index];
      return true;
    }
  }

  const uint8_t bhAddresses[] = {0x23, 0x5C};
  for (unsigned index = 0; index < sizeof(bhAddresses); ++index) {
    if (initBh1750(bhAddresses[index])) {
      lightSensor.kind = LIGHT_SENSOR_BH1750;
      lightSensor.address = bhAddresses[index];
      delay(180);
      return true;
    }
  }

  if (initVeml7700(0x10)) {
    lightSensor.kind = LIGHT_SENSOR_VEML7700;
    lightSensor.address = 0x10;
    delay(120);
    return true;
  }

  if (initSi114x(0x60)) {
    lightSensor.kind = LIGHT_SENSOR_SI114X;
    lightSensor.address = 0x60;
    delay(30);
    return true;
  }

  lightSensor.kind = LIGHT_SENSOR_NONE;
  lightSensor.address = 0;
  return false;
}

static bool readLightSensor(float& lightValue) {
  bool ok = false;
  switch (lightSensor.kind) {
    case LIGHT_SENSOR_TSL2561:
      ok = readTsl2561(lightValue);
      break;
    case LIGHT_SENSOR_BH1750:
      ok = readBh1750(lightValue);
      break;
    case LIGHT_SENSOR_VEML7700:
      ok = readVeml7700(lightValue);
      break;
    case LIGHT_SENSOR_SI114X:
      ok = readSi114x(lightValue);
      break;
    default:
      ok = false;
      break;
  }

  if (ok) {
    lightSensor.lastValue = lightValue;
    lightSensor.failures = 0;
    return true;
  }

  lightSensor.failures++;
  lightValue = lightSensor.lastValue;
  return false;
}

#include "fpga_selftest.h"

static uint8_t toQ4_4(float value, float minimum, float maximum) {
  if (maximum <= minimum) {
    return 0;
  }
  float normalized = (value - minimum) / (maximum - minimum);
  if (normalized < 0.0f) {
    normalized = 0.0f;
  } else if (normalized > 1.0f) {
    normalized = 1.0f;
  }
  int q = int(normalized * 16.0f + 0.5f);
  if (q < 0) {
    q = 0;
  } else if (q > 16) {
    q = 16;
  }
  return uint8_t(q);
}

static float fromQ4_4(uint8_t value, float minimum, float maximum) {
  return (float(value) / 16.0f) * (maximum - minimum) + minimum;
}

static void pushHistory(float history[4], float value) {
  history[0] = history[1];
  history[1] = history[2];
  history[2] = history[3];
  history[3] = value;
}

static void printHistoryArray(const char* label, const float history[4], int decimals) {
  Serial.print(label);
  Serial.print(":[");
  for (unsigned index = 0; index < 4; ++index) {
    if (index > 0) {
      Serial.print(',');
    }
    Serial.print(history[index], decimals);
  }
  Serial.print(']');
}

static void printCsvHistoryArray(const float history[4], int decimals) {
  Serial.print("\"[");
  for (unsigned index = 0; index < 4; ++index) {
    if (index > 0) {
      Serial.print(',');
    }
    Serial.print(history[index], decimals);
  }
  Serial.print("]\"");
}

static void printI2cScan() {
  Serial.println("I2C scan:");
  for (uint8_t address = 1; address < 127; address++) {
    if (i2cPing(address)) {
      Serial.print("0x");
      if (address < 16) {
        Serial.print('0');
      }
      Serial.println(address, HEX);
    }
  }
}

static void startI2cBus() {
  Wire.begin();
  Wire.setClock(100000);
  Wire.setTimeout(50);
}

static void recoverDht20Bus();

static bool readDht20Stable(float& temperature, float& humidity, const char*& dhtStatus, int& dhtLastStatus) {
  int status = DHT20_OK;

  for (uint8_t attempt = 0; attempt < DHT_READ_ATTEMPTS; ++attempt) {
    status = sensor1.read();
    if (status == DHT20_OK) {
      temperature = sensor1.getTemperature();
      humidity = sensor1.getHumidity();
      lastTemperature = temperature;
      lastHumidity = humidity;
      dhtHasValidSample = true;
      consecutiveDhtErrors = 0;
      dhtLastStatus = status;
      dhtStatus = "OK";
      return true;
    }
    if (attempt + 1 < DHT_READ_ATTEMPTS) {
      delay(DHT_RETRY_DELAY_MS);
    }
  }

  dhtErrorCount++;
  consecutiveDhtErrors++;
  if (status != DHT20_ERROR_LASTREAD) {
    recoverDht20Bus();
    consecutiveDhtErrors = 0;
    dhtStatus = dhtHasValidSample ? "RECOVERED_STALE" : "RECOVERING";
  } else {
    dhtStatus = dhtHasValidSample ? "STALE" : "NO_SENSOR";
  }

  temperature = lastTemperature;
  humidity = lastHumidity;
  dhtLastStatus = status;
  return false;
}

static void handleSerialCommands() {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'C':
        csvOutput = true;
        Serial.println("record,time_ms,temperature_history_c,humidity_rh_pct,dht_status,dht_error_count,dht_last_status,light_history_value,prediction_temperature_c,prediction_light_model,temperature_q4_4,light_q4_4,prediction_temperature_q4_4,prediction_light_q4_4,light_status,light_sensor");
        break;
      case 'P':
        csvOutput = false;
        break;
      case 'T':
        Serial.println(BUILD_DESCRIPTION);
        runFpgaSelfTest();
        break;
      case 'I':
        printI2cScan();
        break;
    }
  }
}

static void waitUntilNextSample(unsigned long nowMs, unsigned long lastSampleStartedMs, unsigned long sampleIntervalMs) {
  if (sampleIntervalMs == 0) {
    return;
  }

  unsigned long elapsedMs = nowMs - lastSampleStartedMs;
  if (elapsedMs >= sampleIntervalMs) {
    return;
  }

  unsigned long waitMs = sampleIntervalMs - elapsedMs;
  if (waitMs > WAIT_CHUNK_MS) {
    waitMs = WAIT_CHUNK_MS;
  }

  Serial.flush();
  delay(waitMs);
}

static void recoverDht20Bus() {
  Wire.end();
  delay(50);
  startI2cBus();
  sensor1.begin();
}

void setup() {
  Serial.begin(9600);
  while (!Serial)
    ;

  if (!FPGA.begin(32, 4)) {
    Serial.println("ERROR: Unable to configure the FPGA.");
    Serial.println(FPGA.getErrorMessage());
    while (1)
      ;
  }
  Serial.println("FPGA successfully configured!");
  Serial.println(BUILD_DESCRIPTION);

  if (!runFpgaSelfTest(false)) {
    while (1)
      ;
  }

  startI2cBus();
  if (!sensor1.begin()) {
    Serial.println("WARN: DHT20 not found on I2C address 0x38.");
  } else {
    Serial.println("DHT20 sensor detected.");
  }
  delay(100);
  if (detectLightSensor()) {
    Serial.print("I2C light sensor detected: ");
    Serial.print(lightSensorName(lightSensor.kind));
    Serial.print(" at 0x");
    if (lightSensor.address < 16) {
      Serial.print('0');
    }
    Serial.println(lightSensor.address, HEX);
  } else {
    Serial.println("WARN: No supported I2C light sensor detected. Prediction uses fallback/last value.");
  }
}

void loop() {
  handleSerialCommands();

  static unsigned long lastSampleStartedMs = 0;
  static unsigned long sampleIntervalMs = 0;
  const unsigned long sampleStartedMs = millis();
  if (sampleStartedMs - lastSampleStartedMs < sampleIntervalMs) {
    waitUntilNextSample(sampleStartedMs, lastSampleStartedMs, sampleIntervalMs);
    return;
  }
  lastSampleStartedMs = sampleStartedMs;
  sampleIntervalMs = SAMPLE_INTERVAL_MS;

  float temperature = TEMP_FALLBACK_VALUE;
  float humidity = 0.0f;
  const char* dhtStatus = "NO_SENSOR";
  int dhtLastStatus = DHT20_OK;
  readDht20Stable(temperature, humidity, dhtStatus, dhtLastStatus);
  float lightValue = LIGHT_FALLBACK_VALUE;
  bool lightOk = readLightSensor(lightValue);

  pushHistory(temperatureHistory, temperature);
  pushHistory(lightHistory, lightValue);

  uint8_t temperatureQ4_4 = toQ4_4(temperature, TEMP_MIN, TEMP_MAX);
  uint8_t lightQ4_4 = toQ4_4(lightValue, LIGHT_MIN, LIGHT_MAX);

  writeFpgaSamplePair(temperatureQ4_4, lightQ4_4, 10);

  uint8_t predictionTempQ4_4 = uint8_t(FPGA.read(0) & 0xFF);
  uint8_t predictionLightQ4_4 = uint8_t(FPGA.read(1) & 0xFF);
  float predictionTemp = fromQ4_4(predictionTempQ4_4, TEMP_MIN, TEMP_MAX);
  float predictionLight = fromQ4_4(predictionLightQ4_4, LIGHT_MIN, LIGHT_MAX);
  const char* lightStatus = lightOk ? "OK" : (lightSensor.kind == LIGHT_SENSOR_NONE ? "NO_SENSOR" : "STALE");

  if (csvOutput) {
    Serial.print("DATA,");
    Serial.print(sampleStartedMs);
    Serial.print(',');
    printCsvHistoryArray(temperatureHistory, 4);
    Serial.print(',');
    Serial.print(humidity, 4);
    Serial.print(',');
    Serial.print(dhtStatus);
    Serial.print(',');
    Serial.print(dhtErrorCount);
    Serial.print(',');
    Serial.print(dhtLastStatus);
    Serial.print(',');
    printCsvHistoryArray(lightHistory, 2);
    Serial.print(',');
    Serial.print(predictionTemp, 4);
    Serial.print(',');
    Serial.print(predictionLight, 4);
    Serial.print(',');
    Serial.print(temperatureQ4_4);
    Serial.print(',');
    Serial.print(lightQ4_4);
    Serial.print(',');
    Serial.print(predictionTempQ4_4);
    Serial.print(',');
    Serial.print(predictionLightQ4_4);
    Serial.print(',');
    Serial.print(lightStatus);
    Serial.print(',');
    Serial.println(lightSensorName(lightSensor.kind));
  } else {
    printHistoryArray("TemperatureHistory_C", temperatureHistory, 2);
    Serial.println();
    printHistoryArray("LightHistory_value", lightHistory, 2);
    Serial.println();
    Serial.print("Temperature_C:");
    Serial.print(temperature, 2);
    Serial.println();
    Serial.print("Light_value:");
    Serial.print(lightValue, 2);
    Serial.println();
    Serial.print("PredictionTemperature_C:");
    Serial.print(predictionTemp, 2);
    Serial.println();
    Serial.print("PredictionLight_model:");
    Serial.print(predictionLight, 2);
    Serial.println();
    Serial.print("LightStatus:");
    Serial.print(lightStatus);
    Serial.print(" sensor=");
    Serial.println(lightSensorName(lightSensor.kind));
    Serial.print("DHTStatus:");
    Serial.print(dhtStatus);
    Serial.print(" code=");
    Serial.print(dhtLastStatus);
    Serial.print(" errors=");
    Serial.println(dhtErrorCount);
    Serial.print("Humidity_pct:");
    Serial.println(humidity, 2);
    Serial.println();
  }
}
