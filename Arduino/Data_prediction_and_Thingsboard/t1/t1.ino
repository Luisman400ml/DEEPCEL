#include "FPGA.h"
#include "DHT20.h"

#define win_size 4
#define measure_period_s 5

#define TEMP_MIN  24.612081304273765
#define TEMP_MAX  37.95430094132428

#define LIGHT_MIN 163.7478016239505
#define LIGHT_MAX 1027.5785826547694

float temp_win[win_size]={}; // to fill with zeros 
float light_win[win_size]={}; // to fill with zeros 
float hum_win[win_size]={}; // to fill with zeros 
float press_win[win_size]={}; // to fill with zeros 

// to FPGA write
// 0 => wake up signal

DHT20 Temperature_Sensor;

void printwin (float temp_win[win_size]) {
  for (int i = 0; i < win_size; i++) {
    Serial.print(temp_win[i]);
    Serial.print(" ");
  }
}

void setup() {
  pinMode(A2,INPUT);
  Serial.begin(9600);
  while(!Serial);

  //   FPGA INITIALISATION 
  
  if (!FPGA.begin(16,4)) {
    Serial.println("ERROR : Impossible configuration of FPGA.");
   Serial.println(FPGA.getErrorMessage());
    while (1); 
  }
  Serial.println("FPGA configured sucessfull !");
  Wire.begin();
  Temperature_Sensor.begin();
}

void loop() {

  unsigned long start = millis();
  //-----reading and sending temperature data----------------------------------------------------------------------------------------------
  int status = Temperature_Sensor.read();
  if (status == DHT20_OK) {
    float temperature = Temperature_Sensor.getTemperature();
    for (int i = 0; i<=win_size-1; i++) {
      temp_win[i] = temp_win[i+1];
    }
    temp_win[win_size-1] = temperature;

    float Normalise_Temp =  (temperature-TEMP_MIN)/(TEMP_MAX-TEMP_MIN);
    uint16_t sending_temperature = (uint16_t)(Normalise_Temp * 256);

    // Sending the data (sensor_in) to Register 0 (register 0 of the JTAG interface)
    FPGA.write(0, sending_temperature); 
    // Pulse DataReady (Register 2) to validate the entry
    FPGA.write(2, 1); 
    delayMicroseconds(1); // Allow time for the FPGA clk  to see the front
    FPGA.write(2, 0);
    delayMicroseconds(1);
  }
    
  // ****************************3. reading and Sending  Light data ***************************************************************************************************************
    // Conversion to Q8.8 (as in Python: value * 256)
    ///
      //Serial.println(".................HERE..................");
  float light =analogRead(A2);
  for (int i = 0; i<win_size-1; i++) {
    light_win[i] = light_win[i+1];
  }
  light_win[win_size-1] = light;
  float Normalise_light=  (light-LIGHT_MIN)/(LIGHT_MAX-LIGHT_MIN);
  uint16_t sending_light = (uint16_t)(Normalise_light * 256);

  // Sending the data (sensor_in) to Register 0 (register 0 of the JTAG interface)
  FPGA.write(1, sending_light); 
  // Pulse DataReady (Register 3) to validate the entry
  FPGA.write(3, 1); 
  delayMicroseconds(1); // Allow time for the FPGA clk  to see the front
  FPGA.write(3, 0);
  delayMicroseconds(1);

  //while(FPGA.read(0))//waiting for the result
  delay(10);
  ///. READING prediction data
  uint16_t prediction_temp = FPGA.read(1);//------------------TEMPERATURE
  uint16_t prediction_Light = FPGA.read(2);//------------------LIGHT
  
  // Reverse conversion: from Q8.8 to Float
  float prediction__temp_float=prediction_temp/ 256.0;
  float reel_predtiction_temp = prediction__temp_float*(TEMP_MAX-TEMP_MIN) + TEMP_MIN;
  // Reverse conversion: from Q8.8 to Float
  float prediction_light_float=prediction_Light/ 256.0;
  float reel_predtiction_light = prediction_light_float*(LIGHT_MAX-LIGHT_MIN) + LIGHT_MIN;
  
  unsigned long exe_time = millis() - start;

  Serial.println("## ITERATION COMPLETE ##");

  Serial.print("Temp window: ");
  printwin(temp_win);
  Serial.print(" => prediction: ");
  Serial.println(reel_predtiction_temp);

  Serial.print("Light window: ");
  printwin(light_win);
  Serial.print(" => prediction: ");
  Serial.println(reel_predtiction_light);
  
  Serial.print("Prediction was ready in: ");
  Serial.print(exe_time/1000);
  Serial.println(" s");


  unsigned long period_ms = measure_period_s * 1000UL;

  if (exe_time < period_ms) {
    unsigned long wait_time = period_ms - exe_time;

    Serial.print("Waiting for ");
    Serial.print(wait_time/float(1000));
    Serial.println(" s");

    delay(wait_time);
  } else {
    Serial.println("No waiting: execution time exceeded measurement period.");
  }
}