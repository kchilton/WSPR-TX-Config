#!/usr/bin/env python
#
# Copyright 2021 Kendell Chilton
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
##############################################################################
#    GUI based on the design by Harry Zachrisson for the WSPR_TX_Config      #
#                   for Microsoft Windows platforms.                         #
##############################################################################
#
#
#########################################################################################################################################################
# NOTES:
#
# **** Enhancement ideas ****
#   Add more command line options for batch configuration
#   Additional checks for user input (e.g. valid callsign) and error-proofing of the device comms
#   An option to save the selected port name to a startup file for automatic selection
#   Verification and correction of the RTS control, which may be causing a device reset on connect
#   Additional WSPR features: random pause, random band selection, local tx logs, antenna/device selection
#   Live update of port availability -- currently cannot detect new ports added since start
#   Change the color (grey) of the UTC clock when GPS updates are not happening
#   Direct entry of the frequency on the Signal Generator tab
#   Programmable frequency sequencing for the signal generator
#   Factory reset option?  Device firmware download option?
#   Qt support, for nicer graphics on platforms that have it installed
#   Event driving capability: set host system clock, device status notification (e.g. if it dies, loses lock)
#   Internationalization of the text fields
#
#########################################################################################################################################################

"""Configuration GUI for ZachTek WSPR devices

This program roughly follows an MVC method.  More comments on this are later in the code.

The program purpose is to allow users of the Zachtek WSPR Transmitters
to graphically configure their devices on:
- MacOS
- Linux
- Windows
- anywhere else Python, PySerial, and tkinter exists

Because of this goal, the features of the GUI are kept to a minimum,
so no additional modules are required for graphics.  Additional
modules may need to be installed on MacOS, but packaging applications
like py2exe may eliminate the need for the consumer to take additional
steps.

Required modules:
- tkinter (distributed with Python on MacOS) for the GUI
- pyserial for serial port communications

Required additional files:
- LP1 Icon.gif the icon image for the program
- 1011.gif the image of ZachTek model 1011 (WSPR TX LP1)
- 1012.gif the image of ZachTek model 1012 (WSPR TX Desktop)
- 1017.gif the image of ZachTek model 1017 (WSPR TX mini)
- unknown.gif the image to display when the model is unknown

Structure of the code:
   Python preliminaries - items needed to get python started
   CreateToolTip() - a class for creating tool tips on widgets
   CreateCanvasTip() - a class for creating tool tips on tags within a canvas
   CreateButton() - a class to provide an info button with tooltip and popup
   MC() - a mirror clock, because the GPS time reports are not constant
   Model() - contains the logic needed to work with the device
   View() - contains the tkinter GUI
   Controller() - ties together the Model and View and runs the app
   main() - the python code that instatiates and boots the app
   the code to call main() - idiomatic Python

"""

###############################################################################
##### Python preliminaries
###############################################################################
#
# Python needs a bit of setup before entering the MVC structure, even before
# we get to main(). This includes importing some libraries to interact with
# the platform, os, tkinter, etc.
#
# Currently, we support both Python 2.x (mainly for MacOS) and Python 3.x
#
VERSION = "0.0.0.5"  ### Extreme Alpha Version

import sys     # system hooks
import os      # operating system hooks
import stat    # to check file types
import math    # for calculation of the GPS plot
import getopt  # command line option processing
import serial  # serial port (tty) routines

# tkinter is named differently in 2.x vs 3.x
if sys.version_info[0] < 3:
    from Tkinter import *
    import ttk
    python = 2
else:
    from tkinter import *
    from tkinter import ttk
    python = 3

class CreateToolTip(object):
    """
    Creates tooltips for widgets
    """
    def __init__(self, widget, text):
        self._widget = widget
        self._text = text
        self._popup = None
        self._widget.bind("<Enter>", self._enter)
        self._widget.bind("<Leave>", self._leave)
        self._widget.bind("<ButtonPress>", self._leave)
        
    def _enter(self, event=None): 
        self._popup = Toplevel(self._widget)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry("+%d+%d" % (self._widget.winfo_pointerx(),
                                            self._widget.winfo_pointery() + 20))
        try:
            self._popup.tk.call("::tk::unsupported::MacWindowStyle", "style",
                             self._popup._w, "help", "noActivates")
        except TclError:
            pass
        self._popup.update_idletasks()
        self._popup.lift()
        Label(self._popup, text=self._text, justify='left', font=('Arial',12),
              background="#ffffff", relief='solid', borderwidth=1,
              wraplength = 360).pack(ipadx=2)
        
    def _leave(self, event=None):
        _p = self._popup
        self._popup= None
        if _p:
            _p.quit()
            _p.destroy()
            _p.update_idletasks()


class CreateCanvasTip(object):
    """
    Creates tooltips for items inside a canvas
    """
    def __init__(self, canvas, tag, text='item info'):
        self._canvas = canvas
        self._tag = tag
        self._text = text
        self._popup = None
        self._canvas.tag_bind(self._tag,"<Enter>", self._enter)
        self._canvas.tag_bind(self._tag,"<Leave>", self._leave)
        self._canvas.tag_bind(self._tag,"<ButtonPress>", self._leave)

    def _enter(self, event=None):
        self._popup = Toplevel(self._canvas)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry("+%d+%d" % (self._canvas.winfo_pointerx(),
                                            self._canvas.winfo_pointery() + 20))
        try:
            self._popup.tk.call("::tk::unsupported::MacWindowStyle", "style",
                                self._popup._w, "help", "noActivates")
        except TclError:
            pass
        self._popup.update_idletasks()
        self._popup.lift()
        Label(self._popup, text=self._text, justify='left', font=('Arial',12),
              background="#ffffff", relief='solid', borderwidth=1,
              wraplength = 180).pack(ipadx=1)

    def _leave(self, event=None):
        _p = self._popup
        self._popup= None
        if _p:
            _p.quit()
            _p.destroy()
            _p.update_idletasks()

class CreateInfoButton(object):
    """
    Creates info buttons that display tooltips when hovering and popups when clicked
    """
    def __init__(self, widget, text, info, bg):
        self._widget = widget
        self._text = text
        self._info = info
        self._popup = None
        self._b = BitmapImage(data="""
        #define info_width 16
        #define info_height 16
        static unsigned char info_bits[] = {
        0xe0, 0x03, 0x18, 0x0c, 0x04, 0x10, 0x82, 0x20, 0x02, 0x20, 0x81, 0x40,
        0x81, 0x40, 0x81, 0x40, 0x81, 0x40, 0x81, 0x40, 0x82, 0x20, 0x82, 0x20,
        0x04, 0x10, 0x18, 0x0c, 0xe0, 0x03, 0x00, 0x00};
        """,foreground="black", background=bg)
        self._iCircle = Label(widget, image=self._b, bg=bg)
        self._iCircle.bind("<Enter>", self._enter)
        self._iCircle.bind("<Leave>", self._leave)
        self._iCircle.bind("<ButtonPress>", self._pop)

    def grid(self, **args):
        self._iCircle.grid(args)

    def place(self,**args):
        self._iCircle.place(args)

    def _pop(self, event=None):
        self._infoWin = Tk()
        self._infoWin.configure(background='white')
        self._infoWin.wm_title("Information")
        self._f = Frame(self._infoWin, bg='white', bd=0)
        self._f.pack(padx=20,pady=20,fill=BOTH,expand=True)
        self._d = Canvas(self._f, width = 40, height = 40, borderwidth = 0, highlightthickness = 0, bg = 'white')
        self._d.create_oval(0, 0, 36, 36, outline = 'blue', fill = 'blue')
        self._d.create_text(18, 18, text = 'i', font=('Arial',18), fill='white')
        self._d.pack(side=LEFT, anchor=NE, pady=10, padx=10)
        Label(self._f, text=self._info, font=('PT Mono',12), bg='white', justify='left').pack(pady=10, padx=20,side=TOP,fill=X)
        Button(self._infoWin, text="Okay", command = self._infoWin.destroy, bg = 'grey80', font = ('Arial', 18)).pack(side=RIGHT,fill=None,padx=10,pady=10)
        self._infoWin.mainloop()
        
    def _enter(self, event=None):
        self._popup = Toplevel(self._iCircle)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry("+%d+%d" % (self._iCircle.winfo_pointerx(),
                                            self._iCircle.winfo_pointery() + 20))
        try:
            self._popup.tk.call("::tk::unsupported::MacWindowStyle", "style", self._popup._w, "help", "noActivates")
        except TclError:
            pass
        self._popup.update_idletasks()
        self._popup.lift()
        Label(self._popup, text=self._text, justify='left', font=('Arial',12),
              background="#ffffff", relief='solid', borderwidth=1,
              wraplength = 640).pack(ipadx=1)

    def _leave(self, event=None):
        _p = self._popup
        self._popup= None
        if _p:
            _p.quit()
            _p.destroy()
            _p.update_idletasks()

            
# Mirror Clock - a Class used by the View
#
# Because the WSPR device stops updating the GPS clock while
# transmitting, a solution is needed to keep the UTC clock display
# going. This is a weakly disciplined timer, syncronized to the GPS
# clock updates, but continues to run with kicks from the Tk timer
# every 1.005 seconds if a GPS update does not occur before the timer
# expires.  For the <2 minutes each transmit sequence takes, this is
# sufficiently accurate, because this is just for human display and is
# not driving any critical systems.
#
class MC():
    """
    The Mirror Clock keeps time

    The clock can be Set, and can be read
    The clock pushes the current time *directly* to the controller as a periodic event
    """
    def __init__(self, root, clock):
        self._hour = 0
        self._minute = 0
        self._second = 0
        self._job = None
        self._root = root
        self._clock = clock

    def __tick(self):
        self._second += 1
        if self._second > 59:
            self._second = 0
            self._minute += 1
            if self._minute > 59:
                self._minute = 0
                self._hour += 1
                if self._hour > 23:
                    self._hour = 0

        # This is ugly, but we need to push the time
        self._clock.set("{0:02d}:{1:02d}:{2:02d}".format(self._hour,self._minute,self._second))
        self._job = self._root.after(1005,self.__tick)

    @property
    def time(self):
        return "{0:02d}:{1:02d}:{2:02d}".format(self._hour,self._minute,self._second)

    @time.setter
    def time(self,data):
        if self._job is not None:
            self._root.after_cancel(self._job)
        try:
            _h,_m,_s = data.split(':')
        except ValueError:
            return -1
        self._hour, self._minute, self._second = int(_h),int(_m), int(_s)
        self._job = self._root.after(1005,self.__tick)

