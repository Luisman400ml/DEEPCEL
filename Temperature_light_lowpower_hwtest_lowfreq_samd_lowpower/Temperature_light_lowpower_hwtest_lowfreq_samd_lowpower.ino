#include "FPGA.h"
#include "DHT20.h"
#include <ArduinoLowPower.h>

const unsigned long SAMPLE_INTERVAL_MS = 10000;
const unsigned long LOW_POWER_IDLE_CHUNK_MS = 250;
const uint8_t LIGHT_SENSOR_PIN = A2;
const char BUILD_DESCRIPTION[] = "Build: Quartus 25.1 lowpower light Q4.4 burst + 6 MHz NN clock + SAMD21 idle low power, DHT20 humidity, Grove Light Sensor on A2";

const float TEMP_MIN = 24.612081304273765f;
const float TEMP_MAX = 37.95430094132428f;
const float LIGHT_MIN = 163.7478016239505f;
const float LIGHT_MAX = 1027.5785826547694f;

bool csvOutput = false;
DHT20 sensor1;

float temperatureHistory[4] = {0, 0, 0, 0};
float lightHistory[4] = {0, 0, 0, 0};

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

static void handleSerialCommands() {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'C':
        csvOutput = true;
        Serial.println("record,time_ms,temperature_history_c,humidity_rh_pct,light_history_adc,prediction_temperature_c,prediction_light_model,temperature_q4_4,light_q4_4,prediction_temperature_q4_4,prediction_light_q4_4");
        break;
      case 'P':
        csvOutput = false;
        break;
      case 'T':
        Serial.println(BUILD_DESCRIPTION);
        runFpgaSelfTest();
        break;
    }
  }
}

static void idleUntilNextSample(unsigned long nowMs, unsigned long lastSampleStartedMs, unsigned long sampleIntervalMs) {
  if (sampleIntervalMs == 0) {
    return;
  }

  unsigned long elapsedMs = nowMs - lastSampleStartedMs;
  if (elapsedMs >= sampleIntervalMs) {
    return;
  }

  unsigned long idleMs = sampleIntervalMs - elapsedMs;
  if (idleMs > LOW_POWER_IDLE_CHUNK_MS) {
    idleMs = LOW_POWER_IDLE_CHUNK_MS;
  }

  Serial.flush();
  LowPower.idle(idleMs);
}

void setup() {
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  analogReadResolution(10);

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

  Wire.begin();
  if (!sensor1.begin()) {
    Serial.println("ERROR: DHT20 not found on I2C address 0x38.");
  }
}

void loop() {
  handleSerialCommands();

  static unsigned long lastSampleStartedMs = 0;
  static unsigned long sampleIntervalMs = 0;
  const unsigned long sampleStartedMs = millis();
  if (sampleStartedMs - lastSampleStartedMs < sampleIntervalMs) {
    idleUntilNextSample(sampleStartedMs, lastSampleStartedMs, sampleIntervalMs);
    return;
  }
  lastSampleStartedMs = sampleStartedMs;
  sampleIntervalMs = SAMPLE_INTERVAL_MS;

  int status = sensor1.read();
  if (status != DHT20_OK) {
    Serial.print("DHT20 read error: ");
    Serial.print(status);
    Serial.print(" (");
    Serial.print(dht20StatusMessage(status));
    Serial.println(")");
    sampleIntervalMs = 2000;
    return;
  }

  float temperature = sensor1.getTemperature();
  float humidity = sensor1.getHumidity();
  int lightAdc = analogRead(LIGHT_SENSOR_PIN);
  float lightValue = float(lightAdc);

  pushHistory(temperatureHistory, temperature);
  pushHistory(lightHistory, lightValue);

  uint8_t temperatureQ4_4 = toQ4_4(temperature, TEMP_MIN, TEMP_MAX);
  uint8_t lightQ4_4 = toQ4_4(lightValue, LIGHT_MIN, LIGHT_MAX);

  writeFpgaSamplePair(temperatureQ4_4, lightQ4_4, 10);

  uint8_t predictionTempQ4_4 = uint8_t(FPGA.read(0) & 0xFF);
  uint8_t predictionLightQ4_4 = uint8_t(FPGA.read(1) & 0xFF);
  float predictionTemp = fromQ4_4(predictionTempQ4_4, TEMP_MIN, TEMP_MAX);
  float predictionLight = fromQ4_4(predictionLightQ4_4, LIGHT_MIN, LIGHT_MAX);

  if (csvOutput) {
    Serial.print("DATA,");
    Serial.print(sampleStartedMs);
    Serial.print(',');
    printCsvHistoryArray(temperatureHistory, 4);
    Serial.print(',');
    Serial.print(humidity, 4);
    Serial.print(',');
    printCsvHistoryArray(lightHistory, 0);
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
    Serial.println(predictionLightQ4_4);
  } else {
    printHistoryArray("TemperatureHistory_C", temperatureHistory, 2);
    Serial.println();
    printHistoryArray("LightHistory_ADC", lightHistory, 0);
    Serial.println();
    Serial.print("Temperature_C:");
    Serial.print(temperature, 2);
    Serial.println();
    Serial.print("Light_ADC:");
    Serial.print(lightValue, 0);
    Serial.println();
    Serial.print("PredictionTemperature_C:");
    Serial.print(predictionTemp, 2);
    Serial.println();
    Serial.print("PredictionLight_model:");
    Serial.print(predictionLight, 0);
    Serial.println();
    Serial.print("Humidity_pct:");
    Serial.println(humidity, 2);
    Serial.println();
  }
}
