#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides class `WindFarmArduino` to manage serial communication with an
Arduino programmed as a wind farm, interfacing multiple wind turbines at once.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-windfarm-practicum"
__date__ = "14-11-2024"
__version__ = "2.0"
# pylint: disable=missing-docstring

import serial
import numpy as np

from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_debug_functions import print_fancy_traceback as pft
from dvg_ringbuffer import RingBuffer


class WindFarmArduino(Arduino):
    """Manages serial communication with an Arduino programmed as a wind
    farm."""

    class State:
        """Container for the measurement values of the wind farm Arduino."""

        def __init__(self, capacity):
            self.capacity = capacity
            """Ring buffer capacity"""

            self.time = RingBuffer(capacity)
            """Time stamp [s]"""

            self.I_1 = RingBuffer(capacity)
            """Current [mA]"""
            self.I_2 = RingBuffer(capacity)
            """Current [mA]"""
            self.I_3 = RingBuffer(capacity)
            """Current [mA]"""
            self.I_4 = RingBuffer(capacity)
            """Current [mA]"""
            self.I_5 = RingBuffer(capacity)
            """Current [mA]"""
            self.I_6 = RingBuffer(capacity)
            """Current [mA]"""

            self.V_1 = RingBuffer(capacity)
            """Bus voltage [mV]"""
            self.V_2 = RingBuffer(capacity)
            """Bus voltage [mV]"""
            self.V_3 = RingBuffer(capacity)
            """Bus voltage [mV]"""
            self.V_4 = RingBuffer(capacity)
            """Bus voltage [mV]"""
            self.V_5 = RingBuffer(capacity)
            """Bus voltage [mV]"""
            self.V_6 = RingBuffer(capacity)
            """Bus voltage [mV]"""

            self.E_1 = RingBuffer(capacity)
            """Accumulated energy [J]"""
            self.E_2 = RingBuffer(capacity)
            """Accumulated energy [J]"""
            self.E_3 = RingBuffer(capacity)
            """Accumulated energy [J]"""
            self.E_4 = RingBuffer(capacity)
            """Accumulated energy [J]"""
            self.E_5 = RingBuffer(capacity)
            """Accumulated energy [J]"""
            self.E_6 = RingBuffer(capacity)
            """Accumulated energy [J]"""

            self.P_1 = RingBuffer(capacity)
            """Power [mW]"""
            self.P_2 = RingBuffer(capacity)
            """Power [mW]"""
            self.P_3 = RingBuffer(capacity)
            """Power [mW]"""
            self.P_4 = RingBuffer(capacity)
            """Power [mW]"""
            self.P_5 = RingBuffer(capacity)
            """Power [mW]"""
            self.P_6 = RingBuffer(capacity)
            """Power [mW]"""

            # fmt: off
            self._ringbuffers = [
                self.time,
                self.I_1, self.I_2, self.I_3, self.I_4, self.I_5, self.I_6,
                self.V_1, self.V_2, self.V_3, self.V_4, self.V_5, self.V_6,
                self.E_1, self.E_2, self.E_3, self.E_4, self.E_5, self.E_6,
                self.P_1, self.P_2, self.P_3, self.P_4, self.P_5, self.P_6,
            ]
            """List of all ring buffers"""
            # fmt: on

        def clear_ring_buffers(self):
            for rb in self._ringbuffers:
                rb.clear()

    def __init__(
        self,
        name="Ard",
        long_name="Arduino",
        connect_to_specific_ID="Wind Farm",
        ring_buffer_capacity: int = 15,
    ):
        super().__init__(
            name=name,
            long_name=long_name,
            connect_to_specific_ID=connect_to_specific_ID,
        )

        # Container for the measurement values
        self.state = self.State(capacity=ring_buffer_capacity)

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

        try:
            time_millis = int(parts[0])  # [ms]
            time_micros = int(parts[1])  # [us] fraction
            I_1 = float(parts[2])  # [mA]
            V_1 = float(parts[3])  # [mV]
            E_1 = float(parts[4])  # [J]
            I_2 = float(parts[5])
            V_2 = float(parts[6])
            E_2 = float(parts[7])
            I_3 = float(parts[8])
            V_3 = float(parts[9])
            E_3 = float(parts[10])
            I_4 = float(parts[11])
            V_4 = float(parts[12])
            E_4 = float(parts[13])
            I_5 = float(parts[14])
            V_5 = float(parts[15])
            E_5 = float(parts[16])
            I_6 = float(parts[17])
            V_6 = float(parts[18])
            E_6 = float(parts[19])
        except IndexError:
            pft("Received an incorrect number of values from the Arduino.")
            return False
        except ValueError:
            pft("Failed to convert Arduino data into numeric values.")
            return False

        # Derived
        P_1 = np.maximum(I_1 * V_1 / 1e3, 0)  # [mW]
        P_2 = np.maximum(I_2 * V_2 / 1e3, 0)
        P_3 = np.maximum(I_3 * V_3 / 1e3, 0)
        P_4 = np.maximum(I_4 * V_4 / 1e3, 0)
        P_5 = np.maximum(I_5 * V_5 / 1e3, 0)
        P_6 = np.maximum(I_6 * V_6 / 1e3, 0)

        self.state.time.append(time_millis / 1e3 + time_micros / 1e6)

        self.state.I_1.append(I_1)
        self.state.V_1.append(V_1)
        self.state.E_1.append(E_1)
        self.state.P_1.append(P_1)

        self.state.I_2.append(I_2)
        self.state.V_2.append(V_2)
        self.state.E_2.append(E_2)
        self.state.P_2.append(P_2)

        self.state.I_3.append(I_3)
        self.state.V_3.append(V_3)
        self.state.E_3.append(E_3)
        self.state.P_3.append(P_3)

        self.state.I_4.append(I_4)
        self.state.V_4.append(V_4)
        self.state.E_4.append(E_4)
        self.state.P_4.append(P_4)

        self.state.I_5.append(I_5)
        self.state.V_5.append(V_5)
        self.state.E_5.append(E_5)
        self.state.P_5.append(P_5)

        self.state.I_6.append(I_6)
        self.state.V_6.append(V_6)
        self.state.E_6.append(E_6)
        self.state.P_6.append(P_6)

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
                pft("Data received from the Arduino was not an ASCII string.")
                break

            if not self.parse_readings(line):
                break

            new_rows_count += 1
            if new_rows_count == self.state.capacity:
                break

        return new_rows_count
