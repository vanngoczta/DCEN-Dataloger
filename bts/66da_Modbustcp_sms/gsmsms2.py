import time
from datetime import datetime, timedelta, tzinfo
import sys, re, logging, weakref, time, threading, abc, codecs
import serial # pyserial: http://pyserial.sourceforge.net
sys.path.append('/home/pi/bts/gsmmodem')
from util import SimpleOffsetTzInfo, lineStartingWith, allLinesMatchingPattern, parseTextModeTimeStr,lineMatching
from pdu import encodeSmsSubmitPdu, decodeSmsPdu

PYTHON_VERSION = sys.version_info[0]
if PYTHON_VERSION >= 3:
    xrange = range
    dictValuesIter = dict.values
    dictItemsIter = dict.items
else: #pragma: no cover
    dictValuesIter = dict.itervalues
    dictItemsIter = dict.iteritems
    
class GsmModemException(Exception):
    """ Base exception raised for error conditions when interacting with the GSM modem """


class TimeoutException(GsmModemException):
    """ Raised when a write command times out """
    
class CommandError(GsmModemException):
    """ Raised if the modem returns an error in response to an AT command
     
    May optionally include an error type (CME or CMS) and -code (error-specific).
    """
    
    _description = ''
    
    def __init__(self, command=None, type=None, code=None):
        self.command = command
        self.type = type
        self.code = code
        if type != None and code != None:
            super(CommandError, self).__init__('{0} {1}{2}'.format(type, code, ' ({0})'.format(self._description) if len(self._description) > 0 else ''))
        elif command != None:
            super(CommandError, self).__init__(command)
        else:
            super(CommandError, self).__init__()

class Sms(object):
    """ Abstract SMS message base class """
    #__metaclass__ = abc.ABCMeta

    # Some constants to ease handling SMS statuses
    STATUS_RECEIVED_UNREAD = 0
    STATUS_RECEIVED_READ = 1
    STATUS_STORED_UNSENT = 2
    STATUS_STORED_SENT = 3
    STATUS_ALL = 4
    # ...and a handy converter for text mode statuses
    TEXT_MODE_STATUS_MAP = {'REC UNREAD': STATUS_RECEIVED_UNREAD,
                            'REC READ': STATUS_RECEIVED_READ,
                            'STO UNSENT': STATUS_STORED_UNSENT,
                            'STO SENT': STATUS_STORED_SENT,
                            'ALL': STATUS_ALL}

    def __init__(self, number, text, smsc=None):
        self.number = number
        self.text = text
        self.smsc = smsc
        
class SentSms(Sms):
    """ An SMS message that has been sent (MO) """
        
    ENROUTE = 0 # Status indicating message is still enroute to destination
    DELIVERED = 1 # Status indicating message has been received by destination handset
    FAILED = 2 # Status indicating message delivery has failed

    def __init__(self, number, text, reference, smsc=None):
        super(SentSms, self).__init__(number, text, smsc)
        self.report = None # Status report for this SMS (StatusReport object)
        self.reference = reference
        
    @property
    def status(self):
        """ Status of this SMS. Can be ENROUTE, DELIVERED or FAILED
        
        The actual status report object may be accessed via the 'report' attribute
        if status is 'DELIVERED' or 'FAILED'
        """
        if self.report == None:
            return SentSms.ENROUTE
        else:
            return SentSms.DELIVERED if self.report.deliveryStatus == StatusReport.DELIVERED else SentSms.FAILED
        
class StatusReport(Sms):
    """ An SMS status/delivery report
    
    Note: the 'status' attribute of this class refers to this status report SM's status (whether
    it has been read, etc). To find the status of the message that caused this status report,
    use the 'deliveryStatus' attribute.
    """
        
    DELIVERED = 0 # SMS delivery status: delivery successful
    FAILED = 68 # SMS delivery status: delivery failed
    
    def __init__(self, gsmModem, status, reference, number, timeSent, timeFinalized, deliveryStatus, smsc=None):
        super(StatusReport, self).__init__(number, None, smsc)
        self._gsmModem = weakref.proxy(gsmModem)
        self.status = status
        self.reference = reference
        self.timeSent = timeSent
        self.timeFinalized = timeFinalized
        self.deliveryStatus = deliveryStatus
        
class ReceivedSms(Sms):
    """ An SMS message that has been received (MT) """
    
    def __init__(self, SerialComms, status, number, time, text, smsc=None):
        super(ReceivedSms, self).__init__(number, text, smsc)
        self._gsmModem = weakref.proxy(SerialComms)
        self.status = status
        self.time = time
        
    def reply(self, message):
        """ Convenience method that sends a reply SMS to the sender of this message """
        return self._gsmModem.SendSMS(self.number, message)
    
