#include "FPGA.h"   // This is the library specific to the Arduino MKR Vidor 4000. It allows the microcontroller (the SAMD21) to communicate directly with the FPGA integrated on the board using a JTAG connection.
#include "DHT20.h"  //  This is the library that manages the DHT20 temperature and humidity sensor. It simplifies I2C communication with the sensor to retrieve clean data.
#include <Wire.h>

const unsigned long SAMPLE_INTERVAL_MS = 10000;
const uint8_t LIGHT_SENSOR_PIN = A2;
bool csvOutput = false;


DHT20 sensor1;  // Creation of the object representing the DHT sensor

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

void recoverDht20Bus() {
  Wire.end();
  delay(20);
  Wire.begin();
  sensor1.begin();
}

#include "fpga_selftest.h"

void setup() {
  Serial.begin(9600);
  while (!Serial)
    ;

  analogReadResolution(10);
  pinMode(LIGHT_SENSOR_PIN, INPUT);

  // FPGA INITIALIZATION
  // Configures the FPGA (JTAG communication parameters: register size and number of registers used)
  if (!FPGA.begin(32, 2)) {
    Serial.println("ERROR: Unable to configure the FPGA.");
    Serial.println(FPGA.getErrorMessage());
    while (1)
      ;
  }
  Serial.println("FPGA successfully configured!");
  if (!runFpgaSelfTest(false)) {
    while (1)
      ;
  }

  Wire.begin();
  if (!sensor1.begin()) {  // Initializes the sensor on the I2C bus.
    Serial.println("ERROR: DHT20 not found on I2C address 0x38.");
  }
}

void loop() {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'C':
        csvOutput = true;
        Serial.println("record,time_ms,temperature_c,humidity_rh_pct,light_adc,prediction_temperature_c");
        break;
      case 'P':
        csvOutput = false;
        break;
      case 'T':
        Serial.println("Build: Quartus 25.1 lowpower, DHT20 + Grove Light Sensor on A2 plotter/CSV");
        runFpgaSelfTest();
        break;
    }
  }

  // Poll commands between measurements without changing the sampling cadence.
  static unsigned long lastSampleStartedMs = 0;
  static unsigned long sampleIntervalMs = 0;
  const unsigned long sampleStartedMs = millis();
  if (sampleStartedMs - lastSampleStartedMs < sampleIntervalMs) {
    delay(1);
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
    if (status != DHT20_ERROR_LASTREAD) {
      recoverDht20Bus();
    }
    sampleIntervalMs = 2000;
    return;
  }

  // Both values belong to the same I2C measurement.
  float temperature = sensor1.getTemperature();
  float humidity = sensor1.getHumidity();
  int lightAdc = analogRead(LIGHT_SENSOR_PIN);
  uint16_t temperatureQ8_8 = (uint16_t)(256 * temperature);

  FPGA.write(0, temperatureQ8_8);
  FPGA.write(1, 1);
  delayMicroseconds(1);
  FPGA.write(1, 0);
  delay(10);

  uint16_t prediction = FPGA.read(0);
  float predictionC = prediction / 256.0f;

  if (csvOutput) {
    Serial.print("DATA,");
    Serial.print(sampleStartedMs);
    Serial.print(',');
    Serial.print(temperature, 4);
    Serial.print(',');
    Serial.print(humidity, 4);
    Serial.print(',');
    Serial.print(lightAdc);
    Serial.print(',');
    Serial.println(predictionC, 4);
  } else {
    Serial.print("Temperature_C:");
    Serial.print(temperature, 2);
    Serial.print("\tPredictionTemperature_C:");
    Serial.print(predictionC, 2);
    Serial.print("\tHumidity_pct:");
    Serial.print(humidity, 2);
    Serial.print("\tLight_ADC:");
    Serial.println(lightAdc);
  }
}
