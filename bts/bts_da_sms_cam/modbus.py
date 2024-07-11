#!/usr/bin/env python
import minimalmodbus
import time

#minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = True

instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1) # port name, slave address (in decimal)
instrument.debug = True
instrument.serial.port          # this is the serial port name
instrument.serial.baudrate = 9600   # Baud
instrument.serial.bytesize = 8
#instrument.serial.parity   = serial.PARITY_NONE
instrument.serial.stopbits = 1
instrument.serial.timeout  = 0.05   # seconds
instrument.address=1     # this is the slave address number
instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode
count=10
while count:
    ## Read temperature (PV = ProcessValue) ##
    try:
        temperature = instrument.read_register(0, 1) # Registernumber, number of decimals
        print temperature
    except Exception, e:
        #instrument.serial.close()
        print(e.args, e.message)

    time.sleep(2)
    ## Read temperature (PV = ProcessValue) ##
    try:
        temperature = instrument.read_register(1, 1) # Registernumber, number of decimals
        print temperature
    except Exception, e:
        #instrument.serial.close()
        print(e.args, e.message)
        
    time.sleep(2)
    count=count-1
    
instrument.serial.close()
