#include "FPGA.h"      // This is the library specific to the Arduino MKR Vidor 4000. It allows the microcontroller (the SAMD21) to communicate directly with the FPGA integrated on the board using a JTAG connection.
#include "DHT20.h"    //  This is the library that manages the DHT20 temperature and humidity sensor. It simplifies I2C communication with the sensor to retrieve clean data.

float window[4] = {0.0, 0.0, 0.0, 0.0};    // Table (sliding window) to store the last 4 temperature values


DHT20 sensor1;                            // Creation of the object representing the DHT sensor

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

void setup() {
  Serial.begin(9600);
  while(!Serial);

  // FPGA INITIALIZATION
  // Configures the FPGA (JTAG communication parameters: register size and number of registers used)
  if (!FPGA.begin(32,2)) {                                    
    Serial.println("ERROR: Unable to configure the FPGA.");
    while (1);
  }
  Serial.println("FPGA successfully configured!");

  Wire.begin();
  if (!sensor1.begin()) {            // Initializes the sensor on the I2C bus.
    Serial.println("ERROR: DHT20 not found on I2C address 0x38.");
  } else {
    Serial.println("DHT20 sensor detected.");
  }
}

void loop() {
  
  int status = sensor1.read();         //Reading the status of the DHT sensor

   // If the sensor reading was successful (no error)
  if (status == DHT20_OK) {
    float temperature= sensor1.getTemperature(); // // retrieve the temperature value, you can also choose to retrieve the humidity value
   // Update the sliding window (shift the values ​​to the left)
    window[0] = window[1];
    window[1] = window[2];
    window[2] = window[3];
    // We add the new value to the end
    window[3] = temperature;
    
  // --- COMMUNICATION WITH THE FPGA ---

    uint16_t read_value = (uint16_t)(256*temperature); // // convert to Q8.8 format (useful for the FPGA part)

   // Sending the data (sensor_in) to Register 0 (register 0 of the JTAG interface)
    FPGA.write(0, read_value);   // Writes a value to a specific register of the FPGA.

    // // Sending a pulse to Register 1 to validate the input (signal "DataReady")
    FPGA.write(1, 1); 
    delayMicroseconds(1); // Allow time for the FPGA clk  to see the front
    FPGA.write(1, 0);
    delay(10); 

   // // --- DISPLAYING THE HISTORY OF THE 4 VALUES ---------------------------------------------------------------------------------------------------------------------------------------
    Serial.print("4 last  temperature history : [ ");
    for (int j = 0; j < 4; j++) {
      Serial.print(window[j]);
      if (j < 3) Serial.print(", ");
    }
    Serial.println(" ]");
  
   
  Serial.println("");

  // --- READING THE FPGA RESULT ---
  // We will read the prediction calculated by the FPGA from its Register 0
  uint16_t prediction = FPGA.read(0);   // Reads the value stored in a register of the FPGA.
  
// Reverse conversion: from Q8.8 to Float
  float prediction_float=prediction/ 256.0;

  // Displaying the prediction on the serial monitor
  Serial.print("FPGA prediction:");
  Serial.print(prediction_float);
  Serial.println(" °C");
  Serial.println("------------------------------------");
  Serial.println(" ");
  // 10-second pause before the next sensor reading
  delay(10000);
   } else {
    Serial.print("DHT20 read error: ");
    Serial.print(status);
    Serial.print(" (");
    Serial.print(dht20StatusMessage(status));
    Serial.println(")");
    delay(2000);
   }
} 
 