###############################################################################
##### Model
###############################################################################
#
# A "Model" in MVC is theoretically where the logic of the program's
# function is implemented, along with its data and state.  The Model
# is independent of the user interface, allowing changes to the GUI
# without a need to modify this core logic, and also independent of
# the actual application logic, which resides in the Controller.  The
# Model provides the program with its core functions, which for
# different use cases has different meaning.  For many programs, the
# Model implements business logic and workflows.
#
# The Model receives input from the Controller as events, such as user
# input, occur. It also can provide status upon inquiry, either to the
# Controller or the View.  Most implementations of MVC do not allow
# direct communications between the Model and the View, but require
# them to pass through the Controller. Some interpretations of MVC
# allow the View to query the Model for data to display.  Here, some
# data can be queried directly by the View from the Model using the
# public functions.
#
# In this implementation, the Model data and state on the device must
# be queried via Model() to the WSPR device. The Model really is the
# device (the ZachTek WSPR transmitter), and Model() implements
# functions to manage a particular set of such devices connected via
# serial (and maybe in the future, USB) ports.  Model() also holds
# some data about the device and the communication with it.  Commands
# from the Controller are made synchronous, as Model() ensures that
# some of the communications actions are succesful (like receiving a
# whole line), but checking the infomation received is left to the
# Controller, as is typical in MVC -- so retries are driven from the
# Controller. The Controller must poll for asynchonous events from the
# Model, as well as any responses to commands the Contoller sends.
#
class Model(object):
    """
    The Model for the MVC implementation

    The model has these exported functions:
        portName               - when assigned, sets the serial port to the name given
                                 when read, provides the serial port name
        getPorts()             - returns a [list] of serial ports found on the machine
        readPort()             - polls for a line of data from the port
                                 returns the stripped line of data from the port
        sendPort(command,data) - sends a WSPR TX formatted command to the port
    """
    def __init__(self, Controller):
        self._vc = Controller   # I need to know the Controller to call notification functions
        self._serialPort = 'None' # "None" is a flag that means we have not set it, yet.
        self._serials = []      # The list of serial ports found on the machine
        self._fd = None         # File descriptor of the open port
        
        # The first thing to do is to discover what serial ports are available on this system
        _ports=[]
        if sys.platform.startswith('win'):
            _ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            for _name in os.listdir('/dev'):
                if _name.startswith('tty') and ( len(self.name) > 3 ):
                    if self.name[3].isalpha():
                        _ports.append('/dev/'+_name)
        elif sys.platform.startswith('darwin'):
            for _name in os.listdir('/dev'):
                if _name.startswith('cu.'):
                    _ports.append('/dev/'+_name)
                if _name.startswith('ttyS'):
                    _ports.append('/dev/'+_name)
        else:
            sys.stderr.write('OS unknown - cannot find ports')
            self._serialPort = 'None'
            sys.exit(1)

        # Test the possible ports and add them to the list (mainly for Windows)
        self._serials = []
        for _p in _ports:
            try:
                _s = serial.Serial(_p)
                self._serials.append(_p)
                _s.close()
            except:
                pass
        if len(self._serials) < 1:
            sys.stderr.write('No serial ports found.')
            sys.exit(1)

    def getPorts(self): # Only used by the View to create a selector of possible ports
        return self._serials

    @property
    def portName(self):
        return self._serialPort

    @portName.setter
    def portName(self,name):
        if self._serialPort != 'None':
            self._fd.close()
        self._serialPort = name
        if name == 'None':
            return
        try:
            self._fd = serial.Serial(port = self._serialPort, baudrate = 9600, bytesize = serial.EIGHTBITS,
                                     parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE,
                                     xonxoff = False, rtscts = False, dsrdtr = None, timeout = 1)
        except OSError:
            sys.stderr.write('Port in use?')
            self._serialPort = 'None'

    def readPort(self):
        if self._serialPort == 'None':
            return ''
        _ch = _buff = ''
        _count = 0
        if self._fd.in_waiting < 1:
            return ''
        while _count < 1000000:
            _count += 1
            if python == 2:
                _ch = self._fd.read(1)
            else:
                _ch = str(self._fd.read(1), 'ascii')
            if len(_ch) < 1: continue
            if _ch in '\r\n': break
            _buff = _buff + _ch
        if len(_buff) < 1:
            return ''
        if _buff[0] != '{':
            return ''
        return _buff.rstrip()
            
    def sendPort(self, cmd, data):
        if len(cmd)>0:
            _buff = '['+cmd+'] '+data
        else:
            _buff = data
        self._vc.view.traceInsert(_buff)
        if len(cmd)>0: _buff = _buff+'\r\n'
        if python == 3:
            _buff = str.encode(_buff)
        self._fd.write(_buff)

    # Device (WSPR TX) specific items
    def bands(self):
        return ['2190m', '630m', '160m', '80m', '40m', '30m', '20m', '17m',
                '15m', '12m', '10m', '6m', '4m', '2m', '70cm', '23cm']

    def powers(self):
        return [ '0',  '3',  '7', '10', '13', '17',
                '20', '23', '27', '30', '33', '37',
                '40', '43', '47', '50', '53', '57', '60']
        
