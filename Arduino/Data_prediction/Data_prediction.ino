#include "FPGA.h"
#include "DHT20.h"


#define TEMP_MIN  24.612081304273765
#define TEMP_MAX  37.95430094132428

#define LIGHT_MIN 163.7478016239505
#define LIGHT_MAX 1027.5785826547694

  float window1[8]={0,0,0,0,0,0,0,0};
  int cnt_T=0;
  int cnt_L=4;

DHT20 Temperature_Sensor;

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
  Temperature_Sensor.begin();
}

void loop() {
    //-----reading and sending temperature data----------------------------------------------------------------------------------------------

    int status = Temperature_Sensor.read();
    if (status == DHT20_OK) {
   
      float temperature = Temperature_Sensor.getTemperature();
      window1[0]=window1[1];
      window1[1]=window1[2];
      window1[2]=window1[3];
      window1[3]=temperature;
      float Normalise_Temp =  (temperature-TEMP_MIN)/(TEMP_MAX-TEMP_MIN);
      uint16_t sending_temperature = (uint16_t)(Normalise_Temp * 256);
  
     // Sending the data (sensor_in) to Register 0 (register 0 of the JTAG interface)
      FPGA.write(0, sending_temperature); 

      // Pulse DataReady (Register 2) to validate the entry
      FPGA.write(2, 1); 
      delayMicroseconds(1); // Allow time for the FPGA clk  to see the front
      FPGA.write(2, 0);
      delay(2000);
    }
    
    else {
    Serial.println("Errore di lettura del sensore di temperatura.");
    }
    
  // ****************************3. reading and Sending  Light data ***************************************************************************************************************
     // Conversion to Q8.8 (as in Python: value * 256)
    float LIGHT =analogRead(A2);
      window1[4]=window1[5];
      window1[5]=window1[6];
      window1[6]=window1[7];
      window1[7]= LIGHT;
    float Normalise_Light=  (LIGHT-LIGHT_MIN)/(LIGHT_MAX-LIGHT_MIN);
    uint16_t Sensor_in2 = (uint16_t)(Normalise_Light * 256);
  
  // Sending the data (sensor_in) to Register 0 (register 0 of the JTAG interface)
    FPGA.write(1, Sensor_in2); 

    // Pulse DataReady (Register 3) to validate the entry
    FPGA.write(3, 1); 
    delayMicroseconds(1); // Allow time for the FPGA clk  to see the front
    FPGA.write(3, 0);
    
    delay(1000); 


  ///. READING prediction data
  uint16_t prediction_temp = FPGA.read(0);//------------------TEMPERATURE
  
// Reverse conversion: from Q8.8 to Float
  float prediction__temp_float=prediction_temp/ 256.0;
  float reel_predtiction_temp = prediction__temp_float*(TEMP_MAX-TEMP_MIN) + TEMP_MIN;

  uint16_t prediction_Light = FPGA.read(1);//------------------LIGHT
  
// Reverse conversion: from Q8.8 to Float
  float prediction_Light_float=prediction_Light/ 256.0;
  float reel_predtiction_Light = prediction_Light_float*(LIGHT_MAX-LIGHT_MIN) + LIGHT_MIN;
  Serial.print("The actual window values is:[");
  for(int i=0; i<8; i++){ 
  Serial.print(window1[i]);
  Serial.print(", ");
  }
  Serial.print("] /// and the FPGA prediction is: ");
  Serial.print(reel_predtiction_temp);
  Serial.print(" °C  and  ");
  Serial.print(reel_predtiction_Light);
  Serial.println(" Lux ");
  Serial.println("--------------------------------------------------------------------------------------------- ");
  delay(5000);
  

}