# WSPR-TX-Config
Configuration tool for the Zachtek WSPR TX products

******************* WARNING *******************

This project is beta - all source and
distribution files are prone to have bugs.

*Use at your own risk!*

***********************************************

Distribution files are available in dist/ for some environments.

For the Windows version, please install the CH34x driver, or the program will
refuse to run.  If running from the source code, please install Python from
the official Python distribution, and not the Windows provided distribution from
Microsoft, which is incomplete.  Also if running the source Python code dirrectly,
remember to install PySerial (ie python3 -m pip install PySerial).

On some machines, you may find a conflicting and incompatible Python
module also called "serial".  If this is encountered, remove "serial"
and then install PySerial.

The source should work for python2 and python3, but this has only been
"lightly" tested so far, and only on the latest versions of MacOS, Windows,
and CentOS.

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
