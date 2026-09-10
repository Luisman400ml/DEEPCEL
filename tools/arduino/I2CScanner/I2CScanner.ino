#include <Wire.h>

void setup() {
  Serial.begin(9600);
  while (!Serial)
    ;

  Wire.begin();
  Wire.setTimeout(50);
  Serial.println("I2C scanner ready.");
}

void loop() {
  byte found = 0;

  Serial.println("Scanning I2C bus...");
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("I2C device found at 0x");
      if (address < 16) {
        Serial.print('0');
      }
      Serial.println(address, HEX);
      found++;
    }
  }

  Serial.print("I2C devices found: ");
  Serial.println(found);
  Serial.println();
  delay(5000);
}
