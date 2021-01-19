# WSPR-TX-Config
Configuration tool for the Zachtek WSPR TX products

******************* WARNING *******************
This project is pre-alpha - all source and
distribution files are prone to have severe bugs.

Use at your own risk!
***********************************************

This program roughly follows an MVC method.  More comments on this are in the code.

The program purpose is to allow users of the Zachtek WSPR Transmitters
to graphically configure their devices on:
- MacOS
- Linux
- Windows
- anywhere else Python, PySerial, and tkinter exists

Because of this goal, the features of the GUI are kept to a minimum,
so no additional modules are required for graphics.  Additional
modules may need to be installed on MacOS, but packaging applications
like py2exe and py2app may eliminate the need for the consumer to take 
additional steps.

Required modules:
- tkinter (distributed with Python on MacOS and elsewhere) for the GUI
- pyserial for serial port communications

**************** With Thanks!  ****************
This project is provided with much appreciation for Harry Zachrisson
and his wonderful products at ZachTek.  He provided the information
necessary to make this project possible.

73 de Ken W1OT
