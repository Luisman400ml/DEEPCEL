#pragma once

#include "FPGA.h"

// Bit-exact reference for the existing Arduino protocol: ready stays high
// long enough to fill all four FPGA window positions with the current sample.
static uint16_t referencePrediction(uint16_t sample) {
  static const int16_t weights[8][4] = {
    {-157, 5, -142, -84}, {-78, 133, 189, 115},
    {0, 92, 10, 125}, {-80, -154, -146, -105},
    {-56, -149, 64, 50}, {-102, -53, 22, -57},
    {153, 39, 92, 20}, {-150, 69, -83, -163}
  };
  static const int16_t biases[8] = {0, -11, -29, 0, -1, 0, -15, 0};
  static const int16_t outputWeights[8] = {2, 125, -117, 24, 174, 178, 153, -168};
  int32_t result = 4;
  for (unsigned neuron = 0; neuron < 8; ++neuron) {
    int32_t sum = biases[neuron];
    for (unsigned input = 0; input < 4; ++input) {
      sum += (int32_t(int16_t(sample)) * weights[neuron][input]) >> 8;
    }
    int16_t hidden = sum > 0 ? int16_t(sum) : 0;
    result += (int32_t(hidden) * outputWeights[neuron]) >> 8;
  }
  return result > 0 ? uint16_t(result) : 0;
}

static bool runFpgaSelfTest() {
  const uint16_t boundaries[] = {0, 1, 256, 5120, 6784, 15360, 3840, 7680};
  uint32_t randomState = 12345;
  unsigned failures = 0;
  for (unsigned index = 0; index < 128; ++index) {
    randomState = randomState * 1664525UL + 1013904223UL;
    uint16_t sample = index < 8 ? boundaries[index] : (randomState >> 16) % 15361;
    uint16_t expected = referencePrediction(sample);
    FPGA.write(0, sample);
    FPGA.write(1, 1);
    delayMicroseconds(1);
    FPGA.write(1, 0);
    delay(10);
    uint32_t actual = FPGA.read(0);
    delay(1);
    uint32_t held = FPGA.read(0);
    if (actual != expected || held != expected) {
      ++failures;
      if (failures <= 8) {
        Serial.print("SELFTEST mismatch input_q8_8=");
        Serial.print(sample);
        Serial.print(" expected=");
        Serial.print(expected);
        Serial.print(" actual=");
        Serial.print(actual);
        Serial.print(" held=");
        Serial.println(held);
      }
    }
  }
  Serial.print("SELFTEST ");
  Serial.print(failures == 0 ? "PASS" : "FAIL");
  Serial.print(" vectors=128 reads=256 failures=");
  Serial.println(failures);
  return failures == 0;
}
