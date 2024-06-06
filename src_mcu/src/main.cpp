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
  05-06-2024
*******************************************************************************/

#include <Adafruit_INA228.h>

// [Ohm] Shunt resistor internal to Adafruit INA228
const float R_SHUNT = 0.015;
// [A] Maximum expected current
const float MAX_CURRENT = 0.2;
// Shunt full scale ADC range. 0: +/-163.84 mV or 1: +/-40.96 mV.
const uint8_t ADC_RANGE = 1;

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

  ina228.setShunt(R_SHUNT, MAX_CURRENT, ADC_RANGE);
  ina228.setMode(INA228_MODE_CONT_TEMP_BUS_SHUNT);

  // [#] 1, 4, 16, 64, 128, 256, 512, 1024
  ina228.setAveragingCount(INA228_COUNT_4);

  // [us] 50, 84, 150, 280, 540, 1052, 2074, 4120
  ina228.setCurrentConversionTime(INA228_TIME_150_us);
  ina228.setVoltageConversionTime(INA228_TIME_150_us);
  ina228.setTemperatureConversionTime(INA228_TIME_50_us);

  // Report settings to terminal
  Serial.print("ADC range      : ");
  Serial.println(ina228.getADCRange());
  Serial.print("Mode           : ");
  Serial.println(ina228.getMode());
  Serial.print("Averaging count: ");
  Serial.println(ina228.getAveragingCount());
  Serial.print("Current     conversion time: ");
  Serial.println(ina228.getCurrentConversionTime());
  Serial.print("Voltage     conversion time: ");
  Serial.println(ina228.getVoltageConversionTime());
  Serial.print("Temperature conversion time: ");
  Serial.println(ina228.getTemperatureConversionTime());
}

// -----------------------------------------------------------------------------
//  loop
// -----------------------------------------------------------------------------

void loop() {
  static uint32_t tick = micros();
  static uint32_t tick_print = micros();
  float I;       // Current [mA]
  float V_shunt; // Shunt voltage [mV]
  float V;       // Bus voltage [mV]
  float P;       // Power [mW]
  float E;       // Energy [J]
  float T_die;   // Die temperature ['C]
  uint32_t now, DT;

  now = micros();
  DT = now - tick;
  tick = now;

  I = ina228.readCurrent();    // [mA]
  V = ina228.readBusVoltage(); // [mV]
  P = I * V / 1e3;             // [mW]
  E = ina228.readEnergy();     // [J]

  // P = ina228.readPower();          // [mW]
  V_shunt = ina228.readShuntVoltage(); // [mV]
  T_die = ina228.readDieTemp();        // ['C]

  if (now - tick_print >= PERIOD * 1000) {
    tick_print = now;
    snprintf(buf, BUFLEN,
             "DT = %4.2f ms | "
             "I = %5.1f mA | "
             "V_shunt = %6.2f mV | "
             "V = %6.1f mV | "
             "P = %6.1f mW | "
             "E = %6.2f J | "
             "T = %.1f 'C",
             DT / 1000., I, V_shunt, V, P, E, T_die);
    Serial.println(buf);
  }
}