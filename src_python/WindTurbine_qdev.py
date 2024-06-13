#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt/PySide module to provide multithreaded communication and periodical data
acquisition for an Arduino programmed as a wind turbine.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-windfarm-practicum"
__date__ = "10-06-2024"
__version__ = "1.0"
# pylint: disable=missing-docstring

from typing import Callable

from dvg_qdeviceio import QDeviceIO, DAQ_TRIGGER
from WindTurbineArduino import WindTurbineArduino


class WindTurbine_qdev(QDeviceIO):
    """Manages multithreaded communication and periodical data acquisition for
    an Arduino programmed as a wind turbine."""

    def __init__(
        self,
        dev: WindTurbineArduino,
        DAQ_function: Callable[[], bool],
        debug=False,
        **kwargs,
    ):
        super().__init__(dev, **kwargs)  # Pass kwargs onto QtCore.QObject()
        self.dev: WindTurbineArduino  # Enforce type: removes `_NoDevice()`

        # Pause/resume mechanism
        self.DAQ_is_enabled = True

        self.create_worker_DAQ(
            DAQ_trigger=DAQ_TRIGGER.CONTINUOUS,
            DAQ_function=DAQ_function,
            critical_not_alive_count=3,
            debug=debug,
        )
        self.create_worker_jobs(debug=debug)

    # --------------------------------------------------------------------------
    #   Arduino communication functions
    # --------------------------------------------------------------------------

    def turn_on(self):
        self.send(self.dev.turn_on)

    def turn_off(self):
        self.send(self.dev.turn_off)

    def reset_accumulators(self):
        self.send(self.dev.reset_accumulators)

    # --------------------------------------------------------------------------
    #   _DAQ_function
    # --------------------------------------------------------------------------

    def set_DAQ_enabled(self, state: bool):
        self.DAQ_is_enabled = state
        if self.DAQ_is_enabled:
            self.turn_on()
            self.unpause_DAQ()
        else:
            self.turn_off()
            self.pause_DAQ()