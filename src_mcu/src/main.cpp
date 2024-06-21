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
Dennis van Gils, 20-06-2024
*/

#include <Arduino.h>

#include "Adafruit_INA228.h"
#include "Adafruit_NeoPixel.h"
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

// Figure out the onboard RGB led, if any
#if defined(_VARIANT_FEATHER_M4_)
#  define HAS_DOTSTAR 0
#  define HAS_NEOPIXEL 1
#elif defined(_VARIANT_ITSYBITSY_M4_)
#  define HAS_DOTSTAR 1
#  define HAS_NEOPIXEL 0
#else
#  define HAS_DOTSTAR 0
#  define HAS_NEOPIXEL 0
#endif

#if HAS_NEOPIXEL
#  include "Adafruit_NeoPixel.h"
Adafruit_NeoPixel led_rgb(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
#endif

#if HAS_DOTSTAR
#  include <Adafruit_DotStar.h>
Adafruit_DotStar led_rgb(DOTSTAR_NUM, PIN_DOTSTAR_DATA, PIN_DOTSTAR_CLK,
                         DOTSTAR_BGR);
#endif

#if HAS_NEOPIXEL || HAS_DOTSTAR
const uint32_t LED_COLOR_SETUP = led_rgb.Color(0, 0, 6);
const uint32_t LED_COLOR_IDLE = led_rgb.Color(0, 6, 0);
const uint32_t LED_COLOR_DAQ_RUNNING = led_rgb.Color(6, 6, 0);
#endif

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

// Starting setup
#if HAS_NEOPIXEL || HAS_DOTSTAR
  led_rgb.begin();
  led_rgb.setBrightness(255);
  led_rgb.setPixelColor(0, LED_COLOR_SETUP);
  led_rgb.show();
#endif

  Ser.begin(115200);
  while (!Ser) { // Wait until serial port is opened
    delay(10);
  }

  uint8_t i = 0;
  for (auto &ina228 : ina228_sensors) {
    uint8_t i2c_address = ina228_addresses[i];
    if (!ina228.begin(i2c_address, &Wire, SKIP_RESET)) {
      Ser.print("Couldn't find INA228 chip at address 0x");
      Ser.println(i2c_address, HEX);
      while (1) {}
    }
    // Ser.print("Found INA228 chip at address 0x");
    // Ser.println(i2c_address, HEX);
    i++;

    ina228.setShunt(R_SHUNT, MAX_CURRENT);
    ina228.setADCRange(ADC_RANGE);
    ina228.setMode(INA228_MODE_CONT_TEMP_BUS_SHUNT);

    // [#] 1, 4, 16, 64, 128, 256, 512, 1024
    ina228.setAveragingCount(INA228_COUNT_4);

    // [us] 50, 84, 150, 280, 540, 1052, 2074, 4120
    ina228.setCurrentConversionTime(INA228_TIME_4120_us);
    ina228.setVoltageConversionTime(INA228_TIME_4120_us);
    ina228.setTemperatureConversionTime(INA228_TIME_50_us);

    // Report settings to terminal
    /*
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
    */
  }

// Finished setup and idle
#if HAS_NEOPIXEL || HAS_DOTSTAR
  led_rgb.setPixelColor(0, LED_COLOR_IDLE);
  led_rgb.show();
#endif
}

/*------------------------------------------------------------------------------
    loop
------------------------------------------------------------------------------*/

void loop() {
  char *strCmd; // Incoming serial command string
  static bool DAQ_running = false;
  bool prev_DAQ_running = DAQ_running;
  float I; // [mA] Current
  float V; // [mV] Bus voltage
  float E; // [J]  Energy
  // float V_shunt; // [mV] Shunt voltage
  // float P;       // [mW] Power
  // float T_die;   // ['C] Die temperature

  // Time keeping
  uint32_t millis_copy = millis();
  uint16_t micros_part;

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
    LED indicator
  ----------------------------------------------------------------------------*/

#if HAS_NEOPIXEL || HAS_DOTSTAR
  if (DAQ_running != prev_DAQ_running) {
    prev_DAQ_running = DAQ_running;
    if (DAQ_running) {
      led_rgb.setPixelColor(0, LED_COLOR_DAQ_RUNNING);
      led_rgb.show();
    } else {
      led_rgb.setPixelColor(0, LED_COLOR_IDLE);
      led_rgb.show();
    }
  }
#endif

  /*----------------------------------------------------------------------------
    Acquire data
  ----------------------------------------------------------------------------*/

  if (DAQ_running && ina228_sensors[0].conversionReady()) {
    get_systick_timestamp(&millis_copy, &micros_part);

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