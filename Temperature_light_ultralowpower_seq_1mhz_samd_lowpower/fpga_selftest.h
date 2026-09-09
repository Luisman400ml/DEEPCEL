#pragma once

#include "FPGA.h"

struct PredictionPair {
  uint8_t temperature;
  uint8_t light;
};

static int16_t q4Product(int8_t a, int8_t b) {
  int16_t product = int16_t(a) * int16_t(b);
  if (product >= 0) {
    return product >> 4;
  }
  return -int16_t((int16_t(-product) + 15) >> 4);
}

static int8_t relu8(int16_t sum) {
  return sum > 0 ? int8_t(uint8_t(sum)) : int8_t(0);
}

static PredictionPair referencePrediction(const uint8_t tempHistory[4], const uint8_t lightHistory[4]) {
  static const int8_t hiddenWeights[16][8] = {
    {-5, -3, 9, 5, -1, -1, -1, -2},
    {-3, 2, -2, 5, -7, -5, 3, -4},
    {7, 5, 3, 2, -2, 0, -2, 4},
    {-3, 5, 5, -7, -5, 1, 2, -1},
    {8, 3, -3, -2, 3, -6, 7, -7},
    {2, -7, -4, 2, -7, 6, 6, -7},
    {5, 2, -3, 8, 0, 9, 3, 0},
    {-3, 5, -6, -1, 3, 3, -1, 5},
    {0, 2, 0, 1, -2, 3, 5, 0},
    {2, 2, 0, -4, -4, 9, 6, 0},
    {2, -1, -6, 8, 0, -6, 4, 8},
    {-7, -5, 5, -6, 3, 2, 2, -3},
    {-7, -3, 2, -8, 5, 6, 1, -7},
    {0, 6, -6, -5, 0, -1, -2, -6},
    {-7, -6, 4, 5, -4, 6, -2, 1},
    {1, 7, -3, 3, 1, 4, -1, 8}
  };
  static const int8_t hiddenBiases[16] = {
    3, -1, -1, 0, 2, 0, 1, 1, -1, 1, 1, -1, -2, 0, 0, 1
  };
  static const int8_t outputWeights[2][16] = {
    {5, -9, 6, 5, 4, 4, 0, -8, 6, -2, 2, -2, 4, 1, -9, 7},
    {-8, 7, 0, -8, -3, -7, 4, 7, -5, 4, 5, 0, 1, 6, -8, 4}
  };
  static const int8_t outputBiases[2] = {-1, 1};

  int8_t inputs[8] = {
    int8_t(tempHistory[0]), int8_t(tempHistory[1]),
    int8_t(tempHistory[2]), int8_t(tempHistory[3]),
    int8_t(lightHistory[0]), int8_t(lightHistory[1]),
    int8_t(lightHistory[2]), int8_t(lightHistory[3])
  };

  int8_t hidden[16];
  for (unsigned neuron = 0; neuron < 16; ++neuron) {
    int16_t sum = hiddenBiases[neuron];
    for (unsigned input = 0; input < 8; ++input) {
      sum += q4Product(inputs[input], hiddenWeights[neuron][input]);
    }
    hidden[neuron] = relu8(sum);
  }

  uint8_t outputs[2];
  for (unsigned output = 0; output < 2; ++output) {
    int16_t sum = outputBiases[output];
    for (unsigned input = 0; input < 16; ++input) {
      sum += q4Product(hidden[input], outputWeights[output][input]);
    }
    outputs[output] = uint8_t(relu8(sum));
  }

  return {outputs[0], outputs[1]};
}

static void writeFpgaSamplePair(uint8_t temperature, uint8_t light, unsigned settleMs = 2) {
  FPGA.write(0, temperature);
  FPGA.write(1, light);
  FPGA.write(2, 1);
  delayMicroseconds(20);
  FPGA.write(2, 0);
  FPGA.write(3, 1);
  delayMicroseconds(20);
  FPGA.write(3, 0);
  delay(settleMs);
}

static void clearFpgaHistory() {
  for (unsigned index = 0; index < 4; ++index) {
    writeFpgaSamplePair(0, 0);
  }
}

static bool runFpgaSelfTest(bool verbose = true) {
  const uint8_t boundaryValues[] = {0, 1, 8, 15, 16};
  uint8_t tempHistory[4] = {0, 0, 0, 0};
  uint8_t lightHistory[4] = {0, 0, 0, 0};
  uint32_t randomState = 12345;
  unsigned failures = 0;

  clearFpgaHistory();
  for (unsigned index = 0; index < 128; ++index) {
    randomState = randomState * 1664525UL + 1013904223UL;
    uint8_t temperature = index < 5 ? boundaryValues[index] : uint8_t((randomState >> 16) % 17);
    randomState = randomState * 1664525UL + 1013904223UL;
    uint8_t light = index < 5 ? boundaryValues[4 - index] : uint8_t((randomState >> 16) % 17);

    tempHistory[0] = tempHistory[1];
    tempHistory[1] = tempHistory[2];
    tempHistory[2] = tempHistory[3];
    tempHistory[3] = temperature;
    lightHistory[0] = lightHistory[1];
    lightHistory[1] = lightHistory[2];
    lightHistory[2] = lightHistory[3];
    lightHistory[3] = light;

    PredictionPair expected = referencePrediction(tempHistory, lightHistory);
    writeFpgaSamplePair(temperature, light, 5);

    uint8_t actualTemperature = uint8_t(FPGA.read(0) & 0xFF);
    uint8_t actualLight = uint8_t(FPGA.read(1) & 0xFF);
    delay(1);
    uint8_t heldTemperature = uint8_t(FPGA.read(0) & 0xFF);
    uint8_t heldLight = uint8_t(FPGA.read(1) & 0xFF);

    if (actualTemperature != expected.temperature || actualLight != expected.light ||
        heldTemperature != expected.temperature || heldLight != expected.light) {
      ++failures;
      if (verbose && failures <= 8) {
        Serial.print("SELFTEST mismatch temp_q4_4=");
        Serial.print(temperature);
        Serial.print(" light_q4_4=");
        Serial.print(light);
        Serial.print(" expected_temp=");
        Serial.print(expected.temperature);
        Serial.print(" actual_temp=");
        Serial.print(actualTemperature);
        Serial.print(" expected_light=");
        Serial.print(expected.light);
        Serial.print(" actual_light=");
        Serial.println(actualLight);
      }
    }
  }
  clearFpgaHistory();

  if (verbose || failures != 0) {
    Serial.print("SELFTEST ");
    Serial.print(failures == 0 ? "PASS" : "FAIL");
    Serial.print(" multisensor_q4_4 vectors=128 reads=512 failures=");
    Serial.println(failures);
  }
  return failures == 0;
}
