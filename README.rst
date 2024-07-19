.. image:: https://img.shields.io/github/v/release/Dennis-van-Gils/project-windfarm-practicum
    :target: https://github.com/Dennis-van-Gils/project-windfarm-practicum
    :alt: Latest release
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
.. image:: https://img.shields.io/badge/License-MIT-purple.svg
    :target: https://github.com/Dennis-van-Gils/project-windfarm-practicum/blob/master/LICENSE.txt

Wind farm practicum
===================
*This project is part of the minor course "Sustainable Energy" of the University of Twente, The Netherlands, hosted by the Physics of Fluids and the Engineering Fluid Dynamics research groups.*

It involves a practicum on wind farm dynamics, where up to 6 scale model wind
turbines of 1:87 scale will be placed in a wind tunnel facility. The electrical
power output and accumulated energy of each turbine - here, a DC motor used as a
dynamo - will be monitored and logged over time by an Arduino with a graphical
user interface programmed in Python. The goal for the students is to investigate
different grid layouts of the turbines and how their down-wind wakes can affect
each other.

- Github: https://github.com/Dennis-van-Gils/project-windfarm-practicum

.. image:: https://github.com/Dennis-van-Gils/project-windfarm-practicum/blob/main/docs/photos/full_setup_2.jpg

.. image:: https://github.com/Dennis-van-Gils/project-windfarm-practicum/blob/main/docs/screenshots/screenshot.png

Hardware
========
* 1x Microcontroller: Adafruit #3800 - Adafruit ItsyBitsy M4 Express (ATSAMD51 Cortex M4)
* 6x Power monitor: Adafruit #5832 - Adafruit INA228 I2C 85V, 20-bit High or Low Side Power Monitor
* 2x Stemma QT 5 Port Hub: Adafruit 5625
* 6x Scale model wind turbine: Sol Expert 40004 H0 (1:87 scale)

The electronic diagram can be found at
`docs/electronic_diagram.pdf <https://github.com/Dennis-van-Gils/project-windfarm-practicum/blob/main/docs/electronic_diagram.pdf>`_.

Photos of the circuit board can be found at
`docs/photos <https://github.com/Dennis-van-Gils/project-windfarm-practicum/blob/main/docs/photos>`_.

Instructions
============
Download the `latest release <https://github.com/Dennis-van-Gils/project-windfarm-practicum/releases/latest>`_
and unpack to a folder onto your drive.

Flashing the firmware
---------------------

Double click the reset button of the Feather while plugged into your PC. This
will mount a drive called `FEATHERBOOT`. Copy
`src_mcu/_build_ItsyBitsy_M4/CURRENT.UF2 <https://github.com/Dennis-van-Gils/project-windfarm-practicum/raw/main/src_mcu/_build_ItsyBitsy_M4/CURRENT.UF2>`_
onto the Featherboot drive. It will restart automatically with the new firmware.

Running the application
-----------------------


Prerequisites
~~~~~~~~~~~~~

| Preferred distribution: Anaconda full or Miniconda

    * `Anaconda <https://www.anaconda.com>`_
    * `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_

Open `Anaconda Prompt` and navigate to the unpacked folder. Run the following to
install the necessary packages:

::

   cd src_python
   conda create -n wind -c conda-forge --force -y python=3.12
   conda activate wind
   pip install -r requirements.txt

Now you can run the graphical user interface.
In Anaconda prompt:

::

   conda activate wind
   python main.py


LED status lights
=================

The RGB LED of the ItsyBitsy M4 will indicate its status:

* Blue : Setting up microcontroller
* Green: All okay and idling
* Orange: Acquiring and sending data