###############################################################################
##### View
###############################################################################
#
# The "View" is responsible to create an interface to the user, in this case
# via a GUI.  The View can be re-written independently of the Model and
# Controller to implement another GUI framework.
#
# This class is implemented to use tkinter (TK) since that is readily
# available on practically all machines where Python is found. It is
# the default GUI interface for Python.  The decision as to which View
# to select is made in main(), where Qt or another GUI framework could
# be selected.
#
# The View ideally should only output to the user.  User input from
# tkinter is redirected to the Controller. This requires the use of
# the "command" options on many input elements to involke the
# appropriate functions to handle user input, or other methods (like
# trace) to inform the Controller of changes intended by the user.
#
# A View may gather data from the Model or receive it from the
# Controller to output on the display.  In this implementation, input
# to View() from the Controller is not needed to provide view
# selection, since the only view selection is the tab selection
# handled internally to tkinter, and scrollbars.  In addition,
# time-based updates to the view that are driven by tkinter, such as
# the time clock, and remain within the View.  Input from the
# Contoller include real-time changes originating from the Model and
# responses to the View as a result of validating user selections.
# View() also reads some data directly from the Model, which
# simplifies that interface.
#
class View():
    """
    Tkinter View implemenetation
    """
    def __init__(self, Controller):
        self.vc = Controller

        self.points = []       # for satellite positions
        self.tabbg = '#D9E4F1' # background color for the tabbed left frame

        self.root = Tk()
        self.root.resizable(0, 0)
        self.root.title('ZachTek WSPR Transmitter Configuration')
        self.logo = PhotoImage(file = 'LP1 Icon.gif')
        self.root.tk.call('wm','iconphoto',self.root._w,self.logo)
        self.root.configure(background='white')

        self.style = ttk.Style(self.root)
        self.style.theme_use('classic')
        self.style.theme_create( 'WSPR', parent = 'clam', settings = {
            'TNotebook': {'configure': {'tabmargins': [2, 5, 2, 0],
                                        'background': 'white'} },
            'TNotebook.Tab': {
                'configure': {'padding': [5, 1], 'background': self.tabbg },
                'map':       {'background': [('selected', self.tabbg)],
                              'expand': [('selected', [1, 1, 1, 0])] } },
            'TFrame': {'configure': {'background':self.tabbg} },
            'TProgressbar': {'configure': {'troughcolor':'#FFFFFF', 'background':'green'}},
        } )
        self.style.theme_use('WSPR')

        self.name        = StringVar()  # set name or information
        self.hardwareVer = StringVar()  # hardware version
        self.hardwareRev = StringVar()  # hardware revision
        self.firmwareVer = StringVar()  # firmware version
        self.firmwareRev = StringVar()  # firmware revision
        self.frequency   = StringVar()  # current output frequency
        self.signal      = IntVar()     # GPS signal strenth (percentage)
        self.curtime     = StringVar()  # Current time being displayed
        self.position    = StringVar()  # Current GPS Maidenhead
        self.debug       = IntVar()     # Debug checkbox setting
        self.rxChars     = IntVar()     # Number of characters received on the port
        self.sendCommands = StringVar() # Command string to send in debug mode
        self.CRLF        = IntVar()     # CR/LF checkbox setting
        self.pauseTime   = IntVar()     # Number of seconds to pause between transmit cycles
        self.pausepercent = IntVar()    # Percentage progress of the pause part of the cycle
        self.call        = StringVar()  # Amateur radio callsign
        self.rpam        = StringVar()  # Selection of Automatic or Manual reported position
        self.location    = StringVar()  # User-selected position entry
        self.rpmode      = StringVar()  # Selection of Altitude or Power reporting
        self.rpwr        = StringVar()  # Selected output power to be reported
        self.d100M       = IntVar()     # 100MHz digit for the signal generator
        self.d10M        = IntVar()     # 10MHz digit for the signal generator
        self.d1M         = IntVar()     # 1MHz digit for the signal generator
        self.d100k       = IntVar()     # 100kHz digit for the signal generator
        self.d10k        = IntVar()     # 10kHz digit for the signal generator
        self.d1k         = IntVar()     # 1kHz digit for the signal generator
        self.d100Hz      = IntVar()     # 100Hz digit for the signal generator
        self.d10Hz       = IntVar()     # 10Hz digit for the signal generator
        self.d1Hz        = IntVar()     # 1Hz digit for the signal generator
        self.d10c        = IntVar()     # 10cHz digit for the signal generator
        self.d1c         = IntVar()     # 1cHz digit for the signal generator
        self.boot        = StringVar()  # User selection of boot mode
        self.portName    = StringVar()  # User setting of port name (may not be the one in use)
        self.currentPort = StringVar()  # The current port Model() is using for comms
        
        self.mirror = MC(self.root,self.curtime) # Instantiate the Mirror clock

        self._bands  = self.vc.model.bands()   # get info from Model
        self._powers = self.vc.model.powers()  # band config and power levels

        ################################################################
        # Text for the information popup boxes
        ################################################################
        _tips1 = '''
        The Signal Generator outputs a constant signal on the chosen frequency.
        This is useful in a number of applications, like for example to measure SWR
        or field strength of antennas.
        If the boot configuration is set to signal generator, it can be unplugged after
        setting and saving the frequency.  It can then be used standalone with a
        phone charger or power bank.
        This will in effect make it a mobile signal generator that will start up on the
        same frequency whenever it gets power.
        The signal generator will use any interal Low Pass filters in the transmitter to
        get the cleanest signal.
        In case there are no low pass filters fitted, the output signal will be square
        wave with lots of overtones that can be used up to the UHF range.
        The frequency accuracy is 2.5ppm or better for the WSPR Desktop and LP1
        models and 10ppm for the WSPR Mini.
        The actual accuracy can be a lot better than this due to frequency calibration
        saved in EEPROM.
        For example, the WSPR Desktop oputputting a 10MHz signal will often not be
        off more than a couple of Hertz.'''
        _tipb1 = '''
        A green square indicates that a Low Pass filter is fitted
        in this transmitter for this band.

        This serves as a reminder as to what band is OK to
        transmit on.
        However, nothing has been done to prevent the user
        to transmit on any band regardless of
        what filters are fitted or not.
        This is by design to give the maximum freedom for the
        user in case the transmitter is modified or if external
        filters are used, etc.
        '''
        _tipb2 = '''
        The band tick-boxes determine what bands the WSPR Beacon will transmit on.

        The frequency used will be somewhere within the 200Hz wide area used by WSPR on each
        amateur band.
        The modulation only occupies a few Hz in this 200Hz and the actual frequency is randomized
        before each transmission
        Using a random frequency minimizes the chances of tansmitting on top of another user for
        extended periods.
        The center frequency for the 200Hz WSPR area for all bands is shown below.

        2190m       137.500kHz
         630m       475.700kHz
         160m     1.838 100MHz
          80m     3.570 100MHz
          40m     7.040 100MHz
          30m    10.140 200MHz
          20m    14.097 100MHz
          17m    18.106 100MHz
          15m    21,096 100MHz
          12m    24.926 100MHz
          10m    28.126 100MHz
           6m    50.294 500MHz
           4m    70.092 500MHz

        As mentioned above, the actual frequency used is randomized +/- 100Hz.
        The status area will show the current frequency used, the modulation frequency shift can also be
        observed here when the beacon is running.

        If a fixed frequency is needed, a special firmware has to be used and can be provided by
        contacting ZachTek.
        '''
        _tipb3 = '''
        This option sets an optional delay afte the WSPR beacon has run
        for one pass.
        The delay is in seconds and can be set from 0 to 99999.
        The delay will come into effect after all enabled bands have been
        transmitted on once.

        By pausing the transmitter, we provide space on the bands for
        other users.
        This delay is especially important if only a single band is enabled.
        For since band operation, I would recommend an 8 minute delay
        (480 seconds).
        As more bands are enabled, this delay can be lowered.
        If four bands or more are enabled for transmission, the delay can be
        set to 0.
        While this pause is running, the pause can be seen in the
        pause progess bar.
        However, in the WSPR Mini, the entire Microcontroller is put to
        sleep if the delay is more than 60 seconds.
        This means that the pause progress may not be visible if the
        transmitter is an WSPR Mini.
        '''
        _tipb4 = '''
        This option will encode the altitude into the power information bits.

        Every 3dB is 900 meters of altitude, so:
             0dBm (0.001W) means the altitude is between 0 and 900m
             3dBm (0.002W) is  900m to 1800m
             7dBm (0.005W) is 1800m to 2700m
            10dBm (0.010W) is 2700m to 3600m
            etc.
            60dBm ( 1000W) is 18km or higher

        The transmitter must have firmware version 0.81 or higher to
        support this.
        This option is mostly meant to be used by the WSPR Pico model in
        balloon flight applications.'''

        ###################################################
        # Top Level
        ###################################################
        #                                                 #
        #  Layout scheme:                                 #
        #                                                 #
        #  +-tabs----------------+ +-right-------------+  #
        #  |                     | | +-r1------------+ |  #
        #  |   tab1 -WSPR beacon | | |               | |  #
        #  |   tab2 -Signal Gen  | | +---------------+ |  #
        #  |   tab3 -Boot config | | +-r2---+ +-r3---+ |  #
        #  |   tab4 -Port select | | |      | |      | |  #
        #  |                     | | |      | |      | |  #
        #  |                     | | |      | |      | |  #
        #  |                     | | |      | |      | |  #
        #  |                     | | |      | |      | |  #
        #  |                     | | |      | |      | |  #
        #  |                     | | |      | |      | |  #
        #  |                     | | +------+ +------+ |  #
        #  +---------------------+ +-------------------+  #
        #  +-bl------------------+ +-br----------------+  #
        #  |                     | |                   |  #
        #  |                     | |                   |  #
        #  +---------------------+ +-------------------+  #
        #  +-f0----------------------------------------+  #
        #  |                                           |  #
        #  |                                           |  #
        #  +-------------------------------------------+  #
        #                                                 #
        ###################################################

        ###################################################
        ###################################################
        # Left side is Notebook tabs
        ###################################################
        ###################################################
        self.tabs = ttk.Notebook(self.root, padding = [0,0,0,0])
        self.tab1 = ttk.Frame(self.tabs, borderwidth = 0, relief = 'flat')
        self.tab2 = ttk.Frame(self.tabs, borderwidth = 0, relief = 'flat')
        self.tab3 = ttk.Frame(self.tabs, borderwidth = 0, relief = 'flat')
        self.tab4 = ttk.Frame(self.tabs, borderwidth = 0, relief = 'flat')
        self.tabs.add(self.tab1, text = 'WSPR Beacon', state = 'disabled')
        self.tabs.add(self.tab2, text = 'Signal Generator', state = 'disabled')
        self.tabs.add(self.tab3, text = 'Boot Configuration', state = 'disabled')
        self.tabs.add(self.tab4, text = 'Serial Port')
        self.tabs.grid(row = 0, column = 0, columnspan = 2, sticky = W+N+S, padx = 5, pady = 5)
        #self.tabs.select(self.tab4) Don't need to select it, since it is the only one enabled.
        #                            Maybe later can add auto switching to the boot selection
        #                            if the port is remembered from prior saves

        ###################################################
        ###################################################
        # Right side frame set
        ###################################################
        ###################################################
        self.right = Frame(self.root, padx = 5, bg='white')
        self.right.grid(row = 0, column = 2, sticky = N+S)
        self.r1 = Frame(self.right, bg='white')
        self.r1.grid(row = 0, column = 0, sticky = W+N+E, columnspan = 2)
        self.r2 = Frame(self.right, relief = 'ridge', bd = 2, bg='white')
        self.r2.grid(row = 2, column = 0, sticky = N+S, pady = 10)
        self.r3 = Frame(self.right, relief = 'ridge', bd = 2, bg='white')
        self.r3.grid(row = 2, column = 1, sticky = N+S, padx = 10, pady = 10)

        ###################################################
        # r1 - User set name or information
        ###################################################
        ttk.Label(self.r1, anchor = SW, font = ('Arial', 12), text = 'User set name or information',
                  background = 'white', justify = LEFT).grid(row = 0, column = 0, sticky = W+N+E, padx=5)
        self.r1f1 = Frame(self.r1, relief = 'ridge', bd=2, bg='white')
        self.r1f1.grid(row = 1, column = 0, sticky = W+N+E, padx=2)
        self.name.set('')
        self.r1e1 = Entry(self.r1f1, width = 48, textvariable = self.name, font = ('Arial', 18), justify = LEFT, relief='flat')
        self.r1e1.grid(row = 0, column = 0, sticky = W+N+E)
        self.name.trace('w', self.vc.nameUpdate)
        CreateToolTip(self.r1e1,'Give this transmitter a useful name.')
        
        ###################################################
        # r2 - Device Status
        ###################################################
        #### r2f0 - top frame set: photo, hardware and firmware version info    
        self.r2f0 = Frame(self.r2, bd = 0, width = 180, bg='white')
        self.r2f0.grid(row = 0, column = 0, sticky = W+N, padx = 10)
        self.frequency.set('0 000 000.00')
        self.r2l1 = ttk.Label(self.r2f0, anchor = SW, font = ('Arial', 24), text = 'Device Status', background = 'white', justify = LEFT)
        self.r2l1.grid(row = 0, column = 0, sticky = W+S, columnspan = 4, padx = 10, pady = 2)
        self.unknown = PhotoImage(file = 'unknown.gif')
        self.img1011 = PhotoImage(file = '1011.gif')
        self.img1012 = PhotoImage(file = '1012.gif')
        self.img1017 = PhotoImage(file = '1017.gif')
        self.deviceName = 'Device not loaded'
        self.image = Label(self.r2f0, image = self.unknown, text = 'Device not loaded', compound = CENTER, wraplength = 50, fg = 'red', bg='white')
        self.image.grid(row = 1, column = 0, sticky = W+N+E+S, rowspan = 4, padx = 10)
        self.image.ttp = CreateToolTip(self.image,self.deviceName)
        self.r2l2 = ttk.Label(self.r2f0, anchor = SW, font = ('Arial', 18), text = 'Hardware', background = 'white', justify = LEFT)
        self.r2l2.grid(row = 1, column = 1, sticky = W+S+E, columnspan = 3)
        self.r2l3 = ttk.Label(self.r2f0, anchor = NE, font = ('Arial', 18), textvariable = self.hardwareVer, background = 'white', justify = RIGHT)
        self.r2l3.grid(row = 2, column = 1, sticky = E+N)
        CreateToolTip(self.r2l3,'Hardware version')
        self.r2l4 = ttk.Label(self.r2f0, anchor = N, font = ('Arial', 18), text = '.', background = 'white', justify = CENTER)
        self.r2l4.grid(row = 2, column = 2, sticky = N)
        self.r2l5 = ttk.Label(self.r2f0, anchor = NW, font = ('Arial', 18), textvariable = self.hardwareRev, background = 'white', justify = LEFT)
        self.r2l5.grid(row = 2, column = 3, sticky = W+N)
        CreateToolTip(self.r2l5,'Hardware revision')
        self.r2l6 = ttk.Label(self.r2f0, anchor = SW, font = ('Arial', 18), text = 'Firmware', background = 'white', justify = LEFT)
        self.r2l6.grid(row = 3, column = 1, sticky = W+S+E, columnspan = 3)
        self.r2l7 = ttk.Label(self.r2f0, anchor = NE, font = ('Arial', 18), textvariable = self.firmwareVer, background = 'white', justify = RIGHT)
        self.r2l7.grid(row = 4, column = 1, sticky = E+N)
        CreateToolTip(self.r2l7,'Software version - Major')
        self.r2l8 = ttk.Label(self.r2f0, anchor = N, font = ('Arial', 18), text = '.', background = 'white', justify = CENTER)
        self.r2l8.grid(row = 4, column = 2, sticky = N)
        self.r2l9 = ttk.Label(self.r2f0, anchor = NW, font = ('Arial', 18), textvariable = self.firmwareRev, background = 'white', justify = LEFT)
        self.r2l9.grid(row = 4, column = 3, sticky = W+N)
        CreateToolTip(self.r2l9,'Software version - Minor')
        
        #### r2f1 - Frequency label frame set
        self.r2f1 = LabelFrame(self.r2, font = ('Arial', 14), text = 'Current output frequency', background = 'white', width = 180)
        self.r2f1.grid(row = 1, column = 0, sticky = W+N+E, pady = 10, padx = 10)
        self.r2l6 = ttk.Label(self.r2f1, anchor = SE, font = ('Arial', 24), textvariable = self.frequency, background = 'white', justify = RIGHT)
        self.r2l6.grid(row = 0, column = 0, sticky = E+S, padx = 10)
        self.r2l7 = ttk.Label(self.r2f1, anchor = N, font = ('Arial', 16), text = 'MHz    kHz     Hz  ', background = 'white', justify = CENTER)
        self.r2l7.grid(row = 1, column = 0, sticky = E+N, padx = 45)

        #### r2f2 - Transmitter label frame set
        self.r2f2 = LabelFrame(self.r2, font = ('Arial', 16), text = 'Transmitter output', background = 'white')
        self.r2f2.grid(row = 2, column = 0, sticky = W+N+E, pady = 5, padx = 10)
   
        def LED(p, s, t):
            f = Frame(p, bg='white')
            txon = Frame(f, bg = 'grey80', relief = 'sunken', width = s, height = s)
            txon.grid(row = 0, column = 0)
            r2i2 = Label(f, text = t, font = ('Arial', 14), bg='white').grid(row = 0, column = 1, sticky = W)
            return f, txon

        self.r2b1, self.txon = LED(p = self.r2f2, s = 10, t = 'On')
        self.r2b1.pack(anchor = W, padx = 10, pady = 0)
        self.r2b2, self.txoff = LED(p = self.r2f2, s = 10, t = 'Off')
        self.r2b2.pack(anchor = W, padx = 10, pady = 0)
        
        #### r2f2 - Running Program label frame set
        self.r2f3 = LabelFrame(self.r2, font = ('Arial', 16), text = 'Program running', background = 'white')
        self.r2f3.grid(row = 3, column = 0, sticky = W+N+E, pady = 5, padx = 10)
        self.r2b3, self.beacon = LED(self.r2f3, 10, 'WSPR Beacon')
        self.r2b3.pack(anchor = W, padx = 10)
        self.r2b4, self.siggen = LED(self.r2f3, 10, 'Signal Generator')
        self.r2b4.pack(anchor = W, padx = 10)
        self.r2b5, self.idle = LED(self.r2f3, 10, 'Idle')
        self.r2b5.pack(anchor = W, padx = 10)
        CreateToolTip(self.r2f3,'Information about the running software routine in the transmitter.')

        ###################################################
        # r3 - GPS Information
        ###################################################
        self.r3l1 = ttk.Label(self.r3, anchor = SW, font = ('Arial', 24), text = 'GPS Information', background = 'white', justify = LEFT)
        self.r3l1.grid(row = 0, column = 0, sticky = W+S, padx = 10)

        #### r3f1 - Signal Quality frame
        self.r3f1 = Frame(self.r3, bg='white')
        self.r3l2 = ttk.Label(self.r3f1, anchor = S, font = ('Arial', 12), text = 'Signal Quality', background = 'white', justify = CENTER)
        self.r3l2.grid(row = 1, column = 0, sticky = S)
        self.signal_style = ttk.Style()
        self.signal_style.layout('signal.Horizontal.TProgressbar', 
                                 [('Horizontal.Progressbar.trough',
                                   {'children': [('Horizontal.Progressbar.pbar',
                                                  {'side': 'left', 'sticky': 'ns'})],
                                    'sticky': 'nswe'}), 
                                  ('Horizontal.Progressbar.label', {'sticky': ''})])
        self.signal_style.configure('signal.Horizontal.TProgressbar', troughcolor = 'white', background = 'blue')
        self.signal.set(0)
        self.r3p1 = ttk.Progressbar(self.r3f1, orient = HORIZONTAL, length = 180, mode = 'determinate',
                                    style = 'signal.Horizontal.TProgressbar', variable = self.signal)
        self.r3p1.grid(row = 2, column = 0, sticky = N)
        CreateToolTip(self.r3p1,'The mean Signal to Noise Ratio of the four strongest satellites')
        self.r3f1.grid(row = 1, column = 0, padx = 10, pady = 5)
        self.locked = Label(self.r3f1, text = ' ', font = ('Arial',18), bg='white')
        self.locked.grid(row = 3, column = 0, sticky = N)

        #### r3f2 - Time and Position frame
        self.r3f2 = Frame(self.r3, bg='white') 
        self.r3l3 = ttk.Label(self.r3f2, anchor = SW, font = ('Arial', 12), text = 'UTC Time', background = 'white', justify = LEFT)
        self.r3l3.grid(row = 0, column = 0, sticky = SW)
        self.r3l4 = ttk.Label(self.r3f2, anchor = S, font = ('Arial', 12), text = 'Position', background = 'white', justify = LEFT)
        self.r3l4.grid(row = 0, column = 1, sticky = S, padx = 30)
        self.r3l5 = Label(self.r3f2, anchor = NW, font = ('Arial', 24), textvariable = self.curtime, background = 'white', justify = LEFT, fg = 'grey80')
        self.r3l5.grid(row = 1, column = 0, sticky = NW)
        self.r3l6 = Label(self.r3f2, anchor = N, font = ('Arial', 24), textvariable = self.position, background = 'white', justify = LEFT)
        self.r3l6.grid(row = 1, column = 1, sticky = N)
        CreateToolTip(self.r3l6,'Maidenhead grid')
        self.r3f2.grid(row = 2, column = 0, padx = 10, pady = 5, sticky = W)

        #### Label in r3 - Az/El info
        self.r3l7 = ttk.Label(self.r3, anchor = S, font = ('Arial', 12), text = 'Az/El plot of GPS Satellites', background = 'white', justify = CENTER)
        self.r3l7.grid(row = 3, column = 0, sticky = S, padx = 10)
        CreateToolTip(self.r3l7,'Azimuth/Elevation plot of the visible GPS satellites')

        #### Canvas for the GPS plot
        self.plot = Canvas(self.r3, width = 240, height = 240, borderwidth = 0, highlightthickness = 0, bg = 'white')
        self.plot.create_text(10, 120, text = 'W')
        self.plot.create_text(120, 10, text = 'N')
        self.plot.create_text(230, 120, text = 'E')
        self.plot.create_text(120, 230, text = 'S')
        self.plot.p1 = self.plot.create_arc(10, 10, 230, 230, style = ARC, start =  5, extent = 80, width = 2)
        CreateCanvasTip(self.plot,self.plot.p1,'0 degree elevation marker (Local horizon)')
        self.plot.p2 = self.plot.create_arc(10, 10, 230, 230, style = ARC, start = 95, extent = 80, width = 2)
        CreateCanvasTip(self.plot,self.plot.p2,'0 degree elevation marker (Local horizon)')
        self.plot.p3 = self.plot.create_arc(10, 10, 230, 230, style = ARC, start = 185, extent = 80, width = 2)
        CreateCanvasTip(self.plot,self.plot.p3,'0 degree elevation marker (Local horizon)')
        self.plot.p4 = self.plot.create_arc(10, 10, 230, 230, style = ARC, start = 275, extent = 80, width = 2)
        CreateCanvasTip(self.plot,self.plot.p4,'0 degree elevation marker (Local horizon)')
        self.plot.p5 = self.plot.create_oval(50, 50, 190, 190, outline = '#000000', fill = 'white', width = 2)
        CreateCanvasTip(self.plot,self.plot.p5,'30 degree elevation marker')
        self.plot.p6 = self.plot.create_oval(90, 90, 150, 150, outline = '#000000', fill = 'white', width = 2)
        CreateCanvasTip(self.plot,self.plot.p6,'60 degree elevation marker')
        self.plot.grid(row = 4, column = 0, padx = 10, pady = 5)
        
        ###################################################
        ###################################################
        # bl - Bottom Left frame set
        ###################################################
        ###################################################
        self.bl = Frame(self.root, relief = 'ridge', bd = 2, bg='white')
        self.scrollbar = Scrollbar(self.bl)
        self.scrollbar.pack(side = RIGHT, fill = Y)
        self.log = Listbox(self.bl, yscrollcommand = self.scrollbar.set, height = 5, width = 40)
        self.log.pack(side = LEFT, fill = BOTH)
        self.scrollbar.config(command = self.log.yview)
        self.bl.grid(row = 1, column = 0, sticky = W, padx = 5, pady = 5)
        CreateToolTip(self.bl,'Errors and other miscellaneous information from the microcontroller are shown here')
        
        self.saveButton = Frame(self.root, bg='grey80')
        self.saveButton.grid(row = 1, column = 1)
        Button(self.saveButton, text = 'Save Settings', wraplength = 100, command = self.vc.saveSettingsPressed,
               bg = 'grey80', font = ('Arial', 18), width = 10).grid(row = 0, column = 0, ipadx = 5,
                                                                     ipady = 2, padx = 2, pady = 2)
        CreateToolTip(self.saveButton,'Save the configuration to EEPROM')


        ###################################################
        ###################################################
        # br - Bottom right frame set
        ###################################################
        ###################################################
        self.br = Frame(self.root, bg='white')
        self.br.grid(row = 1,column = 2,sticky = E)
        self.debug.set(0)
        self.debugButton = Checkbutton(self.br, selectcolor = 'white', fg = 'black', text = 'Debug view',
                                       variable = self.debug, command = self.vc.setDebug, bg='white')
        self.debugButton.grid(row = 0, column = 0, sticky = E+S,pady = 10,padx = 20)
        CreateToolTip(self.debugButton,'Display optional controls for troubleshooting')
        self.ver = Label(self.br, text = 'Version: '+VERSION, bg='white')
        self.ver.grid(row = 0, column = 1, sticky = E+S, pady = 10, padx = 10)
        CreateToolTip(self.ver,'Version of this program')

        ###################################################
        ###################################################
        # f0 - Debug frame
        ###################################################
        ###################################################
        self.f0 = Frame(self.root, bg='white')
        self.f0.grid(row = 2,column = 0,columnspan = 4,sticky = W+E,pady = 5)

        self.b0 = Frame(self.f0, relief = 'ridge', bd = 2)
        self.s0 = Scrollbar(self.b0)
        self.s0.pack(side = RIGHT, fill = Y)
        self.trace = Listbox(self.b0, yscrollcommand = self.s0.set, height = 10, width = 60)
        self.trace.pack(side = LEFT, fill = BOTH)
        self.s0.config(command = self.trace.yview)
        self.b0.grid(row = 0, rowspan = 2, column = 0, sticky = W)
        CreateToolTip(self.f0,'Incoming API texts are shown here')

        self.f0f1 = Frame(self.f0, bg='white')
        self.f0f1.grid(row = 0,column = 1,padx = 20,sticky = W+N)
        self.f0l1 = Label(self.f0f1, text = 'RXChars:', bg='white')
        self.f0l1.grid(row = 0, column = 1, sticky = E)
        self.f0l2 = Label(self.f0f1, textvariable = self.rxChars, bg='white')
        self.f0l2.grid(row = 0, column = 2, sticky = W)
        self.f0l3 = LabelFrame(self.f0, text = 'SendCommands', bg='white')
        self.f0l3.grid(row = 1, column = 1,sticky = S+W,padx = 10,pady = 10)
        CreateToolTip(self.f0l3,'Use this to send API commands to the microcontroller')
        self.f0e1 = ttk.Entry(self.f0l3, width = 40, textvariable = self.sendCommands)
        self.f0e1.grid(row = 0, column = 0, columnspan = 2, padx = 20)
        CreateToolTip(self.f0e1,'Put you API command string here')
        self.CRLF.set(1)
        self.f0c1 = Checkbutton(self.f0l3, selectcolor = 'white', fg='black', text = 'Send CR+LF',
                                variable = self.CRLF, command = self.vc.setCRLF, bg='white')
        self.f0c1.grid(row = 1, column = 0, sticky = W+S,pady = 10)
        self.sendButton = Button(self.f0l3, text = 'Send', command = self.vc.sendPressed, 
                                 bg = 'grey80', font = ('Arial', 18))
        self.sendButton.grid(row = 1, column = 1, sticky = E+S,padx = 5,pady = 5)
        self.f0.grid_forget()

        ###################################################
        ###################################################
        # tab1 - WSPR Beacon Tab
        ###################################################
        ###################################################

        ### Layout - tab1 #############################
        #                                             #
        #  +-f1------------------------------------+  #
        #  | +-f1l1------------------------------+ |  #
        #  | | +-f1l2------------+ +-f1f1------+ | |  #
        #  | | |                 | |           | | |  #
        #  | | |   per band      | | Callsign  | | |  #
        #  | | |     settings    | |           | | |  #
        #  | | |                 | | +-f1l6--+ | | |  #
        #  | | |                 | | | Pos'n | | | |  #
        #  | | |                 | | +-------+ | | |  #
        #  | | |                 | | +-f1l7--+ | | |  #
        #  | | |                 | | | Power | | | |  #
        #  | | |                 | | +-------+ | | |  #
        #  | | |                 | |           | | |  #
        #  | | |                 | | +-f1f2--+ | | |  #
        #  | | |    pause        | | | St/St | | | |  #
        #  | | |                 | | +-------+ | | |  #
        #  | | +-----------------+ +-----------+ | |  #
        #  | +-----------------------------------+ |  #
        #  +---------------------------------------+  #
        #                                             #
        ###############################################

        self.f1 = Frame(self.tab1, bg = self.tabbg)
        self.f1.grid(row = 0, column = 0)
        self.f1l1 = LabelFrame(self.f1, font = ('Arial', 18), text = 'WSPR Configuration', background = self.tabbg, padx = 5)
        self.f1l1.grid(row = 0, column = 0)

        ##### Items within the Left side of the Beacon tab
        self.f1l2 = LabelFrame(self.f1l1, font = ('Arial', 14), text = 'Bands to transmit on', background = self.tabbg)
        self.f1l2.grid(row = 0, column = 0, sticky = N+S+W)
        CreateInfoButton(self.f1l2, 'Click me for more information about this section',
                         _tipb1, bg=self.tabbg).grid(row = 0, column = 0)
        CreateInfoButton(self.f1l2, 'Click me for more information about this section',
                         _tipb2, bg=self.tabbg).grid(row = 0, column = 1, columnspan = 2)
        ttk.Label(self.f1l2, font = ('Arial', 16), text = 'LP', background = self.tabbg,
                  justify = CENTER).grid(row = 1, column = 0)
        ttk.Label(self.f1l2, font = ('Arial', 16), text = 'Band', background = self.tabbg,
                  justify = CENTER).grid(row = 1, column = 1, columnspan = 2)
        ttk.Label(self.f1l2, font = ('Arial', 16), text = 'Progress', background = self.tabbg,
                  justify = CENTER).grid(row = 1, column = 3, columnspan = 2)

        self.lp = []
        self.band = []
        self.bandlabel = []
        self.progress = []
        self.percentprogress = []
        self.active = []
        self.f1f = []
        self.enable = []        
        self.blank_style = ttk.Style()
        self.blank_style.configure('blank.Horizontal.TProgressbar',troughcolor = self.tabbg, background = self.tabbg,
                                   bordercolor = self.tabbg, darkcolor = self.tabbg, lightcolor = self.tabbg)

        for n in range(len(self._bands)):
            self.lp.append(Frame(self.f1l2, bg = self.tabbg, relief = 'flat', width = 10, height = 10))
            self.lp[n].grid(row = 2+n, column = 0)
            self.enable.append(IntVar())
            self.band.append(Checkbutton(self.f1l2, bg = self.tabbg, selectcolor = 'white', fg='black', bd = 2, highlightthickness = 0,
                                         variable = self.enable[n], command = self.vc.bandCheck))
            self.band[n].grid(row = 2+n, column = 1, sticky = E)
            self.enable[n].set(0)
            #self.band[n].configure(state = 'disabled')
            CreateToolTip(self.band[n],'Enable/Disable transmission on this band')
            self.bandlabel.append(ttk.Label(self.f1l2, font = ('Arial', 14), text = self._bands[n],
                                            background = self.tabbg, justify = LEFT, anchor = W))
            self.bandlabel[n].grid(row = 2+n, column = 2, sticky = W)
            self.percentprogress.append(IntVar())
            self.percentprogress[n].set(0)
            self.progress.append(ttk.Progressbar(self.f1l2, style = 'blank.Horizontal.TProgressbar', orient = HORIZONTAL, length = 50,
                                                 mode = 'determinate',variable = self.percentprogress[n]))
            self.progress[n].grid(row = 2+n, column = 3)
            CreateToolTip(self.progress[n],'WSPR transmission progress')
            self.active.append(Label(self.f1l2, font = ('Arial', 16), text = ' ', width = 1, borderwidth = 0, bg = self.tabbg, bd = 0,
                                     highlightthickness = 0, anchor = 'center'))
            self.active[n].grid(row = 2+n, column = 4)

        n = len(self._bands)+2
        ttk.Label(self.f1l2, font = ('Arial', 14), text = 'Pause after transmission.', background = self.tabbg,
                  justify = CENTER).grid(row = n, column = 0, columnspan = 3)
        CreateInfoButton(self.f1l2, 'Click me for more information about this section',
                         _tipb3, bg=self.tabbg).grid(row = n+1, column = 0, padx = 10, sticky = E)
        self.pauseTime.set(0)
        self.pause = ttk.Entry(self.f1l2, width = 6, textvariable = self.pauseTime)
        self.pause.grid(row = n+1, column = 1, columnspan = 2, sticky = W)
        CreateToolTip(self.pause,'Pause in seconds after the WSPR beacon has transmitted on all enabled bands.')
        self.pauseTime.trace('w', self.vc.pauseUpdate)
        self.f1p1 = ttk.Progressbar(self.f1l2, orient = HORIZONTAL, length = 50, mode = 'determinate', variable = self.pausepercent)
        self.f1p1.grid(row = n+1, column = 3)
        CreateToolTip(self.f1p1,'Pause progress')
        self.pauseactive = Label(self.f1l2, font = ('Arial', 16), text = ' ', width = 1, borderwidth = 0, bg = self.tabbg, bd = 0,
                                 highlightthickness = 0, anchor = 'center')
        self.pauseactive.grid(row = n+1, column = 4)
        
        # Loop graphic
        m = (5+n)*20
        self.loop = Canvas(self.f1l2, width = 60, height = m, borderwidth = 0, highlightthickness = 0, bg = self.tabbg)
        self.loop.create_line(50, 30, 50, m-40, width = 3)
        self.loop.create_line(10, 40, 10, m-40, dash = (4, 2), width = 3, arrow = LAST)
        self.loop.create_line(10, 40, 10, 44, dash = (4, 2), width = 3, arrow = LAST)
        self.loop.create_arc(10, 60, 50, 10, style = ARC, start = 0, extent = 180, width = 3)
        self.loop.create_arc(10, m-20, 50, m-60, style = ARC, start = 180, extent = 180, width = 3)
        self.loop.grid(row = 0, column = 5, rowspan = n+4, padx = 10)

        ################################################################
        # Right side of Beacon Configuration frame
        ################################################################
        self.f1f1 = Frame(self.f1l1, bg = self.tabbg)
        self.f1f1.grid(row = 0, column = 1, sticky = N+S, padx = 10)

        # Call sign
        ttk.Label(self.f1f1, font = ('Arial', 14), text = 'Call Sign', background = self.tabbg,
                  justify = LEFT).grid(row = 0, column = 0, sticky = W+N)
        self.call.trace('w', self.vc.callUpdate)
        self.f1e2 = ttk.Entry(self.f1f1, width = 8, textvariable = self.call, font = ('Arial', 20))
        self.f1e2.grid(row = 1, column = 0, sticky = W+N)
        self.f1e2.insert(0, '')
        CreateToolTip(self.f1e2,'Your Amateur Call Sign.  Max six characters')

        #### f1l6 - Position reporting labelframe
        self.f1l6 = LabelFrame(self.f1f1, font = ('Arial', 14), text = 'Reported position', background = self.tabbg, pady = 10)
        self.f1l6.grid(row = 2, column = 0, pady = 10, sticky = N+W+E)
        Radiobutton(self.f1l6, text = 'Auto (GPS)', font = ('Arial', 14), padx = 10,
                    variable = self.rpam, value = 'G', bg = self.tabbg, command = self.vc.rpamGPS).pack(anchor = W)
        Radiobutton(self.f1l6, text = 'Manual', font = ('Arial', 14), padx = 10,
                    variable = self.rpam, value = 'M', bg = self.tabbg,  command = self.vc.rpamManual).pack(anchor = W)
        self.rpam.set('G')
        self.location.trace('w', self.vc.changeLocation)
        ttk.Entry(self.f1l6, width = 5, textvariable = self.location).pack(anchor = N)
        
        #### f1l7 - Power reporting labelframe
        self.f1l7 = LabelFrame(self.f1f1, font = ('Arial', 14), text = 'Reported power', background = self.tabbg, pady = 10)
        self.f1l7.grid(row = 3, column = 0, sticky = N+W+E)
        CreateToolTip(self.f1l7,'Set the power you want to report in the transmission')
        self.f1b3 = Radiobutton(self.f1l7, text = 'Normal mode', font = ('Arial', 14), padx = 10,
                                variable = self.rpmode, value = 'N', bg = self.tabbg,
                                command = self.vc.rpmodeNormal)
        self.f1b3.grid(row = 0, column = 0, columnspan = 2, sticky = W+S)
        # Note: need to separate the button and label - different tool tip in each in the official version
        CreateToolTip(self.f1b3,'Normal power reporting from the listbox below.')
        self.f1o1 = OptionMenu(self.f1l7, self.rpwr, *self._powers, command = self.vc.rpwrUpdate)
        self.f1o1.grid(row = 1, column = 0, sticky = E)
        self.rpwr.set('23')
        CreateToolTip(self.f1o1,'Pick the power you are using.  Normally 23 dBm for the Desktop and LP1 products.')
        Label(self.f1l7, text = 'dBm', bg = self.tabbg).grid(row = 1, column = 1, sticky = W)
        self.f1df = Frame(self.f1l7, bg=self.tabbg)
        self.f1df.grid(row = 3, column = 0, columnspan = 2, sticky=W, pady = 5)
        self.f1b4 = Radiobutton(self.f1df, variable = self.rpmode, value = 'A', command = self.vc.rpmodeAltitude,
                                bg = self.tabbg, anchor = SW).grid(row = 0, column = 0, sticky=W+N)
        Label(self.f1df, text = 'Encode Altitude as power', font = ('Arial', 14), justify = LEFT, wraplength = 100,
              bg = self.tabbg).grid(row = 0, column = 1, sticky=W)
        self.rpmode.set('N')
        CreateToolTip(self.f1df,'Altitude will be sent as power. 0-18km will be coded into 0-60dBm.')
        CreateInfoButton(self.f1l7, 'Click me for more information about this section',
                         _tipb4, bg=self.tabbg).grid(row = 4, column = 1, sticky = E)

        #### f1f2 - Start/Stop buttons
        self.f1f2 = Frame(self.f1f1, background = self.tabbg)
        self.f1f2.grid(row = 4, column = 0, sticky = 'SWE', padx = 15, pady = 15)

        self.running = Frame(self.f1f2, bg = self.tabbg)
        self.running.pack(side = LEFT)
        Button(self.running, text = 'Start', command = self.vc.startPressed, bg = 'grey80',
               font = ('Arial', 18)).grid(row = 0, column = 0, ipadx = 5, ipady = 2, padx = 2, pady = 2)
        self.stopped = Frame(self.f1f2, bg = self.tabbg)
        self.stopped.pack(side = RIGHT)
        Button(self.stopped, text = 'Stop', command = self.vc.stopPressed, bg = 'grey80',
               font = ('Arial', 18)).grid(row = 0, column = 0, ipadx = 5, ipady = 2, padx = 2, pady = 2)

        self.f1f1.grid_columnconfigure(1, weight = 1)
        self.f1f1.grid_rowconfigure(4, weight = 1)

        ###################################################
        ###################################################
        # tab2 - Signal Generator tab
        ###################################################
        ###################################################
        self.f2 = Frame(self.tab2, bg = self.tabbg)
        self.f2.grid(row = 0, column = 0, sticky = W+E, padx = 20)
        self.f2l1 = LabelFrame(self.f2, font = ('Arial', 18), text = 'Signal Generator', background = self.tabbg, pady = 10)
        self.f2l1.grid(row = 0, column = 0, columnspan = 2, sticky = N+W+E+S, ipadx = 20)

        #### row 0 - labels
        Label(self.f2l1, text = 'MHz', bg = self.tabbg, font = ('Arial', 14)).grid(row = 0, column = 1, sticky = 'N')
        Label(self.f2l1, text = 'kHz', bg = self.tabbg, font = ('Arial', 14)).grid(row = 0, column = 3, sticky = 'N')
        Label(self.f2l1, text = ' Hz', bg = self.tabbg, font = ('Arial', 14)).grid(row = 0, column = 5, sticky = 'N')
        Label(self.f2l1, text = 'cHz', bg = self.tabbg, font = ('Arial', 14)).grid(row = 0, column = 7, sticky = 'N')
        
        #### row 1 - frames to hold groups of three digits, spacings, and info button
        self.f2f0 = Frame(self.f2l1, bg = self.tabbg)
        self.f2f0.grid(row = 1, column = 0, padx=20)
        self.f2f1 = Frame(self.f2l1, bg = self.tabbg) #MHz
        self.f2f1.grid(row = 1, column = 1)
        self.f2f2 = Frame(self.f2l1, bg = self.tabbg)
        self.f2f2.grid(row = 1, column = 2)
        self.f2f3 = Frame(self.f2l1, bg = self.tabbg) #kHz
        self.f2f3.grid(row = 1, column = 3)
        self.f2f4 = Frame(self.f2l1, bg = self.tabbg)
        self.f2f4.grid(row = 1, column = 4)
        self.f2f5 = Frame(self.f2l1, bg = self.tabbg) #Hz
        self.f2f5.grid(row = 1, column = 5)
        self.f2f6 = Frame(self.f2l1, bg = self.tabbg) #dot
        self.f2f6.grid(row = 1, column = 6)
        self.f2f7 = Frame(self.f2l1, bg = self.tabbg) #cHz
        self.f2f7.grid(row = 1, column = 7)
        self.f2f8 = Frame(self.f2l1, bg = self.tabbg) #info
        self.f2f8.grid(row = 1, column = 8)

        # up buttons, digits, and down buttons for the MHz frame
        Button(self.f2f1, text = '+', command = self.vc.up100M, bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 0, sticky = 'S')
        Button(self.f2f1, text = '+', command = self.vc.up10M,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 1, sticky = 'S')
        Button(self.f2f1, text = '+', command = self.vc.up1M,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 2, sticky = 'S')
        Label(self.f2f1, textvariable = self.d100M, bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 0)
        Label(self.f2f1, textvariable = self.d10M,  bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 1)
        Label(self.f2f1, textvariable = self.d1M,   bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 2)
        Button(self.f2f1, text = '-', command = self.vc.down100M, bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 0, sticky = 'S')
        Button(self.f2f1, text = '-', command = self.vc.down10M,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 1, sticky = 'S')
        Button(self.f2f1, text = '-', command = self.vc.down1M,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 2, sticky = 'S')

        # Space holder to seperate the MHz from the kHz
        Label(self.f2f2, text = ' ', bg = self.tabbg, font = ('Arial', 16)).grid(row = 0, column = 0, padx = 10)
        
        # up buttons, digits, and down buttons for the kHz frame
        Button(self.f2f3, text = '+', command = self.vc.up100k, bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 0, sticky = 'S')
        Button(self.f2f3, text = '+', command = self.vc.up10k,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 1, sticky = 'S')
        Button(self.f2f3, text = '+', command = self.vc.up1k,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 2, sticky = 'S')
        Label(self.f2f3, textvariable = self.d100k, bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 0)
        Label(self.f2f3, textvariable = self.d10k,  bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 1)
        Label(self.f2f3, textvariable = self.d1k,   bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 2)
        Button(self.f2f3, text = '-', command = self.vc.down100k, bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 0, sticky = 'S')
        Button(self.f2f3, text = '-', command = self.vc.down10k,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 1, sticky = 'S')
        Button(self.f2f3, text = '-', command = self.vc.down1k,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 2, sticky = 'S')

        # Space holder to seperate the kHz from the Hz
        Label(self.f2f4, text = ' ', bg = self.tabbg, font = ('Arial', 16)).grid(row = 0, column = 0, padx = 10)

        # up buttons, digits, and down buttons for the Hz frame
        Button(self.f2f5, text = '+', command = self.vc.up100Hz, bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 0, sticky = 'S')
        Button(self.f2f5, text = '+', command = self.vc.up10Hz,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 1, sticky = 'S')
        Button(self.f2f5, text = '+', command = self.vc.up1Hz,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 2, sticky = 'S')
        Label(self.f2f5, textvariable = self.d100Hz, bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 0)
        Label(self.f2f5, textvariable = self.d10Hz,  bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 1)
        Label(self.f2f5, textvariable = self.d1Hz,   bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 2)
        Button(self.f2f5, text = '-', command = self.vc.down100Hz, bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 0, sticky = 'S')
        Button(self.f2f5, text = '-', command = self.vc.down10Hz,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 1, sticky = 'S')
        Button(self.f2f5, text = '-', command = self.vc.down1Hz,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 2, sticky = 'S')

        # Decimal mark to seperate the Hz from the cHz
        Label(self.f2f6, text = '.', bg = self.tabbg, font = ('Arial', 16)).grid(row = 0, column = 0, padx = 10)

        # up buttons, digits, and down buttons for the cHz frame
        Button(self.f2f7, text = '+', command = self.vc.up10c,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 1, sticky = 'S')
        Button(self.f2f7, text = '+', command = self.vc.up1c,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 0, column = 2, sticky = 'S')
        Label(self.f2f7, textvariable = self.d10c,  bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 1)
        Label(self.f2f7, textvariable = self.d1c,   bg = self.tabbg, font = ('Arial', 16)).grid(row = 1, column = 2)
        Button(self.f2f7, text = '-', command = self.vc.down10c,  bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 1, sticky = 'S')
        Button(self.f2f7, text = '-', command = self.vc.down1c,   bg = 'grey80', font = ('Arial', 12),
               highlightthickness = 0).grid(row = 2, column = 2, sticky = 'S')

        # info button on the right side
        CreateInfoButton(self.f2f8, 'Click me for more information about this section', _tips1, bg=self.tabbg).grid(row = 0, column = 0, padx=20)

        # Frame to hold the Start/Stop buttons
        self.f2f9 = Frame(self.f2l1, bg = self.tabbg)
        self.f2f9.grid(row = 2, column = 6, columnspan = 3, padx=20, pady = 40, sticky=W+E+S)
        self.generating = Frame(self.f2f9, bg = self.tabbg)
        self.generating.pack(side = LEFT)
        Button(self.generating, text = 'Start', command = self.vc.startGenerator, bg = 'grey80',
               font = ('Arial', 18)).grid(row = 0, column = 0, ipadx = 5, ipady = 2, padx = 2, pady = 2)
        self.silent = Frame(self.f2f9, bg = self.tabbg)
        self.silent.pack(side = RIGHT)
        Button(self.silent, text = 'Stop', command = self.vc.stopPressed, bg = 'grey80',
               font = ('Arial', 18)).grid(row = 0, column = 0, ipadx = 5, ipady = 2, padx = 2, pady = 2)

        ###################################################
        ###################################################
        # tab3 - Boot Configuration tab
        ###################################################
        ###################################################
        self.f3 = Frame(self.tab3, bg = self.tabbg)
        self.f3.grid(row = 0, column = 0) 
        self.f3l1 = LabelFrame(self.f3, font = ('Arial', 14), text = 'Do this at startup', background = self.tabbg, pady = 10)
        self.f3l1.grid(row = 0, column = 0, columnspan = 2, sticky = W+E, padx = 20)
        Radiobutton(self.f3l1, text = 'Signal Generator', font = ('Arial', 14), padx = 10, variable = self.boot,
                    highlightthickness = 0, value = 'S', bg = self.tabbg, command = self.vc.setBoot).pack(anchor = W, padx=10)
        Radiobutton(self.f3l1, text = 'WSPR Beacon', font = ('Arial', 14), padx = 10, variable = self.boot,
                    highlightthickness = 0, value = 'W', bg = self.tabbg,  command = self.vc.setBoot).pack(anchor = W, padx=10)
        Radiobutton(self.f3l1, text = 'Idle', font = ('Arial', 14), padx = 10, variable = self.boot,
                    highlightthickness = 0, value = 'N', bg = self.tabbg,  command = self.vc.setBoot).pack(anchor = W, padx=10)
        self.boot.set('N')
        CreateToolTip(self.f3l1,'Determines what software routine is executed at power on.')
        
        ###################################################
        ###################################################
        # tab4 - Serial port tab
        ###################################################
        ###################################################
        self.f4 = Frame(self.tab4, bg = self.tabbg,padx = 20)
        self.f4.grid(row = 0, column = 0, padx = 20, sticky=W+E)
 
        #### Top labelframe holds the user selection
        self.f4l4 = LabelFrame(self.f4, font = ('Arial', 14), text = 'Serial Port', background = self.tabbg, pady = 10)
        self.f4l4.grid(row=0,column=0,sticky=N+W+E)
        self.f4m1 = OptionMenu(self.f4l4, self.portName, *self.vc.model.getPorts())
        self.f4m1.config(bg = self.tabbg)
        self.f4m1.pack(side=LEFT,expand=True,fill=BOTH)
        self.serialButton = Button(self.f4l4, text = 'Select', command = self.vc.selectPort, bg = 'grey80', font = ('Arial', 14))
        self.serialButton.pack(side=RIGHT,padx=10)
        CreateToolTip(self.f4l4,'Serial port setting for communication with the transmitter.')
        
        #### Bottom labelframe holds the current status
        self.f4l1 = LabelFrame(self.f4, font = ('Arial', 14), text = 'Status', background = self.tabbg, pady = 10)
        self.f4l1.grid(row = 1, column = 0, columnspan = 2, sticky = S+W+E, padx = 20)
        Label(self.f4l1, text = 'Current Port:', bg = self.tabbg).grid(row = 0, column = 0, sticky = 'E')
        self.currentPort.set(self.vc.model.portName)
        Label(self.f4l1, textvariable = self.currentPort, bg = self.tabbg).grid(row = 0, column = 1, columnspan = 2, sticky = 'W')
        Label(self.f4l1, text = 'Device detected:', bg = self.tabbg).grid(row = 1, column = 0, sticky = 'E')
        def LEDx(p, s, t, b):
            f = Frame(p,bg = b)
            txon = Frame(f, bg = 'grey80', relief = 'sunken', width = s, height = s)
            txon.grid(row = 0, column = 0)
            r2i2 = Label(f, text = t, font = ('Arial', 14), bg = b).grid(row = 0, column = 1, sticky = W)
            return f, txon
        self.f4b2, self.deviceOK = LEDx(self.f4l1, 10, 'OK', self.tabbg)
        self.f4b2.grid(row = 1, column = 1, sticky = 'W', padx = 10)
        self.f4b3, self.deviceNOK = LEDx(self.f4l1, 10, 'Not Detected', self.tabbg)
        self.f4b3.grid(row = 1, column = 2, sticky = 'W', padx = 10)
        self.deviceNOK.config(bg = 'red')

        self.f4.grid_rowconfigure(1, weight = 1)
        self.f4.grid_columnconfigure(0, weight = 1)

        ################################################################
        ################################################################
        # "Loading" labels - here, because they go on top of everything
        ################################################################
        ################################################################
        self.l1 = Label(self.f1, text = 'Loading...', font = ('Arial',40), fg = 'red',  borderwidth = 5, relief = 'solid')
        self.l1.place(relx = 0.5, rely = 0.5, anchor = 'center')
        self.l2 = Label(self.f2, text = 'Loading...', font = ('Arial',40), fg = 'red',  borderwidth = 5, relief = 'solid')
        self.l2.place(relx = 0.5, rely = 0.5, anchor = 'center')
        self.l3 = Label(self.f3, text = 'Loading...', font = ('Arial',40), fg = 'red',  borderwidth = 5, relief = 'solid')
        self.l3.place(relx = 0.5, rely = 0.5, anchor = 'center')


        ################################################################
        # End of __init__ -- setup of templates complete!
        ################################################################


        
    ################################################################
    # Commands from the Controller
    ################################################################
    # WSPR Configuration commands
    def installLP(self, band):
        self.lp[band].config(bg = 'green', relief = 'sunken')
        CreateToolTip(self.lp[band],'A lowpass filter for the '+self._bands[band]+' band is built in.')
        #self.band[band].configure(state = 'normal') # We don't disable them, now

    def setPauseTime(self, data):
        self.pauseTime.set(int(data))
    def setProgress(self, band, seconds):
        self.found = False
        if band<0:
            if seconds == 0: self.found = True
            _p = self.pauseTime.get()
            if _p < 1:
                self.percent = 100
            else:
                self.percent = 100 * (_p - seconds) / _p
            self.pausepercent.set(self.percent)
        else:
            self.pausepercent.set(0)
            self.percent = 100 * seconds/161
        for self.v in range(len(self._bands)):
            if self.v == band:
                self.found = True
                self.percentprogress[self.v].set(self.percent)
            else:
                if self.found:
                    self.percentprogress[self.v].set(0)

    def setActive(self,band,color):
        if band < 0:
            if python == 2:
                self.pauseactive.configure(text = unichr(0x2B05),fg = color)
            else:
                self.pauseactive.configure(text = chr(0x2B05),fg = color)
        else:
            self.pauseactive.configure(text = ' ',fg = self.tabbg)
        for self.v in range(len(self._bands)):
            if self.v == band:
                if python == 2:
                    self.active[self.v].configure(text = unichr(0x2B05),fg = color)
                else:
                    self.active[self.v].configure(text = chr(0x2B05),fg = color)
            else:
                self.active[self.v].configure(text = ' ',fg = self.tabbg)

    def setRunning(self):
        self.stopped.config(bg = self.tabbg)
        self.silent.config(bg = self.tabbg)
        self.generating.config(bg = self.tabbg)
        self.running.config(bg = '#0000FF')
    def setStopped(self):
        self.running.config(bg = self.tabbg)
        self.generating.config(bg = self.tabbg)
        self.stopped.config(bg = '#0000FF')
        self.silent.config(bg = '#0000FF')
        self.setActive(-1,self.tabbg)

    # Signal Generator commands
    def setGenerating(self):
        self.stopped.config(bg = self.tabbg)
        self.silent.config(bg = self.tabbg)
        self.running.config(bg = self.tabbg)
        self.generating.config(bg = '#0000FF')
        self.setActive(-1,self.tabbg)

    def setFQ(self,data):
        self.d100M.set(int(data[1]))
        self.d10M.set(int(data[2]))
        self.d1M.set(int(data[3]))
        self.d100k.set(int(data[4]))
        self.d10k.set(int(data[5]))
        self.d1k.set(int(data[6]))
        self.d100Hz.set(int(data[7]))
        self.d10Hz.set(int(data[8]))
        self.d1Hz.set(int(data[9]))
        self.d10c.set(int(data[10]))
        self.d1c.set(int(data[11]))

    # Boot Configuration commands (none, at present)

    # Serial Port configuration commands
    def serialOK(self,state):
        if state:
            self.deviceNOK.config(bg = 'grey80')
            self.deviceOK.config(bg = 'green')
            
            # Enable the other tabs (if they are still disabled)
            self.tabs.tab(self.tab1,state = 'normal')
            self.tabs.tab(self.tab2,state = 'normal')
            self.tabs.tab(self.tab3,state = 'normal')

            # Remove 'Loading...' labels, if they are there
            if self.l1.winfo_exists():
                self.l1.place_forget()
            if self.l2.winfo_exists():
                self.l2.place_forget()
            if self.l3.winfo_exists():
                self.l3.place_forget()
                
        else:
            self.deviceOK.config(bg = 'grey80')
            self.deviceNOK.config(bg = 'red')

            # Put the Loading labels on everything except Serial port
            self.l1.place(relx = 0.5, rely = 0.5, anchor = 'center')
            self.l2.place(relx = 0.5, rely = 0.5, anchor = 'center')
            self.l3.place(relx = 0.5, rely = 0.5, anchor = 'center')

            # Should I just disable the non-serial-configuration tabs instead????

    def setDebug(self,state): # Displays or hides the debug pane
        if state:
            self.f0.grid(row = 2, column = 0, columnspan = 3, sticky=W)
        elif self.f0.winfo_exists():
            self.f0.grid_forget() # Hide debug frame

    def traceInsert(self, msg): # puts a debug message in the debug frame
        if len(msg)>0:
            if debug: print(msg)
            self.trace.insert(END, msg)
            self.trace.see(END)

    # Device Status commands
    def setDevice(self, data):
        if data == '01011':
            self.image['image'] = self.img1011
            self.image['text'] = ''
            self.image.ttp.text = 'WSPR TX LP1 detected'
        elif data == '01012':
            self.image['image'] = self.img1012
            self.image['text'] = ''
            self.image.ttp.text = 'WSPR TX Desktop detected'
        elif data == '01017':
            self.image['image'] = self.img1017
            self.image['text'] = ''
            self.image.ttp.text = 'WSPR Mini detected'
        else:
            self.image['image'] = self.unknown
            self.image['text'] = 'Device Unknown'
            self.image['compound'] = CENTER
            self.image['wraplength'] = 50
            self.image['fg'] = 'red'
            self.image.ttp.text = 'Unknown device detected'

    def setHardwareVer(self, data):
        self.hardwareVer.set(data)
    def setHardwareRev(self, data):
        self.hardwareRev.set(data)
    def setFirmwareVer(self, data):
        self.firmwareVer.set(data)
    def setFirmwareRev(self, data):
        self.firmwareRev.set(data)
    def setFrequency(self, data):
        self.v = '{0:12.2f}'.format(int(data)/100.0)
        self.frequency.set(self.v[0:3]+' '+self.v[3:6]+' '+self.v[6:])
    def tx(self, onoff):
        if onoff == 0:
            self.txon.config(bg = 'grey80')
            self.txoff.config(bg = 'green')
        else:
            self.txon.config(bg = 'red')
            self.txoff.config(bg = 'grey80')
    def program(self, mode):
        if mode == 0:
            self.beacon.config(bg = 'grey80')
            self.siggen.config(bg = 'grey80')
            self.idle.config(bg = 'green')
        elif mode == 1:
            self.beacon.config(bg = 'green')
            self.siggen.config(bg = 'grey80')
            self.idle.config(bg = 'grey80')
        else:
            self.beacon.config(bg = 'grey80')
            self.siggen.config(bg = 'green')
            self.idle.config(bg = 'grey80')

    # GPS Status commands
    def setPosition(self, maidenhead):
        self.position.set(maidenhead)
    def updateTime(self, time):
        self.curtime.set(time)
        self.mirror.time = time
    def satdata(self, data):
        #Clear previous plot points
        if len(self.points)>0:
            for self.point in self.points:
                self.plot.delete(self.point)
        self.points = []
        self.snrList = []
        
        # Add new point for each bird
        for self.sat in data:
            self.line = self.sat.split()
            if len(self.line)<4:
                continue
            self.n, self.az, self.el, self.snr = self.line[0], self.line[1], self.line[2], self.line[3]
            
            # Make a list of the top 4 SNRs
            if not (self.n.isdigit() and self.az.isdigit() and self.el.isdigit() and self.snr.isdigit()):
                continue
            self.snrList.append(int(self.snr))
            if(len(self.snrList)>4): 
                self.snrList.sort(reverse=True)
                self.snrList.pop()
                
            #convert polar to cartesian
            self.rho = 110*(90-int(self.el))/90 # The plot radius is 110
            self.theta = (int(self.az)-90) * math.pi/180.0
            self.x = 120+int(self.rho * math.cos(self.theta)) # The canvas is 240x240, so 120
            self.y = 120+int(self.rho * math.sin(self.theta)) #   pushes it into the middle
            self.color = 'white'
            if self.snr.isdigit():
                #self.quality = int(self.snr)*2+57
                #if self.quality > 255: self.quality = 255
                #self.color = '#00'+'{0:02x}'.format(self.quality)+'00'
                self.quality = int(self.snr)
                if self.quality < 3:    # 0-2 do not display (I don't see and birds with 2dB SNR)
                    continue
                elif self.quality < 17: # 3 - 16 = red
                    self.color = 'red'
                elif self.quality < 25: # 17 - 24 = yellow
                    self.color = 'yellow'
                elif self.quality < 33: # 25 - 32 = dark green
                    self.color = 'dark green'
                else:
                    self.color = 'green' # 33 and over is green
                    
            self.point = self.plot.create_oval(self.x-5, self.y-5, self.x+5, self.y+5, fill = self.color, outline = 'black')
            self.points.append(self.point)
            CreateCanvasTip(self.plot,self.point,'Sat {} Az={} El={} SNR={}'.format(self.n,self.az,self.el,self.snr))

        _q=0
        for _snr in self.snrList: _q+=_snr
        #                # Always dividing by 4 birds -- if there are less, the rest are 0
        #self.q = 2*_q/4 # Multiply by 2, becuase an SNR of 50 is about as good as it gets.
        #                # This can/should be modified to something more interesting, maybe.
        self.q = (_q - 15) * 100 / 36 # "The linear Signal Quality meter is 0 when average SNR is 15dB or lower 
        if self.q > 100: self.q = 100 # and 100%  when average is 51dB or more" - Harry
        elif self.q < 0: self.q = 0
        self.signal.set(self.q)
        if self.q < 20:
            self.signal_style.configure('signal.Horizontal.TProgressbar', troughcolor = 'white', background = 'red') 
        elif self.q < 40:
            self.signal_style.configure('signal.Horizontal.TProgressbar', troughcolor = 'white', background = 'yellow')
        elif self.q < 60:
            self.signal_style.configure('signal.Horizontal.TProgressbar', troughcolor = 'white', background = 'blue')
        else:
            self.signal_style.configure('signal.Horizontal.TProgressbar', troughcolor = 'white', background = 'green')
        if self.q < 30:
            self.signal_style.configure('signal.Horizontal.TProgressbar', text='{} %'.format(self.q), foreground='black')
        elif self.q < 60:
            self.signal_style.configure('signal.Horizontal.TProgressbar', text='{} %'.format(self.q), foreground='grey50')
        else:
            self.signal_style.configure('signal.Horizontal.TProgressbar', text='{} %'.format(self.q), foreground='white')
            
    # Log commands
    def logInsert(self, msg):
        self.log.insert(END, msg)
        self.log.see(END)


