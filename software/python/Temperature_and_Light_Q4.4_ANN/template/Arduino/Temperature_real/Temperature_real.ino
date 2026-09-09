#include "FPGA.h"
#include "DHT20.h"


#define TEMP_MIN  24.612081304273765
#define TEMP_MAX  37.95430094132428

#define LIGHT_MIN 163.7478016239505
#define LIGHT_MAX 1027.5785826547694

DHT20 sensor1;

void setup() {
  pinMode(A2,INPUT);
  Serial.begin(9600);
  while(!Serial);

  // 1.  FPGA INITIALISATION 
  
  if (!FPGA.begin(16,4)) {
    Serial.println("ERROR : Impossible configuration of FPGA.");
   Serial.println(FPGA.getErrorMessage());
    while (1); 
  }
  Serial.println("FPGA configured sucessfull !");
  Wire.begin();
  sensor1.begin();
}

void loop() {
  //-----reading and sending temperature data----------------------------------------------------------------------------------------------
  float window1[8]={0,0,0,0,0,0,0,0};
  for(int i=0; i<4; i++){ 
    int status = sensor1.read();
    if (status == DHT20_OK) {
   
      float temperature = sensor1.getTemperature();
      window1[i]=temperature;
      float Normalise_Temp =  (temperature-TEMP_MIN)/(TEMP_MAX-TEMP_MIN);
      uint16_t sending_temperature = (uint16_t)(Normalise_Temp * 16);
  
     // Sending the data (sensor_in) to Register 0 (register 0 of the JTAG interface)
      FPGA.write(0, sending_temperature); 

      // Pulse DataReady (Register 2) to validate the entry
      FPGA.write(2, 1); 
      delayMicroseconds(1); // Allow time for the FPGA clk  to see the front
      FPGA.write(2, 0);
      delay(2000);
   }
    
    else {
    Serial.println("Errore di lettur del sensore di temperatura.");
    }
  }  
  // ****************************3. reading and Sending  Light data ***************************************************************************************************************
   for(int i=4; i<8; i++){ 
     // Conversion to Q4.4 (as in Python: value * 16)
    float LIGHT =analogRead(A2);
     window1[i]= LIGHT;
    float Normalise_Light=  (LIGHT-LIGHT_MIN)/(LIGHT_MAX-LIGHT_MIN);
    uint16_t Sensor_in2 = (uint16_t)(Normalise_Light * 16);
  
  // Sending the data (sensor_in) to Register 0 (register 0 of the JTAG interface)
    FPGA.write(1, Sensor_in2); 

    // Pulse DataReady (Register 3) to validate the entry
    FPGA.write(3, 1); 
    delayMicroseconds(1); // Allow time for the FPGA clk  to see the front
    FPGA.write(3, 0);
    
    delay(1000); 

  }


  ///. READING prediction data
  uint16_t prediction_temp = FPGA.read(0);//------------------TEMPERATURE
  
// Reverse conversion: from Q4.4 to Float
  float prediction__temp_float=prediction_temp/ 16.0;
  float reel_predtiction_temp = prediction__temp_float*(TEMP_MAX-TEMP_MIN) + TEMP_MIN;

  uint16_t prediction_Light = FPGA.read(1);//------------------LIGHT
  
// Reverse conversion: from Q4.4 to Float
  float prediction_Light_float=prediction_Light/ 16.0;
  float reel_predtiction_Light = prediction_Light_float*(LIGHT_MAX-LIGHT_MIN) + LIGHT_MIN;
  Serial.print("The actual window values is: [");
  for(int i=0; i<8; i++){ 
  Serial.print(window1[i]);
  Serial.print(", ");
  }
  Serial.print("] //and the  FPGA prediction is: ");
  Serial.print(reel_predtiction_temp);
  Serial.print(" °C  and  ");
  Serial.print(reel_predtiction_Light);
  Serial.println(" Lux ");
  Serial.println("--------------------------------------------------------------------------------------------- ");
  delay(3000);
  
  
}