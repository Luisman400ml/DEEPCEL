#include "FPGA.h"
#include "DHT20.h"
#include <ArduinoLowPower.h>

#define win_size 7
#define measure_period_s 10
#define range_percentage 100
bool fpga_used;

#define TEMP_MIN -5.0f
#define TEMP_MAX 40.0f
const float temp_spread = (TEMP_MAX - TEMP_MIN) * range_percentage / 100.0f;
float prediction_temp;

#define LIGHT_MIN 163.7478016239505
#define LIGHT_MAX 1027.5785826547694
const float light_spread = (LIGHT_MAX - LIGHT_MIN) * range_percentage / 100.0f;
float prediction_light;

#define HUM_MIN 40.0f
#define HUM_MAX 100.0f
const float hum_spread = (HUM_MAX - HUM_MIN) * range_percentage / 100.0f;
float prediction_hum;

float temp_win[win_size] = {};
float light_win[win_size] = {};
float hum_win[win_size] = {};
float press_win[win_size] = {};

DHT20 Temp_Hum_Sensor;

void printwin(float temp_win[win_size]) {
  Serial.print("[ ");
  for (int i = 0; i < win_size; i++) {
    Serial.print(temp_win[i]);
    Serial.print(" ");
  }
  Serial.print("]");
}

bool windowWithinRange(float window[], float spread)
{
  float win_min = window[0];
  float win_max = window[0];

  for (int i = 1; i < win_size; i++) {
    if (window[i] < win_min)
      win_min = window[i];
    if (window[i] > win_max)
      win_max = window[i];
  }

  return (win_max - win_min) <= spread;
}

float mean(float window[], int size)
{
    float sum = 0.0f;
    for (int i = 0; i < size; i++)
        sum += window[i];
    return sum / size;
}

void setup() {
  pinMode(A2, INPUT);
  Serial.begin(9600);
  while (!Serial);

  if (!FPGA.begin(16, 4)) {
    Serial.println("ERROR : Impossible configuration of FPGA.");
    Serial.println(FPGA.getErrorMessage());
    while (1);
  }

  Serial.println("FPGA configured sucessfull !");

  Wire.begin();
  Temp_Hum_Sensor.begin();
}

void loop() {

  unsigned long start = millis();

  int status = Temp_Hum_Sensor.read();

  //TEMPERATURE AND HUMIDITY SENSOR
  if (status == DHT20_OK) {

    //TEMPERATURE
    float temperature = Temp_Hum_Sensor.getTemperature();

    for (int i = 0; i < win_size - 1; i++) {
      temp_win[i] = temp_win[i + 1];
    }
    temp_win[win_size - 1] = temperature;

    //float Normalise_Temp = (temperature - TEMP_MIN) / (TEMP_MAX - TEMP_MIN);

    //uint16_t sending_temperature = (uint16_t)(Normalise_Temp * 256);

    // FPGA.write(0, sending_temperature);
    // FPGA.write(2, 1);
    // delayMicroseconds(1);
    // FPGA.write(2, 0);
    // delayMicroseconds(1);
    //HUMIDITY
    float humidity = Temp_Hum_Sensor.getHumidity();

    for (int i = 0; i < win_size - 1; i++) {
      hum_win[i] = hum_win[i + 1];
    }
    hum_win[win_size - 1] = humidity;

    //float Normalise_Hum = (humidity - HUM_MIN) / (HUM_MAX - HUM_MIN);

    //uint16_t sending_humidity = (uint16_t)(Normalise_Hum * 256);

    //FPGA.write(1, sending_humidity);
    // FPGA.write(3, 1);
    // delayMicroseconds(1);
    // FPGA.write(3, 0);
    // delayMicroseconds(1);
  }

  //LIGHT SENSOR
  // float light = analogRead(A2);

  // for (int i = 0; i < win_size - 1; i++) {
  //   light_win[i] = light_win[i + 1];
  // }

  // light_win[win_size - 1] = light;

  // float Normalise_light =
  //   (light - LIGHT_MIN) / (LIGHT_MAX - LIGHT_MIN);

  // uint16_t sending_light =
  //   (uint16_t)(Normalise_light * 256);

  // FPGA.write(1, sending_light);

  // FPGA.write(3, 1);
  // delayMicroseconds(1);
  // FPGA.write(3, 0);
  // delayMicroseconds(1);

  //deciding whether to use the neural network or not
  //if all the measurements in the window fall within a certain relative range, then the fpga is not used and the prediction is evaluated in the microprocessor
  if (windowWithinRange(temp_win, temp_spread) && windowWithinRange(hum_win, hum_spread)) {
    fpga_used = false;
    prediction_temp = mean(temp_win, win_size);
    prediction_hum  = mean(hum_win,  win_size);
  } else {//need to evaluate the prediction with the neural network
    fpga_used = true;

  // uint16_t prediction_temp = FPGA.read(1);
  // uint16_t prediction_Light = FPGA.read(2);

  // float prediction__temp_float = prediction_temp / 256.0;
  // float reel_predtiction_temp = prediction__temp_float * (TEMP_MAX - TEMP_MIN) + TEMP_MIN;

  // float prediction_light_float = prediction_Light / 256.0;
  // float reel_predtiction_light = prediction_light_float * (LIGHT_MAX - LIGHT_MIN) + LIGHT_MIN;

  delay(10);// waiting for the fpga to finish
  }


  unsigned long exe_time = millis() - start;

  Serial.println("\n\n## ITERATION COMPLETE ##");

  Serial.print("Temp window: ");
  printwin(temp_win);
  Serial.print(" => prediction: ");
  Serial.println(prediction_temp);

  Serial.print("Hum window:  ");
  printwin(light_win);
  Serial.print(" => prediction: ");
  Serial.println(prediction_hum);

  Serial.print("FPGA used: ");
  Serial.println(fpga_used);

  Serial.print("Prediction was ready in: ");
  Serial.print(exe_time / 1000.0);
  Serial.println(" s");

  unsigned long period_ms = measure_period_s * 1000UL;

  if (exe_time < period_ms) {

    unsigned long wait_time = period_ms - exe_time;

    Serial.print("Sleeping for ");
    Serial.print(wait_time / 1000.0);
    Serial.println(" s");

    LowPower.sleep(wait_time / 1000);
    delay(wait_time % 1000);
  }
  else {
    Serial.println("No waiting: execution time exceeded measurement period.");
  }
}