class SerialComms(object):
    """ Wraps all low-level serial communications (actual read/write operations) """
    
    log = logging.getLogger('gsmmodem.serial_comms.SerialComms')
    # Used for parsing AT command errors
    CM_ERROR_REGEX = re.compile(r'^\+(CM[ES]) ERROR: (\d+)$')
    # Used for parsing signal strength query responses
    CSQ_REGEX = re.compile(r'^\+CSQ:\s*(\d+),')
    # Used for parsing caller ID announcements for incoming calls. Group 1 is the number
    CLIP_REGEX = re.compile(r'^\+CLIP:\s*"(\+{0,1}\d+)",(\d+).*$')
    # Used for parsing new SMS message indications
    CMTI_REGEX = re.compile(r'^\+CMTI:\s*"([^"]+)",(\d+)$')
    #'+CMT: "+84915086942",,"15/08/28,15:52:03+28"', 'Test?']
    CMT_REGEX = re.compile(r'^\+CMT: "(.+?)",.*?,"(.+?)".*?$')
    # Used for parsing SMS message reads (text mode)
    CMGR_SM_DELIVER_REGEX_TEXT = None
    # Used for parsing SMS status report message reads (text mode)
    CMGR_SM_REPORT_REGEXT_TEXT = None
    # Used for parsing SMS message reads (PDU mode)
    CMGR_REGEX_PDU = None
    # Used for parsing USSD event notifications
    CUSD_REGEX = re.compile(r'^\+CUSD:\s*(\d),"(.*)",(\d+)$', re.DOTALL)
    # Used for parsing SMS status reports
    CDSI_REGEX = re.compile(r'\+CDSI:\s*"([^"]+)",(\d+)$')
    
    # End-of-line read terminator
    RX_EOL_SEQ = '\r\n'
    # End-of-response terminator
    RESPONSE_TERM = re.compile(r'^OK|ERROR|(\+CM[ES] ERROR: \d+)|(COMMAND NOT SUPPORT)$')
    # Default timeout for serial port reads (in seconds)
    timeout = 1
        
    def __init__(self, notifyCallbackFunc=None, incomingCallCallbackFunc =None,smsReceivedCallbackFunc=None,fatalErrorCallbackFunc=None, smsStatusReportCallback=None):
        """ Constructor
         
        @param fatalErrorCallbackFunc: function to call if a fatal error occurs in the serial device reading thread
        @type fatalErrorCallbackFunc: func
        """
        notifyCallbackFunc=self._handleModemNotification
        self.incomingCallCallback = incomingCallCallbackFunc or self._placeholderCallback
        self.smsReceivedCallback = smsReceivedCallbackFunc or self._placeholderCallback
        self.smsStatusReportCallback = smsStatusReportCallback or self._placeholderCallback
        self.alive = False

        self._responseEvent = None # threading.Event()
        self._expectResponseTermSeq = None # expected response terminator sequence
        self._response = None # Buffer containing response to a written command
        self._notification = [] # Buffer containing lines from an unsolicited notification from the modem
        # Reentrant lock for managing concurrent write access to the underlying serial port
        self._txLock = threading.RLock()
        
        self.notifyCallback = notifyCallbackFunc or self._placeholderCallback        
        self.fatalErrorCallback = fatalErrorCallbackFunc or self._placeholderCallback
        # Flag indicating whether caller ID for incoming call notification has been set up
        self._callingLineIdentification = False
        # Flag indicating whether incoming call notifications have extended information
        self._extendedIncomingCallIndication = False
        # Current active calls (ringing and/or answered), key is the unique call ID (not the remote number)
        self.activeCalls = {}
        # Dict containing sent SMS messages (for auto-tracking their delivery status)
        self.sentSms = weakref.WeakValueDictionary()
        self._ussdSessionEvent = None # threading.Event
        self._ussdResponse = None # gsmmodem.modem.Ussd
        self._smsStatusReportEvent = None # threading.Event
        self._dialEvent = None # threading.Event
        self._dialResponse = None # gsmmodem.modem.Call
        self._waitForAtdResponse = True # Flag that controls if we should wait for an immediate response to ATD, or not
        self._waitForCallInitUpdate = True # Flag that controls if we should wait for a ATD "call initiated" message
        self._callStatusUpdates = [] # populated during connect() - contains regexes and handlers for detecting/handling call status updates
        self._mustPollCallStatus = False # whether or not the modem must be polled for outgoing call status updates
        self._pollCallStatusRegex = None # Regular expression used when polling outgoing call status
        self._writeWait = 0 # Time (in seconds to wait after writing a command (adjusted when 515 errors are detected)
        self._smsTextMode = True # Storage variable for the smsTextMode property
        self._smscNumber = None # Default SMSC number
        self._smsRef = 0 # Sent SMS reference counter
        self._smsMemReadDelete = None # Preferred message storage memory for reads/deletes (<mem1> parameter used for +CPMS)
        self._smsMemWrite = None # Preferred message storage memory for writes (<mem2> parameter used for +CPMS)
        self._smsReadSupported = True # Whether or not reading SMS messages is supported via AT commands
        self.connected=True   # co ket noi USB GSM hay ko
    def connect(self, port, baudrate):
        print("Connects to the device and starts the read thread USB3G" )
        try:
            self.serial = serial.Serial(port, baudrate=115200,timeout=5)
        except:
            self.connected=False
            self.log.warning('Not USB3G device')
            return
        # Start read thread
        self.alive = True 
        self.rxThread = threading.Thread(target=self._readLoop)
        self.rxThread.daemon = True
        self.rxThread.start()

    def close(self):
        """ Stops the read thread, waits for it to exit cleanly, then closes the underlying serial port """        
        self.alive = False
        self.rxThread.join()
        self.serial.close()

    def setsms(self):
        """ Opens the port and initializes the modem and SIM card
         
        @param pin: The SIM card PIN code, if any
        @type pin: str
        
        @raise PinRequiredError: if the SIM card requires a PIN but none was provided
        @raise IncorrectPinError: if the specified PIN is incorrect
        """
        #self.log.info('Connecting to modem on port %s at %dbps', self.port, self.baudrate)        
        #super(GsmModem, self).connect()
        # Send some initialization commands to the modem
        
        try:
            self.write('ATZ\r') # reset configuration
        except CommandError:
            # Some modems require a SIM PIN at this stage already; unlock it now
            # Attempt to enable detailed error messages (to catch incorrect PIN error)
            # but ignore if it fails
            self.write('AT+CMEE=1\r', parseError=False)            
            #self._unlockSim(None)
            pinCheckComplete = True
            self.write('ATZ\r') # reset configuration        
        else:
            pinCheckComplete = False
        self.write('ATE0\r') # echo off
        try:
            cfun = int(lineStartingWith('+CFUN:', self.write('AT+CFUN?\r'))[7:]) # example response: +CFUN: 1
            if cfun != 1:
                self.write('AT+CFUN=1\r')
        except CommandError:
            pass # just ignore if the +CFUN command isn't supported
                
        self.write('AT+CMEE=1\r') # enable detailed error messages (even if it has already been set - ATZ may reset this)
        #if not pinCheckComplete:
        #    self._unlockSim(None)

        # Get list of supported commands from modem
        '''commands = self.supportedCommands

        # Device-specific settings
        callUpdateTableHint = 0 # unknown modem
        enableWind = False
        if commands != None:
            if '^CVOICE' in commands:
                self.write('AT^CVOICE=0\r', parseError=False) # Enable voice calls
            if '+VTS' in commands: # Check for DTMF sending support
                Call.dtmfSupport = True
            elif '^DTMF' in commands:
                # Huawei modems use ^DTMF to send DTMF tones
                callUpdateTableHint = 1 # Huawei
            if '+WIND' in commands:
                callUpdateTableHint = 2 # Wavecom
                enableWind = True
            elif '+ZPAS' in commands:
                callUpdateTableHint = 3 # ZTE
        else:
            # Try to enable general notifications on Wavecom-like device
            enableWind = True

        if enableWind:
            try:
                wind = lineStartingWith('+WIND:', self.write('AT+WIND?\r')) # Check current WIND value; example response: +WIND: 63
            except CommandError:
                # Modem does not support +WIND notifications. See if we can detect other known call update notifications
                pass
            else:
                # Enable notifications for call setup, hangup, etc
                if int(wind[7:]) != 50:
                    self.write('AT+WIND=50\r')
                callUpdateTableHint = 2 # Wavecom

        # Attempt to identify modem type directly (if not already) - for outgoing call status updates
        if callUpdateTableHint == 0:
            if self.manufacturer.lower() == 'huawei':
                callUpdateTableHint = 1 # huawei
            else:
                # See if this is a ZTE modem that has not yet been identified based on supported commands
                try:
                    self.write('AT+ZPAS?\r')
                except CommandError:
                    pass # Not a ZTE modem
                else:
                    callUpdateTableHint = 3 # ZTE
        # Load outgoing call status updates based on identified modem features
        if callUpdateTableHint == 1:
            # Use Hauwei's ^NOTIFICATIONs
            self.log.info('Loading Huawei call state update table')
            self._callStatusUpdates = ((re.compile(r'^\^ORIG:(\d),(\d)$'), self._handleCallInitiated),
                                       (re.compile(r'^\^CONN:(\d),(\d)$'), self._handleCallAnswered),
                                       (re.compile(r'^\^CEND:(\d),(\d),(\d)+,(\d)+$'), self._handleCallEnded))
            self._mustPollCallStatus = False
            # Huawei modems use ^DTMF to send DTMF tones; use that instead
            Call.DTMF_COMMAND_BASE = '^DTMF={cid},'
            Call.dtmfSupport = True
        elif callUpdateTableHint == 2:
            # Wavecom modem: +WIND notifications supported
            self.log.info('Loading Wavecom call state update table')
            self._callStatusUpdates = ((re.compile(r'^\+WIND: 5,(\d)$'), self._handleCallInitiated),
                                      (re.compile(r'^OK$'), self._handleCallAnswered),
                                      (re.compile(r'^\+WIND: 6,(\d)$'), self._handleCallEnded))
            self._waitForAtdResponse = False # Wavecom modems return OK only when the call is answered
            self._mustPollCallStatus = False
            if commands == None: # older modem, assume it has standard DTMF support
                Call.dtmfSupport = True
        elif callUpdateTableHint == 3: # ZTE
            # Use ZTE notifications ("CONNECT"/"HANGUP", but no "call initiated" notification)
            self.log.info('Loading ZTE call state update table')
            self._callStatusUpdates = ((re.compile(r'^CONNECT$'), self._handleCallAnswered),
                                       (re.compile(r'^HANGUP:\s*(\d+)$'), self._handleCallEnded),
                                       (re.compile(r'^OK$'), self._handleCallRejected))
            self._waitForAtdResponse = False # ZTE modems do not return an immediate  OK only when the call is answered
            self._mustPollCallStatus = False
            self._waitForCallInitUpdate = False # ZTE modems do not provide "call initiated" updates
            if commands == None: # ZTE uses standard +VTS for DTMF
                Call.dtmfSupport = True
        else:
            # Unknown modem - we do not know what its call updates look like. Use polling instead
            self.log.info('Unknown/generic modem type - will use polling for call state updates')
            self._mustPollCallStatus = True
            self._pollCallStatusRegex = re.compile('^\+CLCC:\s+(\d+),(\d),(\d),(\d),([^,]),"([^,]*)",(\d+)$')
            self._waitForAtdResponse = True # Most modems return OK immediately after issuing ATD

        # General meta-information setup
        self.write('AT+COPS=3,0\r') # Use long alphanumeric name format'''
        
         # SMS setup
        self.write('AT+CMGF={0}\r'.format(1 if self._smsTextMode else 0),waitForResponse=True,timeout=5) # Switch to text or PDU mode for SMS messages
        self._compileSmsRegexes()
        if self._smscNumber != None:
            self.write('AT+CSCA="{0}\r"'.format(self._smscNumber),waitForResponse=True,timeout=3) # Set default SMSC number
            currentSmscNumber = self._smscNumber
        else:
            currentSmscNumber = self.smsc
        # Some modems delete the SMSC number when setting text-mode SMS parameters; preserve it if needed
        if currentSmscNumber != None:
            self._smscNumber = None # clear cache
        self.write('AT+CSMP=49,167,0,0\r',waitForResponse=True,timeout=3) # Enable delivery reports
        # ...check SMSC again to ensure it did not change
        if currentSmscNumber != None and self.smsc != currentSmscNumber:
            self.smsc = currentSmscNumber
            
        # Set message storage, but first check what the modem supports - example response: +CPMS: (("SM","BM","SR"),("SM"))
        try:
            cpmsLine = lineStartingWith('+CPMS', self.write('AT+CPMS=?\r'))
        except CommandError:
            # Modem does not support AT+CPMS; SMS reading unavailable
            self._smsReadSupported = False
            self.log.warning('SMS preferred message storage query not supported by modem. SMS reading unavailable.')
        else:
            cpmsSupport = cpmsLine.split(' ', 1)[1].split('),(')
            # Do a sanity check on the memory types returned - Nokia S60 devices return empty strings, for example
            for memItem in cpmsSupport:
                if len(memItem) == 0:
                    # No support for reading stored SMS via AT commands - probably a Nokia S60
                    self._smsReadSupported = False
                    self.log.warning('Invalid SMS message storage support returned by modem. SMS reading unavailable. Response was: "%s"', cpmsLine)
                    break
            else:
                # Suppported memory types look fine, continue
                preferredMemoryTypes = ('"ME"', '"SM"', '"SR"')
                #preferredMemoryTypes = ('"SM"', '"ME"', '"SR"')
                cpmsItems = [''] * len(cpmsSupport)
                for i in range(len(cpmsSupport)):
                    for memType in preferredMemoryTypes:
                        if memType in cpmsSupport[i]:
                            if i == 0:
                                self._smsMemReadDelete = memType
                            cpmsItems[i] = memType
                            break
                self.write('AT+CPMS={0}\r'.format(','.join(cpmsItems))) # Set message storage
            del cpmsSupport
            del cpmsLine
        
        if self._smsReadSupported:
            try:
                self.write('AT+CNMI=2,1,0,2\r') # Set message notifications self.write('AT+CNMI=2,1,0,2\r')
            except CommandError:
                # Message notifications not supported
                self._smsReadSupported = False
                self.log.warning('Incoming SMS notifications not supported by modem. SMS receiving unavailable.')
                
    def _handleLineRead(self, line, checkForResponseTerm=True):
        #print 'sc.hlineread:',line
        if self._responseEvent and not self._responseEvent.is_set():
            # A response event has been set up (another thread is waiting for this response)
            self._response.append(line)
            if not checkForResponseTerm or self.RESPONSE_TERM.match(line):
                # End of response reached; notify waiting thread
                #print 'response:', self._response
                self.log.debug('response: %s', self._response)
                self._responseEvent.set()
                #print('response: %s', self._response)
        else:            
            # Nothing was waiting for this - treat it as a notification
            self._notification.append(line)
            if self.serial.inWaiting() == 0:
                # No more chars on the way for this notification - notify higher-level callback
                #print 'notification:', self._notification
                self.log.debug('notification: %s', self._notification)
                self.notifyCallback(self._notification)
                self._notification = []
                #print('notification: %s', self._notification)

    def _placeholderCallback(self, *args, **kwargs):
        """ Placeholder callback function (does nothing) """
        
    def _readLoop(self):
        """ Read thread main loop
        
        Reads lines from the connected device
        """
        try:
            readTermSeq = list(self.RX_EOL_SEQ)
            readTermLen = len(readTermSeq)
            rxBuffer = []
            while self.alive:
                data = self.serial.read(1).decode('utf-8')
                if data != '': # check for timeout
                    
                    rxBuffer.append(data)
                    #print (' RX:', rxBuffer)
                    if rxBuffer[-readTermLen:] == readTermSeq:                        
                        # A line (or other logical segment) has been read
                        line = ''.join(rxBuffer[:-readTermLen])
                        rxBuffer = []
                        if len(line) > 0:                          
                            #print ('calling handler')                      
                            self._handleLineRead(line)
                    elif self._expectResponseTermSeq:
                        if rxBuffer[-len(self._expectResponseTermSeq):] == self._expectResponseTermSeq:
                            line = ''.join(rxBuffer) 
                            rxBuffer = []
                            self._handleLineRead(line, checkForResponseTerm=False)
            #else:
            #    print('RX timeout>')
        except serial.SerialException as e:
            self.alive = False
            print('SerialException:',e)
            try:
                self.serial.close()
            except Exception: #pragma: no cover
                pass
            # Notify the fatal error handler
            self.fatalErrorCallback(e)
            
    def _unlockSim(self, pin):
        """ Unlocks the SIM card using the specified PIN (if necessary, else does nothing) """
        # Unlock the SIM card if needed
        if self.write('AT+CPIN?\r')[0] != '+CPIN: READY':
            if pin != None:
                self.write('AT+CPIN="{0}"\r'.format(pin))
            else:
                raise PinRequiredError('AT+CPIN')
            
    def write(self, data, waitForResponse=True, timeout=5, expectedResponseTermSeq=None):
        self.log.debug('write: %s', data)
        with self._txLock:            
            if waitForResponse:
                if expectedResponseTermSeq:
                    self._expectResponseTermSeq = list(expectedResponseTermSeq) 
                self._response = []
                self._responseEvent = threading.Event()                
                self.serial.write(data.encode())
                #print(data.encode())
                if self._responseEvent.wait(timeout):
                    self._responseEvent = None
                    self._expectResponseTermSeq = False
                    #print(self._response)
                    return self._response
                else: # Response timed out
                    self._responseEvent = None
                    self._expectResponseTermSeq = False
                    print('Response timed out')
                    raise TimeoutException()
            else:                
                self.serial.write(data.encode())
                
    def GetNetwork(self):
         # General meta-information setup
        self.write('AT+COPS=3,0\r',waitForResponse=True,timeout=3) # Use long alphanumeric name format
        """ @return: the name of the GSM Network Operator to which the modem is connected """
        copsMatch = lineMatching(r'^\+COPS: (\d),(\d),"(.+)",{0,1}\d*$', self.write('AT+COPS?\r',waitForResponse=True,timeout=3)) # response format: +COPS: mode,format,"operator_name",x
        if copsMatch:
            print(copsMatch.group(3))
            return copsMatch.group(3)

    def signalStrength(self):
        """ Checks the modem's cellular network signal strength
        
        @raise CommandError: if an error occurs
        
        @return: The network signal strength as an integer between 0 and 99, or -1 if it is unknown
        @rtype: int
        """
        csq = self.CSQ_REGEX.match(self.write('AT+CSQ\r',waitForResponse=True,timeout=3)[0])
        if csq:
            ss = int(csq.group(1))
            return ss if ss != 99 else -1
        else:
            raise CommandError()
        
    def open(self):
        self.write('ATZ\r',waitForResponse=True,timeout=3)
        self.write('AT+CMGF=1\r',waitForResponse=True,timeout=3)

    @property
    def supportedCommands(self):
        """ @return: list of AT commands supported by this modem (without the AT prefix). Returns None if not known """
        try:
            # AT+CLAC responses differ between modems. Most respond with +CLAC: and then a comma-separated list of commands
            # while others simply return each command on a new line, with no +CLAC: prefix
            response = self.write('AT+CLAC\r')
            if len(response) == 2: # Single-line response, comma separated
                commands = response[0]
                if commands.startswith('+CLAC'):
                    commands = commands[6:] # remove the +CLAC: prefix before splitting
                return commands.split(',')
            elif len(response) > 2: # Multi-line response
                return [cmd.strip() for cmd in response[:-1]]
            else:
                self.log.debug('Unhandled +CLAC response: {0}'.format(response))
                return None
        except CommandError:
            return None
        
    def imei(self):
        """ @return: The modem's serial number (IMEI number) """
        return self.write('AT+CGSN',waitForResponse=True,timeout=3)[0]
    
    '''def SendSMS(self, address, message):
        command = 'AT+CMGS="%s"\r'%address
        self.write(command, waitForResponse=True, timeout=5, expectedResponseTermSeq='> ')
        command = '%s\n'%message+chr(26)
        result = lineStartingWith('+CMGS:', self.write(command, waitForResponse=True, timeout=1)'''

    def SendSMS(self, destination, message,waitForDeliveryReport=False, deliveryTimeout=15):
        """ Send an SMS text message
        
        @param destination: the recipient's phone number
        @type destination: str
        @param text: the message text
        @type text: str
        @param waitForDeliveryReport: if True, this method blocks until a delivery report is received for the sent message
        @type waitForDeliveryReport: boolean
        @param deliveryReport: the maximum time in seconds to wait for a delivery report (if "waitForDeliveryReport" is True)
        @type deliveryTimeout: int or float 
        
        @raise CommandError: if an error occurs while attempting to send the message
        @raise TimeoutException: if the operation times out
        """
        if self._smsTextMode:
            command = 'AT+CMGS="%s"\r'%destination
            self.write(command, waitForResponse=True, timeout=5, expectedResponseTermSeq='> ')
            command = '%s\n'%message+chr(26)
            result = lineStartingWith('+CMGS:', self.write(command, waitForResponse=True, timeout=20))
        else:
            pdus = encodeSmsSubmitPdu(destination,message, reference=self._smsRef)
            for pdu in pdus:
                self.write('AT+CMGS={0}\r'.format(pdu.tpduLength), timeout=5, expectedResponseTermSeq='> ')
                command = str(pdu)+chr(26)
                result = lineStartingWith('+CMGS:', self.write(command, waitForResponse=True, timeout=20))
        if result == None:
            raise CommandError('Modem did not respond with +CMGS response')
        reference = int(result[7:])
        self._smsRef = reference + 1
        if self._smsRef > 255:
            self._smsRef = 0
        sms = SentSms(destination, message, reference)
        # Add a weak-referenced entry for this SMS (allows us to update the SMS state if a status report is received)
        self.sentSms[reference] = sms
        if waitForDeliveryReport:
            self._smsStatusReportEvent = threading.Event()
            if self._smsStatusReportEvent.wait(deliveryTimeout):
                self._smsStatusReportEvent = None
            else: # Response timed out
                self._smsStatusReportEvent = None
                raise TimeoutException()
        return sms

    def sendUssd(self, ussdString, responseTimeout=15):
        """ Starts a USSD session by dialing the the specified USSD string, or \
        sends the specified string in the existing USSD session (if any)
                
        @param ussdString: The USSD access number to dial
        @param responseTimeout: Maximum time to wait a response, in seconds
        
        @raise TimeoutException: if no response is received in time
        
        @return: The USSD response message/session (as a Ussd object)
        @rtype: gsmmodem.modem.Ussd
        """
        self._ussdSessionEvent = threading.Event()
        try:
            cusdResponse = self.write('AT+CUSD=1,"{0}",15\r'.format(ussdString),waitForResponse=True, timeout=responseTimeout) # Should respond with "OK"
        except Exception:
            self._ussdSessionEvent = None # Cancel the thread sync lock
            raise

        # Some modems issue the +CUSD response before the acknowledgment "OK" - check for that
        if len(cusdResponse) > 1:
            # Look for more than one +CUSD response because of certain modems' strange behaviour
            cusdMatches = allLinesMatchingPattern(self.CUSD_REGEX, cusdResponse)
            if len(cusdMatches) > 0:
                self._ussdSessionEvent = None # Cancel thread sync lock
                return self._parseCusdResponse(cusdMatches)
        # Wait for the +CUSD notification message
        if self._ussdSessionEvent.wait(responseTimeout):
            self._ussdSessionEvent = None
            return self._ussdResponse
        else: # Response timed out
            self._ussdSessionEvent = None            
            raise TimeoutException()
        
    def dial(self, number, timeout=5, callStatusUpdateCallbackFunc=None):
        """ Calls the specified phone number using a voice phone call

        @param number: The phone number to dial
        @param timeout: Maximum time to wait for the call to be established
        @param callStatusUpdateCallbackFunc: Callback function that is executed if the call's status changes due to
               remote events (i.e. when it is answered, the call is ended by the remote party)

        @return: The outgoing call
        @rtype: gsmmodem.modem.Call
        """
        if self._waitForCallInitUpdate:
            # Wait for the "call originated" notification message
            self._dialEvent = threading.Event()
            try:
                self.write('ATD{0};\r'.format(number), timeout=timeout, waitForResponse=self._waitForAtdResponse)
            except Exception:
                self._dialEvent = None # Cancel the thread sync lock
                raise
        else:
            # Don't wait for a call init update - base the call ID on the number of active calls
            self.write('ATD{0};\r'.format(number), timeout=timeout, waitForResponse=self._waitForAtdResponse)
            self.log.debug("Not waiting for outgoing call init update message")
            callId = len(self.activeCalls) + 1
            callType = 0 # Assume voice
            call = Call(self, callId, callType, number, callStatusUpdateCallbackFunc)
            self.activeCalls[callId] = call
            return call

        if self._mustPollCallStatus:
            # Fake a call notification by polling call status until the status indicates that the call is being dialed
            threading.Thread(target=self._pollCallStatus, kwargs={'expectedState': 0, 'timeout': timeout}).start()

        if self._dialEvent.wait(timeout):
            self._dialEvent = None
            callId, callType = self._dialResponse
            call = Call(self, callId, callType, number, callStatusUpdateCallbackFunc)
            self.activeCalls[callId] = call
            return call
        else: # Call establishing timed out
            self._dialEvent = None
            raise TimeoutException()
        
    def _handleModemNotification(self, lines):
        """ Handler for unsolicited notifications from the modem
        
        This method simply spawns a separate thread to handle the actual notification
        (in order to release the read thread so that the handlers are able to write back to the modem, etc)
         
        @param lines The lines that were read
        """
        threading.Thread(target=self.__threadedHandleModemNotification, kwargs={'lines': lines}).start()
    
    def __threadedHandleModemNotification(self, lines):
        """ Implementation of _handleModemNotification() to be run in a separate thread
        
        @param lines The lines that were read
        """
        for line in lines:
            if 'RING' in line:
                # Incoming call (or existing call is ringing)
                self._handleIncomingCall(lines)
                return
            elif line.startswith('+CMTI'):
                # New SMS message indication
                self._handleSmsReceived(line)
                return
            elif line.startswith('+CMT'):
                # New SMS message indication
                self._handleSmsReceived2(lines)
                return
            elif line.startswith('+CUSD'):
                # USSD notification - either a response or a MT-USSD ("push USSD") message
                self._handleUssd(lines)
                return
            elif line.startswith('+CDSI'):
                # SMS status report
                self._handleSmsStatusReport(line)
                return
            else:
                # Check for call status updates            
                for updateRegex, handlerFunc in self._callStatusUpdates:
                    match = updateRegex.match(line)
                    if match:
                        # Handle the update
                        handlerFunc(match)
                        return
        # If this is reached, the notification wasn't handled
        self.log.debug('Unhandled unsolicited modem notification: %s', lines)    
    
    def _handleIncomingCall(self, lines):
        self.log.debug('Handling incoming call')
        ringLine = lines.pop(0)
        if self._extendedIncomingCallIndication:
            try:
                callType = ringLine.split(' ', 1)[1]
            except IndexError:
                # Some external 3G scripts modify incoming call indication settings (issue #18)
                self.log.debug('Extended incoming call indication format changed externally; re-enabling...')
                callType = None
                try:
                    # Re-enable extended format of incoming indication (optional)
                    self.write('AT+CRC=1\r') 
                except CommandError:
                    self.log.warn('Extended incoming call indication format changed externally; unable to re-enable')
                    self._extendedIncomingCallIndication = False
        else:
            callType = None
        if self._callingLineIdentification and len(lines) > 0:
            clipLine = lines.pop(0)
            clipMatch = self.CLIP_REGEX.match(clipLine)
            if clipMatch:
                callerNumber = clipMatch.group(1)
                ton = clipMatch.group(2)
                #TODO: re-add support for this
                callerName = None
                #callerName = clipMatch.group(3)
                #if callerName != None and len(callerName) == 0:
                #    callerName = None
            else:
                callerNumber = ton = callerName = None
        else:
            callerNumber = ton = callerName = None
        
        call = None
        for activeCall in dictValuesIter(self.activeCalls):
            if activeCall.number == callerNumber:
                call = activeCall
                call.ringCount += 1
        if call == None:
            callId = len(self.activeCalls) + 1;
            call = IncomingCall(self, callerNumber, ton, callerName, callId, callType)
            self.activeCalls[callId] = call
        self.incomingCallCallback(call)    
    
    def _handleCallInitiated(self, regexMatch, callId=None, callType=1):
        """ Handler for "outgoing call initiated" event notification line """
        if self._dialEvent:
            if regexMatch:
                groups = regexMatch.groups()
                # Set self._dialReponse to (callId, callType)
                if len(groups) >= 2:
                    self._dialResponse = (int(groups[0]) , int(groups[1]))
                else:
                    self._dialResponse = (int(groups[0]), 1) # assume call type: VOICE
            else:
                self._dialResponse = callId, callType
            self._dialEvent.set()
                
    def _handleCallAnswered(self, regexMatch, callId=None):
        """ Handler for "outgoing call answered" event notification line """
        if regexMatch:
            groups = regexMatch.groups()
            if len(groups) > 1:
                callId = int(groups[0])
                self.activeCalls[callId].answered = True
            else:
                # Call ID not available for this notificition - check for the first outgoing call that has not been answered
                for call in dictValuesIter(self.activeCalls):
                    if call.answered == False and type(call) == Call:
                        call.answered = True
                        return
        else:
            # Use supplied values
            self.activeCalls[callId].answered = True

    def _handleCallEnded(self, regexMatch, callId=None, filterUnanswered=False):
        if regexMatch:
            groups = regexMatch.groups()
            if len(groups) > 0:
                callId = int(groups[0])
            else:
                # Call ID not available for this notification - check for the first outgoing call that is active
                for call in dictValuesIter(self.activeCalls):
                    if type(call) == Call:
                        if not filterUnanswered or (filterUnanswered == True and call.answered == False):
                            callId = call.id
                            break
        if callId and callId in self.activeCalls:
            self.activeCalls[callId].answered = False
            self.activeCalls[callId].active = False
            del self.activeCalls[callId]

    def _handleCallRejected(self, regexMatch, callId=None):
        """ Handler for rejected (unanswered calls being ended)

        Most modems use _handleCallEnded for handling both call rejections and remote hangups.
        This method does the same, but filters for unanswered calls only.
        """
        return self._handleCallEnded(regexMatch, callId, True)

    def _handleSmsReceived(self, notificationLine):
        """ Handler for "new SMS" unsolicited notification line """
        self.log.debug('SMS message received')
        cmtiMatch = self.CMTI_REGEX.match(notificationLine)
        if cmtiMatch:
            msgMemory = cmtiMatch.group(1)
            msgIndex = cmtiMatch.group(2)
            sms = self.readStoredSms(msgIndex, msgMemory)
            self.deleteStoredSms(msgIndex)
            self.smsReceivedCallback(sms)

    def _handleSmsReceived2(self, lines):
        """ Handler for "new SMS" unsolicited notification line """
        self.log.debug('SMS message received2')
        '''cmtMatch = self.CMT_REGEX.match(notificationLine)
        #text = notificationLine[3].strip()
        text = '\n'.join(notificationLine[1:-1])
        print(cmtMatch.groups(),text)'''
        output_lines = []
        n = 0
        # iterate the lines like it's 1984
        # (because we're patching the array,
        # which is hard work for iterators)
        while n < len(lines):

            # not a CMT string? add it back into the
            # output (since we're not interested in it)
            # and move on to the next
            if lines[n][0:5] != "+CMT:":
                output_lines.append(lines[n])
                n += 1
                continue

            # since this line IS a CMT string (an incoming
            # SMS), parse it and store it to deal with later
            m = re.match(r'^\+CMT: "(.+?)",.*?,"(.+?)".*?$', lines[n])
            if m is None:

                # couldn't parse the string, so just move
                # on to the next line. TODO: log this error
                n += 1
                next

            # extract the meta-info from the CMT line,
            # and the message from the FOLLOWING line
            number, timestamp = m.groups()
            text = lines[n+1].strip()
            msgStatus = "REC READ"
            sms=ReceivedSms(self, Sms.TEXT_MODE_STATUS_MAP[msgStatus],number, parseTextModeTimeStr(timestamp),text)
            print(sms)
            self.smsReceivedCallback(sms)
            break
            
    def _handleSmsStatusReport(self, notificationLine):
        """ Handler for SMS status reports """
        self.log.debug('SMS status report received')
        cdsiMatch = self.CDSI_REGEX.match(notificationLine)
        if cdsiMatch:
            msgMemory = cdsiMatch.group(1)
            msgIndex = cdsiMatch.group(2)
            report = self.readStoredSms(msgIndex, msgMemory)
            self.deleteStoredSms(msgIndex)
            # Update sent SMS status if possible            
            if report.reference in self.sentSms:                
                self.sentSms[report.reference].report = report
            if self._smsStatusReportEvent:                
                # A sendSms() call is waiting for this response - notify waiting thread
                self._smsStatusReportEvent.set()
            else:
                # Nothing is waiting for this report directly - use callback
                self.smsStatusReportCallback(report)

    def processStoredSms(self, unreadOnly=False):
        """ Process all SMS messages currently stored on the device/SIM card.
        
        Reads all (or just unread) received SMS messages currently stored on the 
        device/SIM card, initiates "SMS received" events for them, and removes 
        them from the SIM card.
        This is useful if SMS messages were received during a period that
        python-gsmmodem was not running but the modem was powered on.
        
        @param unreadOnly: If True, only process unread SMS messages
        @type unreadOnly: boolean
        """
        states = [Sms.STATUS_ALL]
        if not unreadOnly:
            states.insert(0, Sms.STATUS_RECEIVED_UNREAD)
        for msgStatus in states:
            messages = self.listStoredSms(status=msgStatus, delete=True)
            for sms in messages:
                self.smsReceivedCallback(sms)

    def listStoredSms(self, status=Sms.STATUS_ALL, memory=None, delete=False):
        """ Returns SMS messages currently stored on the device/SIM card.
        
        The messages are read from the memory set by the "memory" parameter.
        
        @param status: Filter messages based on this read status; must be 0-4 (see Sms class)
        @type status: int
        @param memory: The memory type to read from. If None, use the current default SMS read memory
        @type memory: str or None
        @param delete: If True, delete returned messages from the device/SIM card
        @type delete: bool
        
        @return: A list of Sms objects containing the messages read
        @rtype: list
        """
        self._setSmsMemory(readDelete=memory)
        messages = []
        delMessages = set()
        if self._smsTextMode:
            cmglRegex= re.compile(r'^\+CMGL: (\d+),"([^"]+)","([^"]+)",[^,]*,"([^"]+)"$')
            for key, val in dictItemsIter(Sms.TEXT_MODE_STATUS_MAP):
                if status == val:
                    statusStr = key
                    break
            else:
                raise ValueError('Invalid status value: {0}'.format(status))
            result = self.write('AT+CMGL="{0}"\r'.format(statusStr))
            msgLines = []
            msgIndex = msgStatus = number = msgTime = None
            for line in result:
                cmglMatch = cmglRegex.match(line)                
                if cmglMatch:
                    # New message; save old one if applicable
                    if msgIndex != None and len(msgLines) > 0:
                        msgText = '\n'.join(msgLines)
                        msgLines = []
                        print(msgText)
                        messages.append(ReceivedSms(self, Sms.TEXT_MODE_STATUS_MAP[msgStatus], number, parseTextModeTimeStr(msgTime), msgText))
                        delMessages.add(int(msgIndex))
                    msgIndex, msgStatus, number, msgTime = cmglMatch.groups()
                    print("New message:",cmglMatch.groups())
                    msgLines = []
                else:
                    if line != 'OK':
                        msgLines.append(line)
            if msgIndex != None and len(msgLines) > 0:
                msgText = '\n'.join(msgLines)
                msgLines = []
                messages.append(ReceivedSms(self, Sms.TEXT_MODE_STATUS_MAP[msgStatus], number, parseTextModeTimeStr(msgTime), msgText))
                delMessages.add(int(msgIndex))
        else:
            cmglRegex = re.compile(r'^\+CMGL:\s*(\d+),(\d+),.*$')
            readPdu = False
            result = self.write('AT+CMGL={0}\r'.format(status))
            for line in result:
                if not readPdu:
                    cmglMatch = cmglRegex.match(line)
                    if cmglMatch:
                        msgIndex = int(cmglMatch.group(1))
                        msgStat = int(cmglMatch.group(2))
                        readPdu = True
                else:
                    try:
                        smsDict = decodeSmsPdu(line)
                    except EncodingError:
                        self.log.debug('Discarding line from +CMGL response: %s', line)
                    else:
                        if smsDict['type'] == 'SMS-DELIVER':
                            sms = ReceivedSms(self, int(msgStat), smsDict['number'], smsDict['time'], smsDict['text'], smsDict['smsc'])
                        elif smsDict['type'] == 'SMS-STATUS-REPORT':
                            sms = StatusReport(self, int(msgStat), smsDict['reference'], smsDict['number'], smsDict['time'], smsDict['discharge'], smsDict['status'])
                        else:
                            raise CommandError('Invalid PDU type for readStoredSms(): {0}'.format(smsDict['type']))
                        messages.append(sms)
                        delMessages.add(msgIndex)
                        readPdu = False
        if delete:
            if status == Sms.STATUS_ALL:
                # Delete all messages
                self.deleteMultipleStoredSms()
            else:
                for msgIndex in delMessages:
                    self.deleteStoredSms(msgIndex)
        return messages
                
    @property
    def smsTextMode(self):
        """ @return: True if the modem is set to use text mode for SMS, False if it is set to use PDU mode """
        return self._smsTextMode
    @smsTextMode.setter
    def smsTextMode(self, textMode):
        """ Set to True for the modem to use text mode for SMS, or False for it to use PDU mode """
        if textMode != self._smsTextMode:
            if self.alive:
                self.write('AT+CMGF={0}\r'.format(1 if textMode else 0))
            self._smsTextMode = textMode
            self._compileSmsRegexes()

    def _compileSmsRegexes(self):
        """ Compiles regular expression used for parsing SMS messages based on current mode """
        if self._smsTextMode:
            if self.CMGR_SM_DELIVER_REGEX_TEXT == None:
                self.CMGR_SM_DELIVER_REGEX_TEXT = re.compile(r'^\+CMGR: "([^"]+)","([^"]+)",[^,]*,"([^"]+)"$')
                self.CMGR_SM_REPORT_REGEXT_TEXT = re.compile(r'^\+CMGR: ([^,]*),\d+,(\d+),"{0,1}([^"]*)"{0,1},\d*,"([^"]+)","([^"]+)",(\d+)$')
        elif self.CMGR_REGEX_PDU == None:
            self.CMGR_REGEX_PDU = re.compile(r'^\+CMGR: (\d+),(\d*),(\d+)$')

    @property    
    def smsc(self):
        """ @return: The default SMSC number stored on the SIM card """
        if self._smscNumber == None:
            try:
                readSmsc = self.write('AT+CSCA?\r')
            except SmscNumberUnknownError:
                pass # Some modems return a CMS 330 error if the value isn't set
            else:
                cscaMatch = lineMatching(r'\+CSCA:\s*"([^,]+)",(\d+)$', readSmsc)
                if cscaMatch:
                    self._smscNumber = cscaMatch.group(1)
        return self._smscNumber
    
    @smsc.setter
    def smsc(self, smscNumber):
        """ Set the default SMSC number to use when sending SMS messages """
        if smscNumber != self._smscNumber:
            if self.alive:
                self.write('AT+CSCA="{0}"\r'.format(smscNumber))
            self._smscNumber = smscNumber
            
    def _setSmsMemory(self, readDelete=None, write=None):
        """ Set the current SMS memory to use for read/delete/write operations """
        # Switch to the correct memory type if required
        if write != None and write != self._smsMemWrite:
            self.write()
            readDel = readDelete or self._smsMemReadDelete
            self.write('AT+CPMS="{0}","{1}"\r'.format(readDel, write))
            self._smsMemReadDelete = readDel
            self._smsMemWrite = write
        elif readDelete != None and readDelete != self._smsMemReadDelete:
            self.write('AT+CPMS="{0}"\r'.format(readDelete))
            self._smsMemReadDelete = readDelete
            
    def readStoredSms(self, index, memory=None):
        """ Reads and returns the SMS message at the specified index
        
        @param index: The index of the SMS message in the specified memory
        @type index: int
        @param memory: The memory type to read from. If None, use the current default SMS read memory
        @type memory: str or None
        
        @raise CommandError: if unable to read the stored message
        
        @return: The SMS message
        @rtype: subclass of gsmmodem.modem.Sms (either ReceivedSms or StatusReport)
        """
        # Switch to the correct memory type if required
        self._setSmsMemory(readDelete=memory)
        msgData = self.write('AT+CMGR={0}\r'.format(index),waitForResponse=True,timeout=5)
        # Parse meta information
        if self._smsTextMode:
            cmgrMatch = self.CMGR_SM_DELIVER_REGEX_TEXT.match(msgData[0])
            if cmgrMatch:
                msgStatus, number, msgTime = cmgrMatch.groups()
                msgText = '\n'.join(msgData[1:-1])
                return ReceivedSms(self, Sms.TEXT_MODE_STATUS_MAP[msgStatus], number, parseTextModeTimeStr(msgTime), msgText)
            else:
                # Try parsing status report
                cmgrMatch = self.CMGR_SM_REPORT_REGEXT_TEXT.match(msgData[0])
                if cmgrMatch:
                    msgStatus, reference, number, sentTime, deliverTime, deliverStatus = cmgrMatch.groups()
                    if msgStatus.startswith('"'):
                        msgStatus = msgStatus[1:-1]                    
                    if len(msgStatus) == 0:
                        msgStatus = "REC UNREAD"
                    return StatusReport(self, Sms.TEXT_MODE_STATUS_MAP[msgStatus], int(reference), number, parseTextModeTimeStr(sentTime), parseTextModeTimeStr(deliverTime), int(deliverStatus))
                else:
                    raise CommandError('Failed to parse text-mode SMS message +CMGR response: {0}'.format(msgData))
        else:
            cmgrMatch = self.CMGR_REGEX_PDU.match(msgData[0])
            if not cmgrMatch:
                raise CommandError('Failed to parse PDU-mode SMS message +CMGR response: {0}'.format(msgData))
            stat, alpha, length = cmgrMatch.groups()
            pdu = msgData[1]
            smsDict = decodeSmsPdu(pdu)
            if smsDict['type'] == 'SMS-DELIVER':
                return ReceivedSms(self, int(stat), smsDict['number'], smsDict['time'], smsDict['text'], smsDict['smsc'])
            elif smsDict['type'] == 'SMS-STATUS-REPORT':
                return StatusReport(self, int(stat), smsDict['reference'], smsDict['number'], smsDict['time'], smsDict['discharge'], smsDict['status'])
            else:
                raise CommandError('Invalid PDU type for readStoredSms(): {0}'.format(smsDict['type']))
    
    def deleteStoredSms(self, index, memory=None):
        """ Deletes the SMS message stored at the specified index in modem/SIM card memory
        
        @param index: The index of the SMS message in the specified memory
        @type index: int
        @param memory: The memory type to delete from. If None, use the current default SMS read/delete memory
        @type memory: str or None
        
        @raise CommandError: if unable to delete the stored message
        """
        self._setSmsMemory(readDelete=memory)
        self.write('AT+CMGD={0},0\r'.format(index))
    
    def deleteMultipleStoredSms(self, delFlag=4, memory=None):
        """ Deletes all SMS messages that have the specified read status.
        
        The messages are read from the memory set by the "memory" parameter.
        The value of the "delFlag" paramater is the same as the "DelFlag" parameter of the +CMGD command:
        1: Delete All READ messages
        2: Delete All READ and SENT messages
        3: Delete All READ, SENT and UNSENT messages
        4: Delete All messages (this is the default)
 
        @param delFlag: Controls what type of messages to delete; see description above.
        @type delFlag: int
        @param memory: The memory type to delete from. If None, use the current default SMS read/delete memory
        @type memory: str or None
        @param delete: If True, delete returned messages from the device/SIM card
        @type delete: bool
        
        @raise ValueErrror: if "delFlag" is not in range [1,4]
        @raise CommandError: if unable to delete the stored messages
        """
        if 0 < delFlag <= 4:
            self._setSmsMemory(readDelete=memory)
            self.write('AT+CMGD=1,{0}\r'.format(delFlag))
        else:
            raise ValueError('"delFlag" must be in range [1,4]')
    
    def _handleUssd(self, lines):
        """ Handler for USSD event notification line(s) """
        if self._ussdSessionEvent:
            # A sendUssd() call is waiting for this response - parse it
            cusdMatches = allLinesMatchingPattern(self.CUSD_REGEX, lines)
            if len(cusdMatches) > 0:
                self._ussdResponse = self._parseCusdResponse(cusdMatches)
            # Notify waiting thread
            self._ussdSessionEvent.set()
    
    def _parseCusdResponse(self, cusdMatches):
        """ Parses one or more +CUSD notification lines (for USSD)
        @return: USSD response object
        @rtype: gsmmodem.modem.Ussd
        """
        message = None
        sessionActive = True
        if len(cusdMatches) > 1:
            self.log.debug('Multiple +CUSD responses received; filtering...')
            # Some modems issue a non-standard "extra" +CUSD notification for releasing the session
            for cusdMatch in cusdMatches:
                if cusdMatch.group(1) == '2':
                    # Set the session to inactive, but ignore the message
                    self.log.debug('Ignoring "session release" message: %s', cusdMatch.group(2))
                    sessionActive = False
                else:
                    # Not a "session release" message
                    message = cusdMatch.group(2)
                    if sessionActive and cusdMatch.group(1) != '1':
                        sessionActive = False
        else:
            sessionActive = cusdMatches[0].group(1) == '1'
            message = cusdMatches[0].group(2)
        return Ussd(self, sessionActive, message)

    def _placeHolderCallback(self, *args):
        """ Does nothing """
        self.log.debug('called with args: {0}'.format(args))
    
    def _pollCallStatus(self, expectedState, callId=None, timeout=None):
        """ Poll the status of outgoing calls.    
        This is used for modems that do not have a known set of call status update notifications.
        
        @param expectedState: The internal state we are waiting for. 0 == initiated, 1 == answered, 2 = hangup
        @type expectedState: int
        
        @raise TimeoutException: If a timeout was specified, and has occurred
        """
        callDone = False
        timeLeft = timeout or 999999
        while self.alive and not callDone and timeLeft > 0:
            time.sleep(0.5)
            if expectedState == 0: # Only call initializing can timeout
                timeLeft -= 0.5
            try:
                clcc = self._pollCallStatusRegex.match(self.write('AT+CLCC\r')[0])
            except TimeoutException as timeout:
                # Can happend if the call was ended during our time.sleep() call
                clcc = None
            if clcc:
                direction = int(clcc.group(2))
                if direction == 0: # Outgoing call
                    # Determine call state
                    stat = int(clcc.group(3))
                    if expectedState == 0: # waiting for call initiated
                        if stat == 2 or stat == 3: # Dialing or ringing ("alerting")                            
                            callId = int(clcc.group(1))
                            callType = int(clcc.group(4))
                            self._handleCallInitiated(None, callId, callType) # if self_dialEvent is None, this does nothing
                            expectedState = 1 # Now wait for call answer
                    elif expectedState == 1: # waiting for call to be answered
                        if stat == 0: # Call active
                            callId = int(clcc.group(1))
                            self._handleCallAnswered(None, callId)
                            expectedState = 2 # Now wait for call hangup                            
            elif expectedState == 2 : # waiting for remote hangup
                # Since there was no +CLCC response, the call is no longer active
                callDone = True
                self._handleCallEnded(None, callId=callId)
            elif expectedState == 1: # waiting for call to be answered
                # Call was rejected
                callDone = True
                self._handleCallRejected(None, callId=callId)
        if timeLeft <= 0:
            raise TimeoutException()


        
