#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt/PySide module to provide multithreaded communication and periodical data
acquisition for an Arduino programmed as a wind farm, interfacing multiple
wind turbines at once.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-windfarm-practicum"
__date__ = "14-11-2024"
__version__ = "2.0"
# pylint: disable=missing-docstring

from typing import Callable

from dvg_qdeviceio import QDeviceIO, DAQ_TRIGGER
from WindFarmArduino import WindFarmArduino


class WindFarm_qdev(QDeviceIO):
    """Manages multithreaded communication and periodical data acquisition for
    an Arduino programmed as a wind farm, interfacing multiple wind turbines at
    once."""

    def __init__(
        self,
        dev: WindFarmArduino,
        DAQ_function: Callable[[], bool],
        debug=False,
        **kwargs,
    ):
        super().__init__(dev, **kwargs)  # Pass kwargs onto QtCore.QObject()
        self.dev: WindFarmArduino  # Enforce type: removes `_NoDevice()`

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
