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
Dennis van Gils, 10-06-2024
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
const uint32_t PERIOD_SC = 20; // [ms] Period to listen for serial commands
DvG_SerialCommand sc(Ser);

// General string buffer
const int BUFLEN = 255;
char buf[BUFLEN];

/*------------------------------------------------------------------------------
  Time keeping
------------------------------------------------------------------------------*/

void get_systick_timestamp(uint32_t *stamp_millis,
                           uint16_t *stamp_micros_part) {
  /* Adapted from:
  https://github.com/arduino/ArduinoCore-samd/blob/master/cores/arduino/delay.c

  Note:
    The millis counter will roll over after 49.7 days.
  */
  // clang-format off
  uint32_t ticks, ticks2;
  uint32_t pend, pend2;
  uint32_t count, count2;
  uint32_t _ulTickCount = millis();

  ticks2 = SysTick->VAL;
  pend2  = !!(SCB->ICSR & SCB_ICSR_PENDSTSET_Msk);
  count2 = _ulTickCount;

  do {
    ticks  = ticks2;
    pend   = pend2;
    count  = count2;
    ticks2 = SysTick->VAL;
    pend2  = !!(SCB->ICSR & SCB_ICSR_PENDSTSET_Msk);
    count2 = _ulTickCount;
  } while ((pend != pend2) || (count != count2) || (ticks < ticks2));

  (*stamp_millis) = count2;
  if (pend) {(*stamp_millis)++;}
  (*stamp_micros_part) =
    (((SysTick->LOAD - ticks) * (1048576 / (VARIANT_MCK / 1000000))) >> 20);
  // clang-format on
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
  static bool DAQ_running = false;
  uint32_t DT;   // [us] Obtained DAQ interval
  float I;       // [mA] Current
  float V;       // [mV] Bus voltage
  float V_shunt; // [mV] Shunt voltage
  float E;       // [J]  Energy
  // float P;       // [mW] Power
  // float T_die;   // ['C] Die temperature

  // Time keeping
  static bool trigger_reset_time = false;
  static uint32_t startup_millis = 0; // Time when DAQ turned on
  static uint16_t startup_micros = 0; // Time when DAQ turned on
  uint32_t millis_copy;
  uint16_t micros_part;

  get_systick_timestamp(&millis_copy, &micros_part);

  /*----------------------------------------------------------------------------
    Process incoming serial commands every PERIOD_SC milliseconds
  ----------------------------------------------------------------------------*/
  static uint32_t tick_sc = millis_copy;

  if ((millis_copy - tick_sc) > PERIOD_SC) {
    tick_sc = millis_copy;
    if (sc.available()) {
      strCmd = sc.getCmd();

      if (strcmp(strCmd, "id?") == 0) {
        Ser.println("Arduino, Wind Turbine");
        DAQ_running = false;

      } else if (strcmp(strCmd, "r") == 0) {
        ina228.reset_accumulators();

      } else if (strcmp(strCmd, "on") == 0) {
        DAQ_running = true;
        trigger_reset_time = true;

      } else if (strcmp(strCmd, "off") == 0) {
        DAQ_running = false;

      } else {
        DAQ_running = !DAQ_running;
        trigger_reset_time = true;
      }
    }
  }

  /*----------------------------------------------------------------------------
    Acquire data
  ----------------------------------------------------------------------------*/

  if (trigger_reset_time) {
    trigger_reset_time = false;
    startup_millis = millis_copy;
    startup_micros = micros_part;
  }

  if (DAQ_running) {
    // Set start DAQ to time = 0.000
    millis_copy -= startup_millis;
    if (micros_part >= startup_micros) {
      micros_part -= startup_micros;
    } else {
      micros_part = micros_part + 1000 - startup_micros;
      millis_copy -= 1;
    }

    // Acquire
    I = ina228.readCurrent();
    V = ina228.readBusVoltage();
    V_shunt = ina228.readShuntVoltage();
    E = ina228.readEnergy();
    // P = ina228.readPower();
    // P = I * V / 1e3;
    // T_die = ina228.readDieTemp();

    snprintf(buf, BUFLEN,
             "%lu\t"   // Timestamp millis [ms]
             "%u\t"    // Timestamp micros part [us]
             "%.2f\t"  // I  [mA]
             "%.2f\t"  // V  [mV]
             "%.4f\t"  // V_shunt [mV]
             "%.5f\n", // E  [J]
             millis_copy, micros_part, I, V, V_shunt, E);
    Ser.print(buf);
  }
}