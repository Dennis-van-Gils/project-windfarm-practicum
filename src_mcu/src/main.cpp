/*******************************************************************************
  Windfarm practicum

  Hardware
  --------

  Microcontroller:
    - Adafruit Feather M4 Express (ADA3857)

  Sensor:
    - Adafruit INA228 (ADA5832): I2C 85V, 20-bit High or Low Side Power Monitor
      featuring Texas Instruments INA228

  Wind turbine toy model:
    - Sol Expert 40004 H0 Windturbine op zonne-energie

  https://github.com/Dennis-van-Gils/project-windfarm-practicum
  Dennis van Gils
  28-05-2024
*******************************************************************************/

#include <Adafruit_INA228.h>

const float R_SHUNT = 0.015; // [Ohm] Shunt resistor internal to Adafruit INA228
const float MAX_CURRENT = 0.2; // [A] Maximum expected current

const uint32_t PERIOD = 500; // [ms]
const int BUFLEN = 255;      // Length of general string buffer
char buf[BUFLEN];            // General string buffer

Adafruit_INA228 ina228 = Adafruit_INA228();

// -----------------------------------------------------------------------------
//  setup
// -----------------------------------------------------------------------------

void setup() {
  asm(".global _printf_float"); // Enables float support for `snprintf()`

  Serial.begin(115200);
  while (!Serial) { // Wait until serial port is opened
    delay(10);
  }

  if (!ina228.begin()) {
    Serial.println("Couldn't find INA228 chip");
    while (1) {}
  }

  Serial.println("Found INA228 chip");

  ina228.setShunt(R_SHUNT, MAX_CURRENT);

  // [#] 1, 4, 16, 64, 128, 256, 512, 1024
  ina228.setAveragingCount(INA228_COUNT_4);

  // [us] 50, 84, 150, 280, 540, 1052, 2074, 4120
  ina228.setVoltageConversionTime(INA228_TIME_150_us);

  // [us] 50, 84, 150, 280, 540, 1052, 2074, 4120
  ina228.setCurrentConversionTime(INA228_TIME_150_us);

  Serial.print("Voltage conversion time: ");
  switch (ina228.getVoltageConversionTime()) {
    case INA228_TIME_50_us:
      Serial.print("50");
      break;
    case INA228_TIME_84_us:
      Serial.print("84");
      break;
    case INA228_TIME_150_us:
      Serial.print("150");
      break;
    case INA228_TIME_280_us:
      Serial.print("280");
      break;
    case INA228_TIME_540_us:
      Serial.print("540");
      break;
    case INA228_TIME_1052_us:
      Serial.print("1052");
      break;
    case INA228_TIME_2074_us:
      Serial.print("2074");
      break;
    case INA228_TIME_4120_us:
      Serial.print("4120");
      break;
  }
  Serial.println(" us");

  Serial.print("Current conversion time: ");
  switch (ina228.getCurrentConversionTime()) {
    case INA228_TIME_50_us:
      Serial.print("50");
      break;
    case INA228_TIME_84_us:
      Serial.print("84");
      break;
    case INA228_TIME_150_us:
      Serial.print("150");
      break;
    case INA228_TIME_280_us:
      Serial.print("280");
      break;
    case INA228_TIME_540_us:
      Serial.print("540");
      break;
    case INA228_TIME_1052_us:
      Serial.print("1052");
      break;
    case INA228_TIME_2074_us:
      Serial.print("2074");
      break;
    case INA228_TIME_4120_us:
      Serial.print("4120");
      break;
  }
  Serial.println(" us");

  ina228.setMode(INA228_MODE_TRIGGERED);
}

// -----------------------------------------------------------------------------
//  loop
// -----------------------------------------------------------------------------

void loop() {
  static uint32_t tick = micros();
  static uint32_t tick_print = micros();
  float I;     // Current [mA]
  float V_bus; // Bus voltage [mV]
  float P;     // Power [mW]
  float E;     // Energy [J]
  uint32_t now, DT;

  while (!ina228.conversionReady()) {
    delayMicroseconds(10);
  }

  // Immediately start acquiring new measurement values for the next
  // `conversionReady()` to speed up the effective data rate. This is possible
  // because the INA228 chip has a dedicated digital engine running in the
  // background. The upcoming `read...()` statements will still reflect the last
  // above `conversionReady()` state, provided the conversion times and
  // averaging count are chosen long enough.
  ina228.setMode(INA228_MODE_TRIGGERED);

  now = micros();
  DT = now - tick;
  tick = now;

  I = ina228.readCurrent();        // [mA]
  V_bus = ina228.readBusVoltage(); // [mV]
  P = ina228.readPower();          // [mW]
  E = ina228.readEnergy();         // [J]

  if (now - tick_print >= PERIOD * 1000) {
    tick_print = now;
    snprintf(buf, BUFLEN,
             "DT = %4.2f ms | I = %5.1f mA | V = %6.1f mV | "
             "P = %6.1f mW | E = %6.2f J",
             DT / 1000., I, V_bus, P, E);
    Serial.println(buf);
  }
}