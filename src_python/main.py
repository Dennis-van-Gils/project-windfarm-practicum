#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wind turbine
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-windfarm-practicum"
__date__ = "07-06-2024"
__version__ = "1.0"
# pylint: disable=missing-function-docstring, unnecessary-lambda

import os
import sys

import qtpy
from qtpy import QtCore, QtGui, QtWidgets as QtWid
from qtpy.QtCore import Slot  # type: ignore

import psutil
import numpy as np
import pyqtgraph as pg

from dvg_pyqtgraph_threadsafe import HistoryChartCurve, PlotManager
from dvg_pyqt_filelogger import FileLogger
import dvg_pyqt_controls as controls

from WindTurbineArduino import WindTurbineArduino
from WindTurbine_qdev import WindTurbine_qdev

# Constants
CHART_CAPACITY = int(1e4)  # [number of points]
CHART_INTERVAL_MS = 20  # [ms]

# Global flags
TRY_USING_OPENGL = True
USE_LARGER_TEXT = False

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False

print(f"{qtpy.API_NAME:9s} {qtpy.QT_VERSION}")  # type: ignore
print(f"PyQtGraph {pg.__version__}")

if TRY_USING_OPENGL:
    try:
        import OpenGL.GL as gl  # pylint: disable=unused-import
        from OpenGL.version import __version__ as gl_version
    except Exception:  # pylint: disable=broad-except
        print("PyOpenGL  not found")
        print("To install: `conda install pyopengl` or `pip install pyopengl`")
    else:
        print(f"PyOpenGL  {gl_version}")
        pg.setConfigOptions(useOpenGL=True)
        pg.setConfigOptions(antialias=True)
        pg.setConfigOptions(enableExperimental=True)
else:
    print("PyOpenGL  disabled")

# Global pyqtgraph configuration
# pg.setConfigOptions(leftButtonPan=False)
pg.setConfigOption("foreground", "#EEE")

# ------------------------------------------------------------------------------
#   current_date_time_strings
# ------------------------------------------------------------------------------


def current_date_time_strings():
    cur_date_time = QtCore.QDateTime.currentDateTime()
    return (
        cur_date_time.toString("dd-MM-yyyy"),  # Date
        cur_date_time.toString("HH:mm:ss"),  # Time
    )


# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------


