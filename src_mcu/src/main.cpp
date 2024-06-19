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
Dennis van Gils, 19-06-2024
*/

#include <Arduino.h>

#include "Adafruit_INA228.h"
#include "DvG_SerialCommand.h"

// INA228 current sensors
Adafruit_INA228 ina228_sensors[] = {
    Adafruit_INA228(),
    Adafruit_INA228(),
    Adafruit_INA228(),
};

// INA228 I2C addresses
uint8_t ina228_addresses[] = {0x40, 0x41, 0x44};

// [Ohm] Shunt resistor internal to Adafruit INA228
const float R_SHUNT = 0.015;
// [A] Maximum expected current
const float MAX_CURRENT = 0.2;
// Shunt full scale ADC range. 0: +/-163.84 mV or 1: +/-40.96 mV.
const uint8_t ADC_RANGE = 1;
// Prevent resetting the INA228 chip on init?
const bool SKIP_RESET = true;

// Instantiate serial command listener
#define Ser Serial
const uint32_t PERIOD_SC = 20; // [ms] Period to listen for serial commands
DvG_SerialCommand sc(Ser);

// General string buffer
const int BUFLEN = 1024;
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

  uint8_t i = 0;
  for (auto &ina228 : ina228_sensors) {
    uint8_t i2c_address = ina228_addresses[i];
    if (!ina228.begin(i2c_address, &Wire, SKIP_RESET)) {
      Ser.print("Couldn't find INA228 chip at address ");
      Ser.println(i2c_address, HEX);
      while (1) {}
    }
    Ser.print("Found INA228 chip at address ");
    Ser.println(i2c_address, HEX);
    i++;

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
    Ser.println();
  }
}

/*------------------------------------------------------------------------------
    loop
------------------------------------------------------------------------------*/

void loop() {
  char *strCmd; // Incoming serial command string
  static bool DAQ_running = false;
  float I; // [mA] Current
  float V; // [mV] Bus voltage
  float E; // [J]  Energy
  // float V_shunt; // [mV] Shunt voltage
  // float P;       // [mW] Power
  // float T_die;   // ['C] Die temperature

  // Time keeping
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
        for (auto &ina228 : ina228_sensors) {
          ina228.resetAccumulators();
        }

      } else if (strcmp(strCmd, "on") == 0) {
        DAQ_running = true;

      } else if (strcmp(strCmd, "off") == 0) {
        DAQ_running = false;

      } else {
        DAQ_running = !DAQ_running;
      }
    }
  }

  /*----------------------------------------------------------------------------
    Acquire data
  ----------------------------------------------------------------------------*/

  if (DAQ_running) {
    snprintf(buf, BUFLEN,
             "%lu\t" // Timestamp millis [ms]
             "%u",   // Timestamp micros part [us]
             millis_copy, micros_part);

    for (auto &ina228 : ina228_sensors) {
      I = ina228.readCurrent();
      V = ina228.readBusVoltage();
      E = ina228.readEnergy();
      // V_shunt = ina228.readShuntVoltage();
      // P = ina228.readPower();
      // P = I * V / 1e3;
      // T_die = ina228.readDieTemp();

      snprintf(buf + strlen(buf), BUFLEN - strlen(buf),
               "\t"
               "%.2f\t" // I
               "%.2f\t" // V
               "%.5f",  // E
               I, V, E);
    }

    Ser.println(buf);
  }
}