class Call(object):
    """ A voice call """
    
    DTMF_COMMAND_BASE = '+VTS='
    dtmfSupport = False # Indicates whether or not DTMF tones can be sent in calls
    
    def __init__(self, gsmModem, callId, callType, number, callStatusUpdateCallbackFunc=None):
        """
        @param gsmModem: GsmModem instance that created this object
        @param number: The number that is being called        
        """
        self._gsmModem = weakref.proxy(gsmModem)
        self._callStatusUpdateCallbackFunc = callStatusUpdateCallbackFunc
        # Unique ID of this call
        self.id = callId
        # Call type (VOICE == 0, etc)
        self.type = callType        
        # The remote number of this call (destination or origin)
        self.number = number                
        # Flag indicating whether the call has been answered or not (backing field for "answered" property)
        self._answered = False
        # Flag indicating whether or not the call is active
        # (meaning it may be ringing or answered, but not ended because of a hangup event)
        self.active = True

    @property
    def answered(self):
        return self._answered
    @answered.setter
    def answered(self, answered):
        self._answered = answered
        if self._callStatusUpdateCallbackFunc:
            self._callStatusUpdateCallbackFunc(self)
    
    def sendDtmfTone(self, tones):
        """ Send one or more DTMF tones to the remote party (only allowed for an answered call) 
        
        Note: this is highly device-dependent, and might not work
        
        @param digits: A str containining one or more DTMF tones to play, e.g. "3" or "*123#"

        @raise CommandError: if the command failed/is not supported        
        @raise InvalidStateException: if the call has not been answered, or is ended while the command is still executing
        """        
        if self.answered:
            dtmfCommandBase = self.DTMF_COMMAND_BASE.format(cid=self.id)
            toneLen = len(tones)
            if len(tones) > 1:
                cmd = ('AT{0}{1};{0}' + ';{0}'.join(tones[1:])).format(dtmfCommandBase, tones[0])                
            else:
                cmd = 'AT{0}{1}'.format(dtmfCommandBase, tones)
            try:
                self._gsmModem.write(cmd, timeout=(5 + toneLen))
            except CmeError as e:
                if e.code == 30:
                    # No network service - can happen if call is ended during DTMF transmission (but also if DTMF is sent immediately after call is answered)
                    raise InterruptedException('No network service', e)
                elif e.code == 3:
                    # Operation not allowed - can happen if call is ended during DTMF transmission
                    raise InterruptedException('Operation not allowed', e)
                else:
                    raise e
        else:
            raise InvalidStateException('Call is not active (it has not yet been answered, or it has ended).')
    
    def hangup(self):
        """ End the phone call.
        
        Does nothing if the call is already inactive.
        """
        if self.active:
            self._gsmModem.write('ATH')
            self.answered = False
            self.active = False
        if self.id in self._gsmModem.activeCalls:
            del self._gsmModem.activeCalls[self.id]


class IncomingCall(Call):
    
    CALL_TYPE_MAP = {'VOICE': 0}
    
    """ Represents an incoming call, conveniently allowing access to call meta information and -control """     
    def __init__(self, gsmModem, number, ton, callerName, callId, callType):
        """
        @param gsmModem: GsmModem instance that created this object
        @param number: Caller number
        @param ton: TON (type of number/address) in integer format
        @param callType: Type of the incoming call (VOICE, FAX, DATA, etc)
        """
        if type(callType) == str:
            callType = self.CALL_TYPE_MAP[callType] 
        super(IncomingCall, self).__init__(gsmModem, callId, callType, number)        
        # Type attribute of the incoming call
        self.ton = ton
        self.callerName = callerName        
        # Flag indicating whether the call is ringing or not
        self.ringing = True        
        # Amount of times this call has rung (before answer/hangup)
        self.ringCount = 1
    
    def answer(self):
        """ Answer the phone call.        
        @return: self (for chaining method calls)
        """
        if self.ringing:
            self._gsmModem.write('ATA')
            self.ringing = False
            self.answered = True
        return self    

    def hangup(self):
        """ End the phone call. """
        self.ringing = False
        super(IncomingCall, self).hangup()
#-----------------------------------------------                
