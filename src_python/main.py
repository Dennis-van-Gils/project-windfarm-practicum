#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wind turbine
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-windfarm-practicum"
__date__ = "21-06-2024"
__version__ = "1.0"
# pylint: disable=missing-function-docstring, unnecessary-lambda
# pylint: disable=multiple-statements

import os
import sys

import qtpy
from qtpy import QtCore, QtGui, QtWidgets as QtWid
from qtpy.QtCore import Slot  # type: ignore

import psutil
import numpy as np
import pyqtgraph as pg
import qtawesome as qta

from dvg_debug_functions import tprint
from dvg_pyqtgraph_threadsafe import (
    HistoryChartCurve,
    ThreadSafeCurve,
    LegendSelect,
    PlotManager,
)
from dvg_pyqt_filelogger import FileLogger
import dvg_pyqt_controls as controls

from WindTurbineArduino import WindTurbineArduino
from WindTurbine_qdev import WindTurbine_qdev

# Constants
CHART_CAPACITY = int(1e4)  # [number of points]

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

        self.do_update_readings_GUI = True
        """Update the GUI elements corresponding to the Arduino readings, like
        textboxes and charts?"""

        self.setWindowTitle("Arduino wind turbine")
        self.setGeometry(40, 60, 960, 660)
        self.setStyleSheet(controls.SS_TEXTBOX_READ_ONLY + controls.SS_GROUP)

        # -------------------------
        #   Top frame
        # -------------------------

        # Left box
        self.qlbl_update_counter = QtWid.QLabel("0")
        self.qlbl_DAQ_rate_1 = QtWid.QLabel("DAQ: nan blocks/s")
        self.qlbl_DAQ_rate_1.setStyleSheet("QLabel {min-width: 7em}")
        self.qlbl_DAQ_rate_2 = QtWid.QLabel("DAQ: nan Hz")
        self.qlbl_DAQ_rate_2.setStyleSheet("QLabel {min-width: 7em}")
        self.qlbl_recording_time = QtWid.QLabel()

        vbox_left = QtWid.QVBoxLayout()
        vbox_left.addWidget(self.qlbl_update_counter, stretch=0)
        vbox_left.addStretch(1)
        vbox_left.addWidget(self.qlbl_recording_time, stretch=0)
        vbox_left.addWidget(self.qlbl_DAQ_rate_1, stretch=0)
        vbox_left.addWidget(self.qlbl_DAQ_rate_2, stretch=0)

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

        p = {
            "color": "#EEE",
            "font-size": "20pt" if USE_LARGER_TEXT else "10pt",
        }

        self.pi_power: pg.PlotItem = self.gw.addPlot(row=0, col=0)
        self.pi_power.setLabel("left", text="power : P (mW)", **p)
        self.pi_power.setYRange(0, 6)

        self.pi_energy: pg.PlotItem = self.gw.addPlot(row=1, col=0)
        self.pi_energy.setLabel("left", text="energy : E (J)", **p)
        self.pi_energy.enableAutoRange(axis="y")

        self.pi_all = [self.pi_power, self.pi_energy]
        # List of all PlotItems

        for plot_item in self.pi_all:
            plot_item.setClipToView(True)
            plot_item.showGrid(x=1, y=1)
            plot_item.setLabel("bottom", text="history (sec)", **p)

            if USE_LARGER_TEXT:
                font = QtGui.QFont()
                font.setPixelSize(26)
                plot_item.getAxis("bottom").setTickFont(font)
                plot_item.getAxis("bottom").setStyle(tickTextOffset=20)
                plot_item.getAxis("bottom").setHeight(90)
                plot_item.getAxis("left").setTickFont(font)
                plot_item.getAxis("left").setStyle(tickTextOffset=20)
                plot_item.getAxis("left").setWidth(120)

        # -------------------------
        #   Create history charts
        # -------------------------

        pen_1 = pg.mkPen(color=(255, 30, 180), width=3)
        pen_2 = pg.mkPen(color=(255, 255, 90), width=3)
        pen_3 = pg.mkPen(color=(0, 255, 255), width=3)

        self.tscurves_P: list[ThreadSafeCurve] = []
        """List of all ThreadSafeCurves for plotting the power [mW]"""

        self.tscurves_P.append(
            HistoryChartCurve(
                capacity=CHART_CAPACITY,
                linked_curve=self.pi_power.plot(pen=pen_1, name="Turbine #1"),
            )
        )
        self.tscurves_P.append(
            HistoryChartCurve(
                capacity=CHART_CAPACITY,
                linked_curve=self.pi_power.plot(pen=pen_2, name="Turbine #2"),
            )
        )
        self.tscurves_P.append(
            HistoryChartCurve(
                capacity=CHART_CAPACITY,
                linked_curve=self.pi_power.plot(pen=pen_3, name="Turbine #3"),
            )
        )

        self.tscurves_E: list[ThreadSafeCurve] = []
        """List of all ThreadSafeCurves for plotting the energy [J]"""

        self.tscurves_E.append(
            HistoryChartCurve(
                capacity=CHART_CAPACITY,
                linked_curve=self.pi_energy.plot(pen=pen_1, name="Turbine #1"),
            )
        )
        self.tscurves_E.append(
            HistoryChartCurve(
                capacity=CHART_CAPACITY,
                linked_curve=self.pi_energy.plot(pen=pen_2, name="Turbine #2"),
            )
        )
        self.tscurves_E.append(
            HistoryChartCurve(
                capacity=CHART_CAPACITY,
                linked_curve=self.pi_energy.plot(pen=pen_3, name="Turbine #3"),
            )
        )

        self.tscurves_all = self.tscurves_P + self.tscurves_E
        # List of all ThreadSafeCurves

        # -------------------------
        #   Legend
        # -------------------------

        legend = LegendSelect(linked_curves=self.tscurves_P)
        legend.grid.setVerticalSpacing(0)

        self.qgrp_legend = QtWid.QGroupBox("Legend")
        self.qgrp_legend.setLayout(legend.grid)

        # -------------------------
        #   PlotManager
        # -------------------------

        self.plot_manager = PlotManager(parent=self)
        self.plot_manager.add_autorange_buttons(linked_plots=self.pi_all)
        self.plot_manager.add_preset_buttons(
            linked_plots=self.pi_all,
            linked_curves=self.tscurves_all,
            presets=[
                {
                    "button_label": "0:30",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-30, 0),
                },
                {
                    "button_label": "1:00",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-60, 0),
                },
                {
                    "button_label": "5:00",
                    "x_axis_label": "history (min)",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-5, 0),
                },
            ],
        )
        self.plot_manager.add_clear_button(linked_curves=self.tscurves_all)
        self.plot_manager.perform_preset(1)

        qgrp_history = QtWid.QGroupBox("History")
        qgrp_history.setLayout(self.plot_manager.grid)

        # -------------------------
        # -------------------------

        # 'Readings'
        p = {"readOnly": True, "maximumWidth": 112 if USE_LARGER_TEXT else 63}
        self.timestamp = QtWid.QLineEdit(**p)
        self.P_1 = QtWid.QLineEdit(**p)
        self.P_2 = QtWid.QLineEdit(**p)
        self.P_3 = QtWid.QLineEdit(**p)
        self.E_1 = QtWid.QLineEdit(**p)
        self.E_2 = QtWid.QLineEdit(**p)
        self.E_3 = QtWid.QLineEdit(**p)
        self.qpbt_running = controls.create_Toggle_button(
            "Running", checked=True
        )
        self.qpbt_running.clicked.connect(
            lambda state: self.process_qpbt_running(state)
        )
        self.qpbt_reset_E = QtWid.QPushButton("Reset\naccumulated energy")
        self.qpbt_reset_E.clicked.connect(self.process_qpbt_reset_E)

        # fmt: off
        i = 0
        grid = QtWid.QGridLayout()
        grid.addWidget(self.qpbt_running       , i, 0, 1, 3); i+=1
        grid.addWidget(self.qpbt_reset_E       , i, 0, 1, 3); i+=1
        grid.addWidget(QtWid.QLabel("Time")    , i, 0)
        grid.addWidget(self.timestamp          , i, 1)
        grid.addWidget(QtWid.QLabel("sec")     , i, 2); i+=1

        #grid.addWidget(QtWid.QLabel("#") , i, 0)
        grid.addWidget(QtWid.QLabel("P (mW)")  , i, 1)
        grid.addWidget(QtWid.QLabel("E (J)")   , i, 2); i+=1

        grid.addWidget(QtWid.QLabel("#1")      , i, 0)
        grid.addWidget(self.P_1                , i, 1)
        grid.addWidget(self.E_1                , i, 2); i+=1
        grid.addWidget(QtWid.QLabel("#2")      , i, 0)
        grid.addWidget(self.P_2                , i, 1)
        grid.addWidget(self.E_2                , i, 2); i+=1
        grid.addWidget(QtWid.QLabel("#3")      , i, 0)
        grid.addWidget(self.P_3                , i, 1)
        grid.addWidget(self.E_3                , i, 2); i+=1

        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        # fmt: on

        qgrp_readings = QtWid.QGroupBox("Readings")
        qgrp_readings.setLayout(grid)

        vbox = QtWid.QVBoxLayout()
        vbox.addWidget(qgrp_readings)
        vbox.addWidget(
            self.qgrp_legend,
            stretch=0,
            alignment=QtCore.Qt.AlignmentFlag.AlignTop,
        )
        vbox.addWidget(
            qgrp_history,
            stretch=0,
            alignment=QtCore.Qt.AlignmentFlag.AlignTop,
        )
        vbox.addStretch(1)

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

    def link_legend_to_tscurves_E(self):
        """Legend currently only hides/shows the power curves. I'd like to have
        the energy curves follow the visibility of the power curves. We have to
        add them in manually, hence this method."""
        for idx, tscurve_P in enumerate(self.tscurves_P):
            self.tscurves_E[idx].setVisible(tscurve_P.isVisible())

    @Slot()
    def process_qpbt_reset_E(self):
        msgbox = QtWid.QMessageBox()
        msgbox.setIcon(QtWid.QMessageBox.Icon.Information)
        msgbox.setWindowTitle("Reset accumulated energy")
        msgbox.setText(
            "Are you sure you want to reset\n"
            "all accumulated energy to 0 joule?"
        )
        msgbox.setStandardButtons(
            QtWid.QMessageBox.StandardButton.Cancel
            | QtWid.QMessageBox.StandardButton.Ok
        )
        msgbox.setDefaultButton(QtWid.QMessageBox.StandardButton.Cancel)
        reply = msgbox.exec()

        if reply == QtWid.QMessageBox.StandardButton.Ok:
            self.qdev.reset_accumulators()
            # msgbox.setText("Energy is reset to 0.")
            # msgbox.setStandardButtons(QtWid.QMessageBox.StandardButton.Ok)
            # msgbox.exec()

    @Slot(bool)
    def process_qpbt_running(self, state: bool):
        self.qpbt_running.setText("Running" if state else "Paused")
        self.do_update_readings_GUI = state

    @Slot()
    def update_GUI(self):
        str_cur_date, str_cur_time = current_date_time_strings()
        state = self.qdev.dev.state  # Shorthand

        self.qlbl_cur_date_time.setText(f"{str_cur_date}    {str_cur_time}")
        self.qlbl_update_counter.setText(f"{self.qdev.update_counter_DAQ}")
        self.qlbl_DAQ_rate_1.setText(
            f"DAQ: {self.qdev.obtained_DAQ_rate_Hz:.2f} blocks/s"
        )
        self.qlbl_DAQ_rate_2.setText(
            f"DAQ: {self.qdev.obtained_DAQ_rate_Hz * state.capacity:.1f} Hz"
        )
        self.qlbl_recording_time.setText(
            f"REC: {self.qlog.pretty_elapsed()}"
            if self.qlog.is_recording()
            else ""
        )

        self.link_legend_to_tscurves_E()

        if self.do_update_readings_GUI and state.time.is_full:
            self.timestamp.setText(f"{state.time[0]:.1f}")
            self.P_1.setText(f"{np.mean(state.P_1):.2f}")
            self.P_2.setText(f"{np.mean(state.P_2):.2f}")
            self.P_3.setText(f"{np.mean(state.P_3):.2f}")
            self.E_1.setText(f"{state.E_1[-1]:.3f}")
            self.E_2.setText(f"{state.E_2[-1]:.3f}")
            self.E_3.setText(f"{state.E_3[-1]:.3f}")

            if DEBUG:
                tprint("update_chart")

            for tscurve in self.tscurves_all:
                tscurve.update()


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

    ard = WindTurbineArduino(ring_buffer_capacity=15)
    ard.auto_connect()
    ard.turn_on()

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
    app.setWindowIcon(qta.icon("mdi6.wind-turbine", color="black"))
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
        window.tscurves_P[0].extendData(ard.state.time, ard.state.P_1)
        window.tscurves_P[1].extendData(ard.state.time, ard.state.P_2)
        window.tscurves_P[2].extendData(ard.state.time, ard.state.P_3)
        window.tscurves_E[0].extendData(ard.state.time, ard.state.E_1)
        window.tscurves_E[1].extendData(ard.state.time, ard.state.E_2)
        window.tscurves_E[2].extendData(ard.state.time, ard.state.E_3)

        # Add readings to the log
        log.update()

        # Work-around for the jobs thread not getting fairly granted a mutex
        # lock on the device mutex `dev.mutex`. It can sometimes wait multiple
        # lock-unlock cycles of the DAQ thread, before the jobs thread is
        # granted a lock. The `QDeviceIO` library should actually be rewritten
        # slightly to make use of a locking queue in combination with a
        # `QWaitCondition` and `wakeAll()`. ChatGPT.
        QtCore.QThread.msleep(10)

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
        log.write(
            "time [s]\t"
            "P_1 [mW]\tE_1 [J]\t"
            "P_2 [mW]\tE_2 [J]\t"
            "P_3 [mW]\tE_3 [J]\n"
        )

    def write_data_to_log():
        np_data = np.column_stack(
            (
                ard.state.time,
                ard.state.P_1,
                ard.state.E_1,
                ard.state.P_2,
                ard.state.E_2,
                ard.state.P_3,
                ard.state.E_3,
            )
        )
        log.np_savetxt(np_data, "%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f")

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
        ard.turn_off()
        ard.close()

    def about_to_quit():
        print("\nAbout to quit")
        stop_running()

    # --------------------------------------------------------------------------
    #   Start the main GUI event loop
    # --------------------------------------------------------------------------

    window = MainWindow(qdev=ard_qdev, qlog=log)
    window.show()

    ard_qdev.start()
    ard_qdev.unpause_DAQ()

    app.aboutToQuit.connect(about_to_quit)
    sys.exit(app.exec())