###############################################################################
#### Controller
###############################################################################
#
# The Controller receives input from the user or other events, validates them,
# and converts them into commands for the Model and View according to the
# application logic.
#
# The Controller is where the Application Logic is implemented.  It will
# determine:
# - Any specific machine-dependant operations
# - What actions to take from user input
#
class Controller():
    
    def __init__(self):
        self.view = self
        self.model = self
        self.sats = []
        self.fq = 100000000
        self.rxChars = 0
        self.handlers = {'CCM':self.handleCCM, 'OTP':self.handleOTP,
                         'OSM':self.handleOSM, 'OBD':self.handleOBD,
                         'OLC':self.handleOLC, 'OPW':self.handleOPW,
                         
                         'DCS':self.handleDCS, 'DL4':self.handleDL4,
                         'DPD':self.handleDPD, 'DNM':self.handleDNM,
                         'DGF':self.handleDGF,
              
                         'FPN':self.handleFPN, 'FHV':self.handleFHV,
                         'FHR':self.handleFHR, 'FSV':self.handleFSV,
                         'FSR':self.handleFSR, 'FRF':self.handleFRF,
                         'FLP':self.handleFLP,

                         'GL4':self.handleGL4,
                         'GTM':self.handleGTM, 'GLC':self.handleGLC,
                         'GSI':self.handleGSI, 'TFQ':self.handleTFQ,
                         'TON':self.handleTON, 'MPS':self.handleMPS,
                         'MIN':self.handleMIN, 'LPI':self.handleLPI,
                         'MVC':self.handleMVC, 'TBN':self.handleTBN,
                         'TWS':self.handleTWS, 'TCC':self.handleTCC}  
    

    ################################################
    # Controller: Event handlers from View 
    ################################################
    # WSPR Configuration tab
    def startPressed(self):
        self.model.sendPort('CCM','S W')
    def stopPressed(self):
        self.model.sendPort('CCM','S N')

    def bandCheck(self):
        for self.band in range(len(self.model.bands())):
            if self.view.enable[self.band].get() == 1:
                self.model.sendPort('OBD', 'S {0:02d} E'.format(self.band))
            else:
                self.model.sendPort('OBD', 'S {0:02d} D'.format(self.band))

    def changeLocation(self, *args):
        self.v = self.view.location.get()
        self.model.sendPort('DL4', 'S '+self.v)
    def quitButtonPressed(self):
        self.parent.destroy()
    def addButtonPressed(self):
        self.view.setLabel_text(self.view.entry_text.get())
        self.addToList(self.view.entry_text.get())
    def callUpdate(self, *args):
        self.v = self.view.call.get()
        if len(self.v) > 6:
            self.view.call.set(self.v[:6])
        else:
            self.setCall(self.v)
        self.model.sendPort('DCS', 'S '+self.v)
    def pauseUpdate(self, *args):
        self.t = self.view.pauseTime.get()
        if self.t > 99999: # Only allowed 5 digits
            self.model.sendPort('OTP', 'G')
        else:
            self.model.sendPort('OTP', 'S {0:05d}'.format(self.t))
    def rpamGPS(self, *args):
        self.model.sendPort('OLC', 'S G')
    def rpamManual(self, *args):
        self.model.sendPort('OLC', 'S M')
    def rpmodeNormal(self, *args):
        self.model.sendPort('OPW', 'S N')
    def rpmodeAltitude(self, *args):
        self.model.sendPort('OPW', 'S A')
    def setBoot(self,*args):
        b = self.view.boot.get()
        self.model.sendPort('OSM','S '+b)
    def rpwrUpdate(self, *args):
        self.t = self.view.rpwr.get()
        self.v = int(self.t)
        self.model.sendPort('DPD', 'S {0:02d}'.format(self.v))

    # Signal Generator tab
    def addFQ(self,add):
        t = self.fq + add
        if t > 100000000000:
            t -= 100000000000
        self.fq = t
        self.model.sendPort('DGF','S '+'{0:012d}'.format(t))
        self.view.setFQ('{0:012d}'.format(t))
    def subFQ(self,sub):
        t = self.fq - sub
        if t < 0:
            t = 1
        self.fq = t
        self.model.sendPort('DGF','S '+'{0:012d}'.format(t))
        self.view.setFQ('{0:012d}'.format(t))
    def up100M(self):
        self.addFQ(10000000000)
    def up10M(self):
        self.addFQ(1000000000)
    def up1M(self):
        self.addFQ(100000000)
    def up100k(self):
        self.addFQ(10000000)
    def up10k(self):
        self.addFQ(1000000)
    def up1k(self):
        self.addFQ(100000)
    def up100Hz(self):
        self.addFQ(10000)
    def up10Hz(self):
        self.addFQ(1000)
    def up1Hz(self):
        self.addFQ(100)
    def up10c(self):
        self.addFQ(10)
    def up1c(self):
        self.addFQ(1)
    def down100M(self):
        self.subFQ(10000000000)
    def down10M(self):
        self.subFQ(1000000000)
    def down1M(self):
        self.subFQ(100000000)
    def down100k(self):
        self.subFQ(10000000)
    def down10k(self):
        self.subFQ(1000000)
    def down1k(self):
        self.subFQ(100000)
    def down100Hz(self):
        self.subFQ(10000)
    def down10Hz(self):
        self.subFQ(1000)
    def down1Hz(self):
        self.subFQ(100)
    def down10c(self):
        self.subFQ(10)
    def down1c(self):
        self.subFQ(1)

    def startGenerator(self):
        self.model.sendPort('CCM','S S')
    # Stop button is same as on the WSPR tab
        
    # Serial tab
    def selectPort(self):
        if self.model.portName == 'None':
            self.portName = self.view.portName.get()       # fetch the selected new port name
            self.model.portName = self.portName      # request to set it on the model
            self.view.serialButton.config(text = "Close")
        else:
            self.model.portName = 'None'
            self.view.serialButton.config(text = "Select")
        self.view.currentPort.set(self.model.portName) # set the View based on the Model's state
        self.view.serialOK(False)

    # Right side
    def nameUpdate(self, *args):
        self.n = self.view.name.get()
        self.model.sendPort('DNM', 'S '+self.n)
            
    # Bottom row
    def saveSettingsPressed(self):
        self.view.saveButton.config(bg='blue')
        self.model.sendPort('CSE', 'S')

    def setDebug(self):
        self.view.setDebug(self.view.debug.get())
            
    def setCRLF(self):
        pass

    def sendPressed(self):
        d = self.view.sendCommands.get()
        if self.view.CRLF.get():
            d = d + '\r\n'
        self.model.sendPortRaw('',d)
        # clear it?
        #self.view.sendCommands.set('')
            

    ################################################
    # Controller: Messages from Model
    ################################################
    def handleMessage(self, msg):
        if len(msg)<5:
            sys.stderr.write('Short message: '+msg)
            return
        if msg[0] == '{' and msg[4] == '}':
            self.setPortStatus(True)
        self.data = ''
        if len(msg)>5:
            self.data = msg[6:]
            if msg[5] != ' ': # MIN seems to forget to add this space sometimes
                self.data = msg[5:]
        self.resp = msg[1:4]
        self.rnum = self.resp in self.handlers.keys()
        if self.rnum == False:
            sys.stderr.write('response: {} is unknown.  Need to upgrade?\n'.format(msg))
            return
        else:
            self.handlers[self.resp](self.data)

    def handleCCM(self, data): # Current Mode
        if len(data)<1:
            sendport('CCM','G')
            return
        if data[0] == 'N':
            self.view.setStopped()
            self.view.program(0)
        elif data[0] == 'W':
            self.view.setRunning()
            self.view.program(1)
        elif data[0] == 'S':
            self.view.setGenerating()
            self.view.program(2)
        else:
            sys.stderr.write('unknown CCM received: '+data)
            self.model.sendPort('CCM','G')
    def handleOTP(self, data): # Option TX Pause
        if data.isdigit():
            self.v = int(data)
            self.view.pauseTime.set(self.v)
        else:
            sys.stderr.write('unknown OTP received: '+data)
            self.model.sendPort('OTP','G')
    def handleOSM(self, data): # Option StartMode
        if data[0] in 'NWS':
            self.view.boot.set(data[0])
        else:
            sys.stderr.write('unknown OSM received: '+data)
            self.model.sendPort('OSM','G')
    def handleOBD(self, data):
        self.filter = int(data[0:2])
        if data[3] == 'E':           
            self.view.enable[self.filter].set(1)
            self.view.progress[self.filter].configure(style = 'WSPR.Horizontal.TProgressbar')
        elif data[3] == 'D':
            self.view.enable[self.filter].set(0)
            self.view.progress[self.filter].configure(style = 'blank.Horizontal.TProgressbar')
        else:
            sys.stderr.write('unknown OBD response:'+data)
            self.model.sendPort('OBD','G')
    def handleOLC(self, data):
        if data[0] == 'G':
            self.view.rpam.set('G')
        elif data[0] == 'M':
            self.view.rpam.set('M')
        else:
            sys.stderr.write('unknown OLC response:'+data)
            self.model.sendPort('OLC','G')            
    def handleOPW(self, data):
        if data[0] == 'N':
            self.view.rpmode.set('N')
        elif data[0] == 'A':
            self.view.rpmode.set('A')
        else:
            sys.stderr.write('unknown OPW response:'+data)
            self.model.sendPort('OPW','G')
    def handleDCS(self, data):
        self.view.call.set(data) # I don't check this
    def handleDL4(self, data):
        self.view.location.set(data) # I don't check this
    def handleDPD(self, data):
        if data.isdigit():
            self.powerlevel = int(data)
            if self.powerlevel > 60: self.powerlevel = 60
            self.view.rpwr.set(str(self.powerlevel))
        else:
            self.model.sendPort('DPD','G')
    def handleDNM(self, data):
        self.view.name.set(data) # I don't check this
    def handleDGF(self, data):
        if len(data) == 12:
            if data.isdigit():
                self.fq = int(data)
                self.view.setFQ(self.data)
                return
        sys.stderr.write('Bad DGF data: '+data)
        self.model.sendPort('DGF','G')
        
    def handleFPN(self, data):
        self.view.setDevice(data) # I don't check this
    def handleFHV(self, data): # Hardware Version
        self.view.setHardwareVer(data) # I don't check this
    def handleFHR(self, data): # Hardware Revision
        self.view.setHardwareRev(data) # I don't check this
    def handleFSV(self, data): # Firmware Version
        self.view.setFirmwareVer(data) # I don't check this
    def handleFSR(self, data): # Firmware Revision
        self.view.setFirmwareRev(data) # I don't check this
    def handleFRF(self, data): # Reference OSC frequency
        pass                   # Not Used, it seems
    def handleFLP(self, data):
        self.v = data[2:]
        if not self.v.isdigit():
            sys.stderr.write('Invalid LPF requested: '+band)
            return -1
        self.filter = int(self.v)
        if self.filter > len(self.model.bands()):
            sys.stderr.write('Device reported an unsupported LPF with an ID of {}.'.format(self.filter))
            return -1
        self.view.installLP(self.filter)
        
    def handleGL4(self, data): # GPS locator 4 char Maidenhead
        self.view.setPosition(data) # I don't check this
    def handleGTM(self, data): # GPS Time
        self.view.updateTime(data) # I don't check this
        self.view.r3l5.config(fg='black')
        if len(self.sats)>0:
            self.view.satdata(self.sats)
            self.sats = []
    def handleGLC(self, data): # GPS Locked - not sure what to do with this
        if data[0] == 'F':
            self.view.locked.config(text = 'No Position Lock', font = ('Arial Italic',18))
            self.view.r3l6.config(fg='grey80')
        elif data[0] == 'T':
            self.view.locked.config(text = 'Position Lock', font = ('Arial',18))
            self.view.r3l6.config(fg='black')
        else:
            sys.stderr.write('unknown GLC response:'+data)
    def handleGSI(self, data): # Info for the GPS plot
        self.sats.append(data) # I don't check this
    def handleTFQ(self, data): # Current frequency
        if data.isdigit():
            self.view.setFrequency(data)
        else:
            sys.stderr.write('unknown TFQ response: '+data)
    def handleTON(self, data): # Transmit on? (T/F)
        if data[0] == 'T':
            self.view.tx(1)
        elif data[0] == 'F':
            self.view.tx(0)
        else:
            sys.stderr.write('unknown TON response:'+data)
            self.model.sendPort('TON','G')
    def handleMPS(self, data): # Progress while paused
        self.view.setActive(-1,'black')
        if data.isdigit():
            self.view.setProgress(-1,int(data))
        else:
            sys.stderr.write('unknown MPS response: '+data)
    def handleMIN(self, data): # Informational Messages
        self.view.logInsert(data)
        self.setPortStatus(True)
        self.view.saveButton.config(bg = 'grey80')
    def handleLPI(self, data): # Low pass filter set
        pass                   # Not used, AFAIK (maybe the 'mid' in the name?)
    def handleMVC(self, data): # MicroController VCC Voltage - not used
        pass                   # Not used
    def handleTBN(self, data): # Next transmitting band 
        if not data.isdigit():
            sys.stderr.write('invalid TBN band data:: '+data)
            return -1
        self.view.setActive(int(data),'black')
    def handleTWS(self, data): # Transmitting band status
        if not data[0:2].isdigit():
            sys.stderr.write('invalid TWS band data:: '+data)
            return -1
        self.v = int(data[0:2])        
        self.view.setActive(self.v,'red') # This should be changed to blinking, I think
        if data[3:6].isdigit():
            self.view.setProgress(self.v,int(data[3:6]))
        else:
            sys.stderr.write('unknown MPS response: '+data)
    def handleTCC(self, data): # End of cycle, use it to clear
        self.view.setProgress(-1,0)

        
    ################################################
    # Controller internal functions
    ################################################
    def updateStatus(self):
        for self.cmd in ['CCM', 'OTP', 'OSM', 'OBD', 'OLC', 'OPW', 'DCS',
                         'DL4', 'DPD', 'DNM', 'DGF', 'FPN', 'FHV', 'FHR',
                         'FSV', 'FSR', 'FRF', 'FLP' ]:
            self.model.sendPort(self.cmd, 'G')
            self.count = 0
            while self.count < 100:
                self.msg = self.model.readPort()
                self.rxChars += len(self.msg)
                self.view.traceInsert(self.msg)
                self.view.rxChars.set(self.rxChars)
                if len(self.msg)>2:
                    self.handleMessage(self.msg)
                    if self.cmd == self.msg[1:4]:
                        break
                    self.count += 1

    def setPortStatus(self,state):
        if state:
            self.view.serialOK(True)
        else:
            self.view.serialOK(False)
        
    def setCall(self, call):
        self.call = call
        self.model.sendPort('CCM', 'S N')
        self.model.sendPort('DCS', 'S '+call)

    def drive(self): # Main controller loop
        while True:
            if self.model.portName != 'None':
                self.buff = self.model.readPort()
                if len(self.buff)>0:
                    self.rxChars += len(self.buff)
                    self.view.traceInsert(self.buff)
                    self.view.rxChars.set(self.rxChars)
                    self.handleMessage(self.buff)
                if self.buff[1:4] == 'MIN':
                    self.updateStatus()
            try:
                self.view.root.update_idletasks()
            except TclError:
                break;
            try:
                self.view.root.update()
            except TclError:
                break;

