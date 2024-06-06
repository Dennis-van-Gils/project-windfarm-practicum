/*
Arduino Wind Turbine

Part of the 'Wind farm practicum' for the 'Sustainable Energy' course of the
University of Twente.

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
Dennis van Gils, 06-06-2024
*/

#include <Arduino.h>

#include "Adafruit_INA228.h"
#include "DvG_SerialCommand.h"

// INA228 current sensor
Adafruit_INA228 ina228 = Adafruit_INA228();

// [Ohm] Shunt resistor internal to Adafruit INA228
const float R_SHUNT = 0.015;
// [A] Maximum expected current
const float MAX_CURRENT = 0.2;
// Shunt full scale ADC range. 0: +/-163.84 mV or 1: +/-40.96 mV.
const uint8_t ADC_RANGE = 1;

// Instantiate serial command listener
#define Ser Serial
const uint32_t PERIOD_SC = 20e3; // [us] Period to listen for serial commands
DvG_SerialCommand sc(Ser);

// General string buffer
const int BUFLEN = 255;
char buf[BUFLEN];

/*------------------------------------------------------------------------------
    reset_ina228_energy_accumulator
------------------------------------------------------------------------------*/

void reset_ina228_energy_accumulator() {
  Adafruit_I2CRegisterBits reset_accumulator =
      Adafruit_I2CRegisterBits(ina228.Config, 1, 14);
  reset_accumulator.write(1);
}

/*------------------------------------------------------------------------------
    setup
------------------------------------------------------------------------------*/

void setup() {
  asm(".global _printf_float"); // Enables float support for `snprintf()`

  Ser.begin(115200);
  while (!Ser) { // Wait until serial port is opened
    delay(10);
  }

  const uint8_t I2C_ADDRESS = 64;
  const bool SKIP_RESET = true;

  if (!ina228.begin(I2C_ADDRESS, &Wire, SKIP_RESET)) {
    Ser.println("Couldn't find INA228 chip");
    while (1) {}
  }
  Ser.println("Found INA228 chip");

  ina228.setShunt(R_SHUNT, MAX_CURRENT, ADC_RANGE);
  ina228.setMode(INA228_MODE_CONT_TEMP_BUS_SHUNT);

  // [#] 1, 4, 16, 64, 128, 256, 512, 1024
  ina228.setAveragingCount(INA228_COUNT_4);

  // [us] 50, 84, 150, 280, 540, 1052, 2074, 4120
  ina228.setCurrentConversionTime(INA228_TIME_150_us);
  ina228.setVoltageConversionTime(INA228_TIME_150_us);
  ina228.setTemperatureConversionTime(INA228_TIME_50_us);

  // Report settings to terminal
  Ser.print("ADC range      : ");
  Ser.println(ina228.getADCRange());
  Ser.print("Mode           : ");
  Ser.println(ina228.getMode());
  Ser.print("Averaging count: ");
  Ser.println(ina228.getAveragingCount());
  Ser.print("Current     conversion time: ");
  Ser.println(ina228.getCurrentConversionTime());
  Ser.print("Voltage     conversion time: ");
  Ser.println(ina228.getVoltageConversionTime());
  Ser.print("Temperature conversion time: ");
  Ser.println(ina228.getTemperatureConversionTime());
}

/*------------------------------------------------------------------------------
    loop
------------------------------------------------------------------------------*/

void loop() {
  char *strCmd; // Incoming serial command string
  static uint32_t tick_DAQ = micros();
  static uint32_t tick_sc = tick_DAQ;
  static bool DAQ_running = false;
  uint32_t DT;   // [us] Obtained DAQ interval
  float I;       // [mA] Current
  float V;       // [mV] Bus voltage
  float V_shunt; // [mV] Shunt voltage
  float E;       // [J]  Energy
  // float P;       // [mW] Power
  // float T_die;   // ['C] Die temperature

  uint32_t now = micros(); // [us] Timestamp

  // DAQ
  if (DAQ_running) {
    DT = now - tick_DAQ;
    tick_DAQ = now;

    I = ina228.readCurrent();
    V = ina228.readBusVoltage();
    V_shunt = ina228.readShuntVoltage();
    E = ina228.readEnergy();
    // P = ina228.readPower();
    // P = I * V / 1e3;
    // T_die = ina228.readDieTemp();

    snprintf(buf, BUFLEN,
             "%lu\t"   // DT [us]
             "%.2f\t"  // I  [mA]
             "%.1f\t"  // V  [mV]
             "%.3f\t"  // V_shunt [mV]
             "%.3f\n", // E  [J]
             DT, I, V, V_shunt, E);
    Ser.print(buf);
  }

  // Process incoming serial commands every PERIOD_SC microseconds
  if ((now - tick_sc) > PERIOD_SC) {
    tick_sc = now;
    if (sc.available()) {
      strCmd = sc.getCmd();

      if (strcmp(strCmd, "id?") == 0) {
        Ser.println("Arduino, Wind Turbine");

      } else if (strcmp(strCmd, "r") == 0) {
        reset_ina228_energy_accumulator();

      } else if (strcmp(strCmd, "on") == 0) {
        DAQ_running = true;

      } else if (strcmp(strCmd, "off") == 0) {
        DAQ_running = false;

      } else {
        DAQ_running = !DAQ_running;
      }
    }
  }
}