class MainWindow(QtWid.QWidget):
    def __init__(
        self,
        qdev: WindTurbine_qdev,
        qlog: FileLogger,
        parent=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.qdev = qdev
        self.qdev.signal_DAQ_updated.connect(self.update_GUI)
        self.qlog = qlog

        self.setWindowTitle("Arduino wind turbine")
        self.setGeometry(40, 60, 960, 660)
        self.setStyleSheet(controls.SS_TEXTBOX_READ_ONLY + controls.SS_GROUP)

        # -------------------------
        #   Chart refresh timer
        # -------------------------

        self.timer_chart = QtCore.QTimer()
        self.timer_chart.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.timer_chart.timeout.connect(self.update_chart)

        # -------------------------
        #   Top frame
        # -------------------------

        # Left box
        self.qlbl_update_counter = QtWid.QLabel("0")
        self.qlbl_DAQ_rate = QtWid.QLabel("DAQ: nan Hz")
        self.qlbl_DAQ_rate.setStyleSheet("QLabel {min-width: 7em}")
        self.qlbl_recording_time = QtWid.QLabel()

        vbox_left = QtWid.QVBoxLayout()
        vbox_left.addWidget(self.qlbl_update_counter, stretch=0)
        vbox_left.addStretch(1)
        vbox_left.addWidget(self.qlbl_recording_time, stretch=0)
        vbox_left.addWidget(self.qlbl_DAQ_rate, stretch=0)

        # Middle box
        self.qlbl_title = QtWid.QLabel("Arduino wind turbine")
        self.qlbl_title.setFont(
            QtGui.QFont(
                "Palatino",
                20 if USE_LARGER_TEXT else 14,
                weight=QtGui.QFont.Weight.Bold,
            )
        )
        self.qlbl_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.qlbl_cur_date_time = QtWid.QLabel("00-00-0000    00:00:00")
        self.qlbl_cur_date_time.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.qpbt_record = controls.create_Toggle_button(
            "Click to start recording to file", minimumHeight=40
        )
        self.qpbt_record.setMinimumWidth(400)
        self.qpbt_record.clicked.connect(lambda state: qlog.record(state))

        vbox_middle = QtWid.QVBoxLayout()
        vbox_middle.addWidget(self.qlbl_title)
        vbox_middle.addWidget(self.qlbl_cur_date_time)
        vbox_middle.addWidget(self.qpbt_record)

        # Right box
        p = {
            "alignment": QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignVCenter,
            "parent": self,
        }
        self.qpbt_exit = QtWid.QPushButton("Exit")
        self.qpbt_exit.clicked.connect(self.close)
        self.qpbt_exit.setMinimumHeight(30)
        self.qlbl_GitHub = QtWid.QLabel(
            f'<a href="{__url__}">GitHub source</a>', **p
        )
        self.qlbl_GitHub.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.qlbl_GitHub.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.qlbl_GitHub.setOpenExternalLinks(True)

        vbox_right = QtWid.QVBoxLayout()
        vbox_right.setSpacing(4)
        vbox_right.addWidget(self.qpbt_exit, stretch=0)
        vbox_right.addStretch(1)
        vbox_right.addWidget(QtWid.QLabel(__author__, **p))
        vbox_right.addWidget(self.qlbl_GitHub)
        vbox_right.addWidget(QtWid.QLabel(f"v{__version__}", **p))

        # Round up top frame
        hbox_top = QtWid.QHBoxLayout()
        hbox_top.addLayout(vbox_left, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_middle, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_right, stretch=0)

        # -------------------------
        #   Bottom frame
        # -------------------------

        # GraphicsLayoutWidget
        self.gw = pg.GraphicsLayoutWidget()
        self.plot = self.gw.addPlot()

        p = {
            "color": "#EEE",
            "font-size": "20pt" if USE_LARGER_TEXT else "10pt",
        }
        self.plot.setClipToView(True)
        self.plot.showGrid(x=1, y=1)
        self.plot.setLabel("bottom", text="history (sec)", **p)
        self.plot.setLabel("left", text="amplitude", **p)

        if USE_LARGER_TEXT:
            font = QtGui.QFont()
            font.setPixelSize(26)
            self.plot.getAxis("bottom").setTickFont(font)
            self.plot.getAxis("bottom").setStyle(tickTextOffset=20)
            self.plot.getAxis("bottom").setHeight(90)
            self.plot.getAxis("left").setTickFont(font)
            self.plot.getAxis("left").setStyle(tickTextOffset=20)
            self.plot.getAxis("left").setWidth(120)

        self.history_chart_curve = HistoryChartCurve(
            capacity=CHART_CAPACITY,
            linked_curve=self.plot.plot(
                pen=pg.mkPen(color=[255, 255, 0], width=3)
            ),
        )

        # 'Readings'
        p = {"readOnly": True, "maximumWidth": 112 if USE_LARGER_TEXT else 63}
        self.qlin_reading_t = QtWid.QLineEdit(**p)
        self.qlin_reading_1 = QtWid.QLineEdit(**p)
        self.qpbt_running = controls.create_Toggle_button(
            "Running", checked=False
        )
        self.qpbt_running.clicked.connect(
            lambda state: self.process_qpbt_running(state)
        )

        # fmt: off
        grid = QtWid.QGridLayout()
        grid.addWidget(self.qpbt_running   , 0, 0, 1, 2)
        grid.addWidget(QtWid.QLabel("time"), 1, 0)
        grid.addWidget(self.qlin_reading_t , 1, 1)
        grid.addWidget(QtWid.QLabel("#01") , 2, 0)
        grid.addWidget(self.qlin_reading_1 , 2, 1)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        # fmt: on

        qgrp_readings = QtWid.QGroupBox("Readings")
        qgrp_readings.setLayout(grid)

        # -------------------------
        #   PlotManager
        # -------------------------

        self.plot_manager = PlotManager(parent=self)
        self.plot_manager.add_autorange_buttons(linked_plots=self.plot)
        self.plot_manager.add_preset_buttons(
            linked_plots=self.plot,
            linked_curves=[self.history_chart_curve],
            presets=[
                {
                    "button_label": "0.100",
                    "x_axis_label": "history (msec)",
                    "x_axis_divisor": 1e-3,
                    "x_axis_range": (-101, 0),
                },
                {
                    "button_label": "0:05",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-5.05, 0),
                },
                {
                    "button_label": "0:10",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-10.1, 0),
                },
            ],
        )
        self.plot_manager.add_clear_button(
            linked_curves=[self.history_chart_curve]
        )
        self.plot_manager.perform_preset(1)

        qgrp_chart = QtWid.QGroupBox("Chart")
        qgrp_chart.setLayout(self.plot_manager.grid)

        vbox = QtWid.QVBoxLayout()
        vbox.addWidget(qgrp_readings)
        vbox.addWidget(qgrp_chart)
        vbox.addStretch()

        # Round up bottom frame
        hbox_bot = QtWid.QHBoxLayout()
        hbox_bot.addWidget(self.gw, 1)
        hbox_bot.addLayout(vbox, 0)

        # -------------------------
        #   Round up full window
        # -------------------------

        vbox = QtWid.QVBoxLayout(self)
        vbox.addLayout(hbox_top, stretch=0)
        vbox.addSpacerItem(QtWid.QSpacerItem(0, 10))
        vbox.addLayout(hbox_bot, stretch=1)

    # --------------------------------------------------------------------------
    #   Handle controls
    # --------------------------------------------------------------------------

    @Slot(bool)
    def process_qpbt_running(self, state: bool):
        self.qpbt_running.setText("Running" if state else "Paused")
        self.qdev.set_DAQ_enabled(state)

    @Slot()
    def update_GUI(self):
        str_cur_date, str_cur_time = current_date_time_strings()
        state = self.qdev.dev.state  # Shorthand

        self.qlbl_cur_date_time.setText(f"{str_cur_date}    {str_cur_time}")
        self.qlbl_update_counter.setText(f"{self.qdev.update_counter_DAQ}")
        self.qlbl_DAQ_rate.setText(
            f"DAQ: {self.qdev.obtained_DAQ_rate_Hz:.1f} Hz"
        )
        self.qlbl_recording_time.setText(
            f"REC: {self.qlog.pretty_elapsed()}"
            if self.qlog.is_recording()
            else ""
        )
        self.qlin_reading_t.setText(f"{state.time[0]:.3f}")
        self.qlin_reading_1.setText(f"{state.V_mV[0]:.4f}")

    @Slot()
    def update_chart(self):
        # if DEBUG:
        #     tprint("update_curve")

        self.history_chart_curve.update()


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Set priority of this process to maximum in the operating system
    print(f"PID: {os.getpid()}\n")
    try:
        proc = psutil.Process(os.getpid())
        if os.name == "nt":
            proc.nice(psutil.REALTIME_PRIORITY_CLASS)  # Windows
        else:
            proc.nice(-20)  # Other
    except Exception:  # pylint: disable=broad-except
        print("Warning: Could not set process to maximum priority.\n")

    # --------------------------------------------------------------------------
    #   Connect to Arduino
    # --------------------------------------------------------------------------

    ard = WindTurbineArduino(ring_buffer_capacity=100)

    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect()

    if not ard.is_alive:
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # --------------------------------------------------------------------------
    #   Create application
    # --------------------------------------------------------------------------

    main_thread = QtCore.QThread.currentThread()
    if isinstance(main_thread, QtCore.QThread):
        main_thread.setObjectName("MAIN")  # For DEBUG info

    if qtpy.PYQT6 or qtpy.PYSIDE6:
        sys.argv += ["-platform", "windows:darkmode=0"]
    app = QtWid.QApplication(sys.argv)
    app.setStyle("Fusion")
    if USE_LARGER_TEXT:
        app.setFont(QtGui.QFont(QtWid.QApplication.font().family(), 16))

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    def DAQ_function() -> bool:
        new_rows_count = ard.listen_to_Arduino()

        if new_rows_count != ard.state.capacity:
            return False

        # Add readings to chart history
        window.history_chart_curve.extendData(ard.state.time, ard.state.V_mV)

        # Add readings to the log
        log.update()

        return True

    ard_qdev = WindTurbine_qdev(
        dev=ard,
        DAQ_function=DAQ_function,
        debug=DEBUG,
    )

    # --------------------------------------------------------------------------
    #   File logger
    # --------------------------------------------------------------------------

    def write_header_to_log():
        log.write("elapsed [s]\treading_1\n")

    def write_data_to_log():
        np_data = np.column_stack((ard.state.time, ard.state.V_mV))
        log.np_savetxt(np_data, "%.4f\t%.4f")

    log = FileLogger(
        write_header_function=write_header_to_log,
        write_data_function=write_data_to_log,
    )
    log.signal_recording_started.connect(
        lambda filepath: window.qpbt_record.setText(
            f"Recording to file: {filepath}"
        )
    )
    log.signal_recording_stopped.connect(
        lambda: window.qpbt_record.setText("Click to start recording to file")
    )

    # --------------------------------------------------------------------------
    #   Program termination routines
    # --------------------------------------------------------------------------

    def stop_running():
        app.processEvents()
        log.close()
        ard_qdev.quit()
        ard.close()

        print("Stopping timers: ", end="")
        window.timer_chart.stop()
        print("done.")

    def about_to_quit():
        print("\nAbout to quit")
        stop_running()

    # --------------------------------------------------------------------------
    #   Start the main GUI event loop
    # --------------------------------------------------------------------------

    window = MainWindow(qdev=ard_qdev, qlog=log)
    window.timer_chart.start(CHART_INTERVAL_MS)
    window.show()

    ard_qdev.start(DAQ_priority=QtCore.QThread.Priority.TimeCriticalPriority)

    app.aboutToQuit.connect(about_to_quit)
    sys.exit(app.exec())