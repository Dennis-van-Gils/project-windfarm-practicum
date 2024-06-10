#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides class `WindTurbineArduino` to manage serial communication with an
Arduino programmed as a wind turbine.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-windfarm-practicum"
__date__ = "10-06-2024"
__version__ = "1.0"
# pylint: disable=missing-docstring

import serial

from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_debug_functions import print_fancy_traceback as pft
from dvg_ringbuffer import RingBuffer


class WindTurbineArduino(Arduino):
    """Manages serial communication with an Arduino programmed as a wind
    turbine."""

    class State:
        """Container for the measurement values of the wind turbine Arduino."""

        def __init__(self, capacity: int = 100):
            self.capacity = capacity
            """Ring buffer capacity"""

            self.time = RingBuffer(capacity)
            """Time stamp [s]"""
            self.I_mA = RingBuffer(capacity)
            """Current [mA]"""
            self.V_mV = RingBuffer(capacity)
            """Bus voltage [mV]"""
            self.V_shunt_mV = RingBuffer(capacity)
            """Shunt voltage [mV]"""
            self.E_J = RingBuffer(capacity)
            """Accumulated energy [J]"""
            self.P_mW = RingBuffer(capacity)
            """Power [mW]"""

            self._ringbuffers = [
                self.time,
                self.I_mA,
                self.V_mV,
                self.V_shunt_mV,
                self.E_J,
                self.P_mW,
            ]
            """List of all ring buffers"""

        def clear_ring_buffers(self):
            for rb in self._ringbuffers:
                rb.clear()

    def __init__(
        self,
        name="Ard",
        long_name="Arduino",
        connect_to_specific_ID="Wind Turbine",
        ring_buffer_capacity: int = 100,
    ):
        super().__init__(
            name=name,
            long_name=long_name,
            connect_to_specific_ID=connect_to_specific_ID,
        )

        # Container for the measurement values
        self.state = self.State(ring_buffer_capacity)

    # --------------------------------------------------------------------------
    #   Arduino commands
    # --------------------------------------------------------------------------

    def turn_on(self) -> bool:
        return self.write("on")

    def turn_off(self) -> bool:
        return self.write("off")

    def reset_accumulators(self) -> bool:
        return self.write("r")

    # --------------------------------------------------------------------------
    #   parse_readings
    # --------------------------------------------------------------------------

    def parse_readings(self, line: str) -> bool:
        """Parse the ASCII string `line` as received from the Arduino into
        separate variables and store these into the `state` ring buffers.

        Returns True when successful, False otherwise.
        """
        parts = line.strip("\n").split("\t")
        if not len(parts) == 6:
            pft(
                "ERROR: Received an incorrect number of values from the "
                "Arduino."
            )
            return False

        try:
            # fmt: off
            time_millis = int(parts[0])
            time_micros = int(parts[1])
            I_mA        = float(parts[2])
            V_mV        = float(parts[3])
            V_shunt_mV  = float(parts[4])
            E_J         = float(parts[5])
            # fmt: on
        except ValueError:
            pft("ERROR: Failed to convert Arduino data into numeric values.")
            return False

        self.state.time.append(time_millis / 1e3 + time_micros / 1e6)
        self.state.I_mA.append(I_mA)
        self.state.V_mV.append(V_mV)
        self.state.V_shunt_mV.append(V_shunt_mV)
        self.state.E_J.append(E_J)

        return True

    # --------------------------------------------------------------------------
    #   listen_to_Arduino
    # --------------------------------------------------------------------------

    def listen_to_Arduino(self) -> int:
        """Listen to the Arduino for new readings being broadcast over the
        serial port. The Arduino must have received the `turn_on()` command
        in order for it to send out these readings.

        This method is blocking until we received enough data to fill up the
        ring buffers with all new data, or until communication timed out.

        Returns the number of newly appended data rows.
        """

        new_rows_count = 0
        while True:
            try:
                _success, line = self.readline(raises_on_timeout=True)
            except serial.SerialException:
                print("Communication timed out. ", end="")
                if new_rows_count == 0:
                    print("No new data was appended to the ring buffers.")
                else:
                    print("New data was appended to the ring buffers.")
                break

            if not isinstance(line, str):
                pft(
                    "ERROR: Data received from the Arduino was not an ASCII "
                    "string."
                )
                break

            if not self.parse_readings(line):
                break

            new_rows_count += 1
            if new_rows_count == self.state.capacity:
                break

        return new_rows_count
