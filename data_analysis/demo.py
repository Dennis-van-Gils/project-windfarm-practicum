#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo on how to read in the log files from the Arduino Wind Farm, and how to
plot the timeseries."""

import numpy as np
import matplotlib.pyplot as plt

from WindFarmData import WindFarmData, COLOR_MAP

# Improve layout of all plots
# plt.style.use("default")
plt.style.use("dark_background")
plt.rcParams["grid.color"] = "gray"
plt.rcParams["font.size"] = 12
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 14

# ------------------------------------------------------------------------------
#   plot_power_timeseries
# ------------------------------------------------------------------------------


def plot_power_timeseries(my_WFD: WindFarmData):
    """Plot the power timeseries for each turbine."""

    fig = plt.figure(figsize=(16, 10), dpi=90)
    fig.suptitle(f"{my_WFD.filename}")

    ax1 = fig.add_subplot(1, 1, 1)
    cm = COLOR_MAP

    marker = "-"
    ax1.plot(my_WFD.time, my_WFD.P_1, marker, color=cm[0], label="Turbine 1")
    ax1.plot(my_WFD.time, my_WFD.P_2, marker, color=cm[1], label="Turbine 2")
    ax1.plot(my_WFD.time, my_WFD.P_3, marker, color=cm[2], label="Turbine 3")
    ax1.plot(my_WFD.time, my_WFD.P_4, marker, color=cm[3], label="Turbine 4")
    ax1.plot(my_WFD.time, my_WFD.P_5, marker, color=cm[4], label="Turbine 5")
    ax1.plot(my_WFD.time, my_WFD.P_6, marker, color=cm[5], label="Turbine 6")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Power (mW)")
    ax1.grid(True)

    fig.legend()

    return fig


# ------------------------------------------------------------------------------
#   plot_power_statistics
# ------------------------------------------------------------------------------


def plot_power_statistics(my_WFD: WindFarmData):
    """Plot statistics on the power per wind turbine. The circles indicate the
    average power and the error bars the standard deviation over all time."""

    fig = plt.figure()
    fig.suptitle(f"{my_WFD.filename}")

    ax1 = fig.add_subplot(1, 1, 1)

    for idx in range(6):
        ax1.plot(
            idx + 1,
            my_WFD.avg_P[idx],
            marker="o",
            markersize=12,
            color=COLOR_MAP[idx],
            label=f"Turbine {idx + 1}",
        )
        ax1.errorbar(
            idx + 1,
            my_WFD.avg_P[idx],
            yerr=my_WFD.std_P[idx],
            capsize=10,
            linewidth=2,
            color=COLOR_MAP[idx],
        )

    ax1.set_xlabel("Turbine #")
    ax1.set_ylabel("Average power (mW)")
    ax1.grid(True)

    fig.legend(loc="outside right upper")
    plt.tight_layout()

    return fig


# ------------------------------------------------------------------------------
#   main
# ------------------------------------------------------------------------------

if __name__ == "__main__":

    # Read in Wind Farm Data from a log file on disk
    data_1 = WindFarmData("demo_log.txt")

    # Print statistics
    for i in range(6):
        print(
            f"Power turbine {i + 1} [mW]: "
            f"{data_1.avg_P[i]:.3f} +/- "
            f"{data_1.std_P[i]:.3f}"
        )

    # Plot
    fig_1 = plot_power_timeseries(data_1)
    fig_2 = plot_power_statistics(data_1)

    # Save the plots to images on disk
    fig_1.savefig("demo_log_fig_1.png", dpi=120)
    fig_1.savefig("demo_log_fig_1.pdf")
    fig_2.savefig("demo_log_fig_2.png", dpi=120)
    fig_2.savefig("demo_log_fig_2.pdf")

    # Show all plots on screen
    plt.show()