###############################################################################
##### Main
###############################################################################
def main(args):
    global debug
    debug = False
    port = ''
    
    def usage(name):
        print('Usage: {} [-d] [-p <serialport>] [OPTIONS]\nOptions:\n'.format(name)+
              '    -d, --debug                  Provide debug information on stdout.\n'+
              '    -h, --help                   Print this help message.\n'+
              '    -p, --port = SERIALPORT      Serial port the device is on.\n')

    # Begin
    myname = args[0]
    try:
        optlist, args = getopt.getopt(args[1:], 'dhp:', ['debug', 'help', 'port = '])
        for (o, v) in optlist:
            if   o == '-h' or o == '--help':
                usage(myname)
                sys.exit(0)
            elif o == '-p' or o == '--port':
                port = v
            elif o == '-d' or o == '--debug':
                if debug:
                    print("HI")
                debug = True
    except getopt.GetoptError as e:
        sys.stderr.write('{}: {}\n'.format(myname, e.msg))
        usage(myname)
        sys.exit(1)

    controller = Controller()

    model = Model(controller)
    controller.model = model

    view  = View(controller)
    controller.view = view

    # Handle --port
    # We do more checking, because this was not discovered
    if port != '':
        if port[0:3] == 'COM':
            model.portName = port
            if model.portName == 'None':
                sys.stderr.write('{}: Port "{}" cannot be opened\n'.format(myname,port))
            view.currentPort.set(model.portName) # set the View based on the Model's state
            view.serialOK(False)
            if model.portName != 'None':
                view.serialButton.config(text = "Close")
        elif os.path.exists (port):
            if stat.S_ISCHR(os.stat(port).st_mode):
                model.portName = port
                if model.portName == 'None':
                    sys.stderr.write('{}: Port "{}" cannot be opened\n'.format(myname,port))
                view.currentPort.set(model.portName) # set the View based on the Model's state
                view.serialOK(False)
                if model.portName != 'None':
                    view.serialButton.config(text = "Close")
            else:
                sys.stderr.write('{}: file "{}" is not a serial port\n'.format(myname,port))
                sys.exit(1)
        else:
            sys.stderr.write('{}: file "{}" does not exist.\n'.format(myname,port))
            sys.exit(1)
        view.portName.set(port)

    # Enter polling and event-driven loop
    controller.drive()
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)
