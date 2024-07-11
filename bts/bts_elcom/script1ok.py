# Imports
# Import smtplib to provide email functions
import smtplib
# Import the email modules
from email.mime.text import MIMEText
import math
import webiopi
from webiopi.devices.serial import Serial
import os
import socket
import codecs
import re
from subprocess import call
from subprocess import *
import time
from time import localtime, strftime
import socket
import datetime
import threading
import queue
import sys
import unicodedata
import sqlite3
import RPi.GPIO as GPIO
import minimalmodbus
import urllib.parse
import urllib.request
import netifaces as ni
sys.path.append('/home/pi/bts')
import gsmsms as gsm
# heardware define
GPIO.setmode(GPIO.BCM)
OUTBEEP = 13
LEDRUN  = 11
LEDERROR= 12
LEDALARM= 22
LEDCONNECT= 23
OUT1=       16
OUT2=       17
OUT3=       18
OUT4=       19
OUT5=       20
OUT6=       21
#OUT7=       22
#OUT8=       23
INP1=       5
INP2=       6
INP3=       7
INP4=       8
INP5=       9
INP6=       10
#INP7=       11
#INP8=       12
# Bien dieu khien may phat:
# OUTGENERATOR=1 khoi dong may phat tu dong
# OUTGENERATOR=0 dung may phat tu dong
# OUTGENERATOR=3 khoi dong may phat bang tay
# OUTGENERATOR=2 dung may phat bang tay
OUTGENERATOR=0
CHANGEOUTGENERATOR=0
#Co 18 kenh du lieu
# Kenh 18 cai dat du lieu toi may phat
# Kenh 19 dieu khien dieu hoa 1
# Kenh 20 dieu khien dieu hoa 2
MAXCHANNEL=18
MAXADDRESS=15
MAXINPUT=6
# Variable global
global inputstatus,outputstatus,modeoutputstatus,Alarmspk,countmin,Beep,lastminute,lasthour,datetimealarms,addslave,addslavesms,looprunning
inputstatus=0
outputstatus=0
modeoutputstatus=0
Alarmspk=0
countmin=0
lastminute=0
lasthour=0
Beep=0
datetimealarms=""
addslave=0
addslavesms=0
looprunning=1
#-----
GPIO.setwarnings(False) 
GPIO.setup(LEDRUN, GPIO.OUT) # sets i to output and 0V, off
GPIO.setup(LEDERROR, GPIO.OUT) # sets i to output and 0V, off
GPIO.setup(OUTBEEP, GPIO.OUT) # sets i to output and 0V, off
#---------------------------------------------------------------------------
#BEGIN;
#CREATE TABLE alarmdisplay (ID INTEGER PRIMARY KEY AUTOINCREMENT,tdate DATE, ttime TIME, event TEXT);
#COMMIT;
    
dbname='/home/pi/bts/database.db'
sys.path.append("/home/pi/webiopi/htdocss")  #<--- or whatever your path is !

# Enable debug output
webiopi.setDebug()
# Tao bang ghi du lieu canh bao
def creat_alarm_tablet():
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    print ("Opened database successfully")
    conn.execute('''CREATE TABLE if not exists alarmdisplay
    (ID INTEGER PRIMARY KEY AUTOINCREMENT,
    tdate DATE,
    ttime TIME,
    event TEXT);''')
    print ("Table alarm created successfully")
    conn.close()
    
# store the event in the database
def insert_alarm_tablet(alarms):
    global Beep
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # I used triple quotes so that I could break this string into
    curs.execute("INSERT INTO alarmdisplay values(null,date('now','localtime'),time('now','localtime'),(?))", (alarms,))
    # commit the changes
    conn.commit()
    conn.close()
    Beep=5
    # Gui du lieu toi server khi co canh bao
    q.put(alarms)
    #messagetoserver("alarm",alarms)
# Doc du lieu canh bao, khong qua 100 su kien
@webiopi.macro
def load_alarm_tablet():
    i=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # ID |date | time | ten su kien canh bao | 
    curs.execute("SELECT * FROM alarmdisplay ORDER BY tdate DESC, ttime DESC" )
    for row in curs.fetchall():
        data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
        i=i+1
        if(i>100):
            break
    #print (data)
    conn.close()
    return (data)

# Doc du lieu canh bao, khong qua 6 su kien index.htm
@webiopi.macro
def load_alarm_tablet_index():
    i=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # ID |date | time | ten su kien canh bao | 
    curs.execute("SELECT * FROM alarmdisplay ORDER BY tdate DESC, ttime DESC" )
    for row in curs.fetchall():
        data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +","+"\r\n"
        i=i+1
        if(i>4):
            break
    #print (data)
    conn.close()
    return (data)

# Doc du lieu canh bao theo ngay thang: alarmdata.htm
@webiopi.macro
def load_alarm_tablet_date(startdate,enddate):
    i=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(startdate)>0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (startdate,enddate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)==0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM alarmdisplay  WHERE tdate=='%s'  ORDER BY ID DESC" % (enddate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)>0 and len(enddate)==0):
        for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate=='%s'  ORDER BY ID DESC" % (startdate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
            i=i+1
            if(i>1000):
                break
                
    #print (data)
    conn.close()
    return (data)
#-------------------------------
# Tao bang ghi du lieu history
# status=0 not connnect
# status=1 ok
# status=2 low
# status=3 high
# Them dia chi Mosbus
def creat_history_data():
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    print ("Opened database successfully")
    conn.execute('''CREATE TABLE if not exists historydata
    (ID INTEGER PRIMARY KEY AUTOINCREMENT,
    tdate DATE,
    ttime TIME,
    address NUMERIC,
    channel NUMERIC,
    value   NUMERIC,
    status  NUMERIC
    );''')
    print ("Table history created successfully")
    conn.close()
    
# store data in the database ok, number
def insert_history_data(indexadd,channel,value,status):
    address=int(indexadd)
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    curs.execute("INSERT INTO historydata values(null,date('now','localtime'),time('now','localtime'),(?),(?),(?),(?))",\
                 (address,channel,value,status))
    # commit the changes
    conn.commit()
    conn.close()


# display the contents of the database channel
@webiopi.macro
def load_history_data_date(indexadd,startdate,enddate):
    i=0
    data=""
    address=int(indexadd)
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(startdate)>0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE address=='%s' AND tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (address,startdate,enddate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ Set.namechannel[address][row[4]] + "," + str(row[5])+","+Set.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)==0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata  WHERE address=='%s' AND tdate=='%s'  ORDER BY ID DESC" % (address,enddate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ Set.namechannel[address][row[4]] + "," + str(row[5])+","+Set.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)>0 and len(enddate)==0):
        for row in curs.execute("SELECT * FROM historydata WHERE address=='%s' AND tdate=='%s'  ORDER BY ID DESC" % (address,startdate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ Set.namechannel[address][row[4]] + "," + str(row[5])+","+Set.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    #print (data)
    conn.close()
    return (data)
# display the contents of the database channel
@webiopi.macro
def load_history_data_day(indexadd,days):
    i=0
    data=""
    address=int(indexadd)
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(days)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE address=='%s' AND tdate>date('now','localtime','-%s day')  ORDER BY ID DESC" % (address,days)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ Set.namechannel[address][row[4]] + "," + str(row[5])+","+Set.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    #print (data)
    conn.close()
    return (data)

# display the contents for trend
# Time | Value
@webiopi.macro
def load_history_days_channel(indexadd,channel,days):
    i=0
    j=0
    data=""
    address=int(indexadd)
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(days)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE address=='%s' AND channel='%s' AND tdate>date('now','localtime','-%s day')  ORDER BY tdate DESC, ttime DESC" % (address,channel,days)):
            j=j+1
            if(j>100):
                j=0
                data=data+str(row[1])+","+ str(row[5])+"\r\n"
            else:
                data=data+str(row[2])+","+ str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    #print (data)
    conn.close()
    return (data)
# display the contents for trend
# Time | Value
@webiopi.macro
def load_history_date_channel(indexadd,channel,startdate,enddate):
    i=0
    data=""
    address=int(indexadd)
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(startdate)>0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE address=='%s' AND channel='%s' AND tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (address,channel,startdate,enddate)):
            data=data+str(row[2])+","+ str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)==0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata  WHERE address=='%s' AND channel='%s' AND tdate=='%s'  ORDER BY ttime DESC" % (address,channel,enddate)):
            data=data+str(row[2])+","+ str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)>0 and len(enddate)==0):
        for row in curs.execute("SELECT * FROM historydata WHERE address=='%s' AND channel='%s' AND tdate=='%s'  ORDER BY ttime DESC" % (address,channel,startdate)):
            data=data+str(row[2])+","+ str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    #print (data)
    conn.close()
    return (data)
# Dieu khien loi ra
@webiopi.macro
def Output(index):
    global Beep,OUTGENERATOR,CHANGEOUTGENERATOR
    if(index=='1'):
        if (GPIO.input(OUT1) == GPIO.LOW):
            GPIO.output(OUT1,1)
            #air.CHANGEOUT1=1
        else:
            GPIO.output(OUT1,0)
            #air.CHANGEOUT1=1

    if(index=='2'):
        if (GPIO.input(OUT2) == GPIO.LOW):
            GPIO.output(OUT2,1)
            #air.CHANGEOUT2=1
        else:
            GPIO.output(OUT2,0)
            #air.CHANGEOUT2=1
    if(index=='3'):
        if (GPIO.input(OUT3) == GPIO.LOW):
            GPIO.output(OUT3,1) 
        else:
            GPIO.output(OUT3,0)
            IOsetting.tsiren3buff=0     #tat chuong bao dong
    if(index=='4'):
        if (GPIO.input(OUT4) == GPIO.LOW):
            GPIO.output(OUT4,1) 
        else:
            GPIO.output(OUT4,0) 
    if(index=='5'):
        if (GPIO.input(OUT5) == GPIO.LOW):
            GPIO.output(OUT5,1) 
        else:
            GPIO.output(OUT5,0) 
    if(index=='6'):
        if (GPIO.input(OUT6) == GPIO.LOW):
            GPIO.output(OUT6,1) 
        else:
            GPIO.output(OUT6,0)
    '''if(index=='7'):
        if (GPIO.input(OUT7) == GPIO.LOW):
            GPIO.output(OUT7,1) 
        else:
            GPIO.output(OUT7,0)
    if(index=='8'):
        if (GPIO.input(OUT8) == GPIO.LOW):
            GPIO.output(OUT8,1) 
        else:
            GPIO.output(OUT8,0)
    # Che do tu dong
    if(index=='9'):
        IOsetting.modeoutgen=0  #che do tu dong
        #OUTGENERATOR=0  
        #CHANGEOUTGENERATOR=1
    # Che do bang tay
    if(index=='10'):
        IOsetting.modeoutgen=1  #che do bang tay
        OUTGENERATOR=3  #khoi dong may phat bang tay
        CHANGEOUTGENERATOR=1
    if(index=='11'):
        IOsetting.modeoutgen=1  #che do bang tay
        OUTGENERATOR=2  #dung may phat bang tay
        CHANGEOUTGENERATOR=1
        '''
    Beep=1
    data=""
    for i in range(MAXINPUT):
        data=data+str(GPIO.input(INP1+i))+","+ str(GPIO.input(OUT1+i))+","+str(IOsetting.modeoutput[i])+"\r\n"
    return(data)
#-----------------------------
# Liet ke ten cac kenh du lieu
@webiopi.macro
def Listnamechannel(indexadd):
    data=""
    address=int(indexadd)
    for i in range(Set.maxchannel[address]):
        data=data+Set.namechannel[address][i]+"\n"
    return(data)

#-----------------------------        
# Hien thi trang thai dieu khien may phat
# usbrtu.readdata[17] là 1 byte có 8 bit voi 4 bit dau la input và 4 bit sau la output
@webiopi.macro
def UpdateGenerator():
    data=""
    data=str(IOsetting.modeoutgen) +","+str(OUTGENERATOR) +","+ str(usbrtu.readdata[17])+"\r\n"
    return(data)
#-----------------------------        
# Hien thi du lieu tren Graph Scada
@webiopi.macro
def UpdatePower():
    # namechannel | value | unit | status | lowset | high
    data=""
    for address in range(MAXADDRESS):
        for i in range(Set.indexweb,Set.indexweb+3):
            data=data+ Set.namechannel[address][i] +","+str(usbrtu.readdata[address][i])+","+Set.unitreg[address][i] +","
            data=data+ str(usbrtu.status[address][i])+","+str(Set.lowset[address][i]) +","+ str(Set.highset[address][i])+"\r\n"
        
    return(data)
@webiopi.macro
def Modedisplay(control):
    if(control=='1' and Set.indexweb<MAXCHANNEL-3):
        Set.indexweb=Set.indexweb+3
    elif (control=='2' and Set.indexweb>=3):
        Set.indexweb=Set.indexweb-3
    return(Set.indexweb) 
#-----------------------------        
# Hien thi du lieu tren Index
@webiopi.macro
def UpdateMonitor(indexadd):
    # Time | channel | namechannel | value | unit | status | Input | 
    data=""
    address=int(indexadd)
    for i in range(Set.maxchannel[address]):
        data=data+strftime("%H:%M:%S",localtime())+","+str(i+1)+"," + Set.namechannel[address][i] +","
        data=data+str(usbrtu.readdata[address][i])+","
        data=data+Set.unitreg[address][i] +","+ str(usbrtu.status[address][i])+","+str(inputstatus)+","+str(outputstatus)+"\r\n"
        
    return(data)
#---       
# Hien thi tren Index
@webiopi.macro
def UpdateNameInput():
    data=""
    for i in range(MAXINPUT):
        data=data+str(IOsetting.lowinput[i])+","+str(IOsetting.highinput[i])+"\r\n"
    return(data)
#---       
# Hien thi tren Index
@webiopi.macro
def UpdateStatusInOut():
    data=""
    for i in range(MAXINPUT):
        data=data+str(GPIO.input(INP1+i))+","+ str(GPIO.input(OUT1+i))+","+str(IOsetting.modeoutput[i])+"\r\n"
    return(data)
#---       
# Hien thi tren Index cac ket noi modbus
@webiopi.macro
def UpdateStatusModbus():
    data=""
    for i in range(MAXADDRESS):
        data=data+str(Set.nameslave[i])+","+str(Set.connect[i])+","+str(Set.maxchannel[i])+"\r\n"
    return(data)
#-----Hien thi tren index voi cac trang thai-----
@webiopi.macro
def UpdateStatus():
    data=""
    data="ID: "+ Netsetting.id + "/ " + str(Netsetting.hostname) +","
    if(IOsetting.alarm):
        data=data+'ARMING,'
    else:
        data=data+'DISARM,'
    if(len(Gsm.reportsms)>0):
        data=data+str(Gsm.reportsms)+". Network:"+str(Gsm.network)+"; CSQ:"+str(Gsm.csq)+","
    else:
        data=data+"Network:"+str(Gsm.network)+"; CSQ:"+str(Gsm.csq)+","
    #data=data+Netsetting.reportserver+". "+ usbrtu.reportmodbus+","+IOsetting.reporthmi+"\r\n"
    data=data+IOsetting.reporthmi+". "+ usbrtu.reportmodbus+"\r\n"
    return(data)
#-----Hien thi tren index cac lenh cusd-----
@webiopi.macro
def SendCusd(data):
    sms.dial(data+"#")
    print(sms._ussdResponse)
    return (sms._ussdResponse)
#---------Net setting----------------------
class netsetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/Netsetting.txt"
        open(self.file, "r+")
        self.sizedatatoserver=0
        self.reportserver=""
        self.id=""
        self.mac=""
        self.hostname="ECA-GPIs6.6CE"
        self.dhcp=1
        self.ip="192.168.1.211"
        self.gateway="192.168.1.1"
        self.mask="255.255.255.0"
        self.ipserver="192.168.1.210"
        self.portserver="9999"
        self.tel=["0915086942","0","0","0","0"]
        self.username=""
        self.newpass=""
        self.conpass=""
        self.mailserver="ecapro.com.vn"
        self.mailport="25"
        self.mailfrom="info@ecapro.com.vn"
        self.mailpass="ecaprovn"
        self.mailto="trainer.ecapro@gmail.com"
    def Load_setting(self):
        f = open(self.file, "r")
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        print("Network Setting:",setting)
        if(len(setting)>=21):
            self.mac=setting[0]
            self.hostname=setting[1]
            self.dhcp=int(setting[2])
            self.ip=setting[3]
            self.gateway=setting[4]
            self.mask=setting[5]
            #self.getiface()
            self.ipserver=setting[6]
            self.portserver=setting[7]
            self.tel[0]=setting[8]
            self.tel[1]=setting[9]
            self.tel[2]=setting[10]
            self.tel[3]=setting[11]
            self.tel[4]=setting[12]
            self.username=setting[13]
            self.newpass=setting[14]
            self.conpass=setting[15]
            self.mailserver=setting[16]
            self.mailport=setting[17]
            self.mailfrom=setting[18]
            self.mailpass=setting[19]
            self.mailto=setting[20]
            print("Read Net Setting ok")
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            for i in range(len(self.tel)):   
                data=data+str(self.tel[i])+"\n"
            #data=data+str(self.username)+"\n"+str(self.newpass)+"\n"+str(self.conpass)+"\n"\
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto)+"\n"
        else:
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            for i in range(len(self.tel)):   
                data=data+str(self.tel[i])+"\n"
            #data=data+str(self.username)+"\n"+str(self.newpass)+"\n"+str(self.conpass)+"\n"\
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto)+"\n"
            self.Save_setting(data)
            print("Default Net Setting ok")
        return (data)

    def Save_setting(self,data):
        f = open(self.file, "w")
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        print (setting)
        if(len(setting)>=21):
            self.mac=setting[0]
            self.hostname=setting[1]
            self.dhcp=int(setting[2])
            self.ip=setting[3]
            self.gateway=setting[4]
            self.mask=setting[5]
            self.smtpserver=setting[6]
            self.port=int(setting[7])
            self.tel[0]=setting[8]
            self.tel[1]=setting[9]
            self.tel[2]=setting[10]
            self.tel[3]=setting[11]
            self.tel[4]=setting[12]
            self.username=setting[13]
            self.newpass=setting[14]
            self.conpass=setting[15]
            self.mailserver=setting[16]
            self.mailport=setting[17]
            self.mailfrom=setting[18]
            self.mailpass=setting[19]
            self.mailto=setting[20]
            if(len(self.username)>0 and len(self.newpass)>0 and len(self.conpass)>0):
                if(self.save_pass()==False):
                    return
            self.setiface()
            print("Saved Net Setting")
            # shutdown our Raspberry Pi
            os.system("sudo reboot")
            
    def save_pass(self):
        file = "/etc/webiopi/passwd"
        fp = open(file, "w")
        if (self.newpass!= self.conpass):
            print("Passwords don't match !")
            return False
        else:
            from webiopi.utils.crypto import encryptCredentials
            auth = encryptCredentials(self.username, self.newpass)
            print("\nHash: %s" % auth)
            if file:
                fp.write(auth)
                fp.close()
                print("Saved to %s" % file)
                return True
            
    def getiface(self):
        '''ni.ifaddresses('eth0')
        {17: [{'broadcast': 'ff:ff:ff:ff:ff:ff', 'addr': '00:02:55:7b:b2:f6'}],
        2: [{'broadcast': '24.19.161.7', 'netmask': '255.255.255.248', 'addr': '24.19.161.6'}],
        10: [{'netmask': 'ffff:ffff:ffff:ffff::', 'addr': 'fe80::202:55ff:fe7b:b2f6%eth0'}]}'''
        print(ni.ifaddresses('eth0'))
        self.ip=ni.ifaddresses('eth0')[2][0]['addr']
        self.netmask=ni.ifaddresses('eth0')[2][0]['netmask']
        #{'default': {2: ('192.168.1.1', 'eth0')}, 2: [('192.168.1.1', 'eth0', True)]}
        self.gateway=ni.gateways()[2][0][0]
        self.mac=ni.ifaddresses('eth0')[17][0]['addr']
        self.id=self.mac[9]+self.mac[10]+self.mac[12]+self.mac[13]+self.mac[15]+self.mac[16]
        self.hostname = socket.gethostname()
        print("IP:",self.ip,self.netmask,self.gateway,self.mac,self.id)

    def setiface(self):
        '''try:
            call(["ifconfig", "wlan0", self.ip, "netmask", self.netmask, "broadcast", self.gateway])
            print ("Network config ok")
        except Exception as e:
            print ("Error ifconfig:", e)'''
        file = "/etc/network/interfaces" 
        with open(file,"r+") as fh:
            content = fh.read()
            print("Doc file:",content)
            contentnew=self.set_mode('static', 'eth0', content)
            contentnew=self.set_ip(self.ip,contentnew)
            contentnew=self.set_gateway(self.gateway,contentnew)
            print("Ghi file:",contentnew)
            if file:
                fh.seek(0)
                fh.writelines(contentnew)
                fh.close()
                print("Saved to %s" % file)
            
    def set_mode(self,mode, iface, interfaces):
        iface_prefix = 'iface {} inet '.format(iface)
        iface_entry = iface_prefix + mode
        if iface_prefix in interfaces:
            interfaces = re.sub(iface_prefix + r'.*', iface_entry, interfaces)
        else:
            interfaces += '\n' + iface_entry
        return interfaces
    
    def set_ip(self,ip,interfaces):
        ip_prefix = 'address '
        ip_entry = ip_prefix + ip
        if ip_prefix in interfaces:
            interfaces = re.sub(ip_prefix + r'.*', ip_entry, interfaces)
        else:
            interfaces += '\n' + ip_entry
        return interfaces

    def set_gateway(self,gateway,interfaces):
        gateway_prefix = 'gateway '
        gateway_entry = gateway_prefix + gateway
        if gateway_prefix in interfaces:
            interfaces = re.sub(gateway_prefix + r'.*', gateway_entry, interfaces)
        else:
            interfaces += '\n' + gateway_entry
        return interfaces

# -----Cai dat mang----
'''# Get a collection of objects representing the network adapters.
interface=interfaces()
adapters = networkAdapter()
# You can print the name of each adapter as follows:
adapters.setName("ECAPROVN")
adapters.setBroadcast("192.168.1.254")
# Write your new interfaces file as follows:
# Any changes made with setter methods will be reflected with the new write.
interface.writeInterfaces()'''
Netsetting=netsetting()
Netsetting.Load_setting()
# Phan web truy cap
@webiopi.macro
def load_networksetting():
    data=Netsetting.Load_setting()
    return (data)

@webiopi.macro
def save_networksetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    Netsetting.Save_setting(read)
    return (read)

#---------IO setting----------------------
class iosetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/iosetting.txt"
        self.tsiren3buff=0
        self.tlamp5buff=0
        self.reporthmi=""
        
        self.alarm=1
        self.sms=1
        self.tinfor=24          #Hour
        self.tupload=10          #Min
        self.tsiren3=10         #Min
        self.tlamp5=10          #Min
        self.tloopout12=20      #Min
        self.modeoutgen=0       #auto=0, manual=1
        self.temphighon12=30    #oC
        self.templowoff12=10    #oC
        self.humihighon4=90     #%
        self.meslow=    "Low Alarm"     
        self.meshigh=   "High Alarm"
        self.modeinput=[2,2,2,2,2,2]
        self.modeoutput=[0,0,0,0,0,0]   #=0 che do tu dong, =1 che do bang tay
        self.lowinput=["Hong ngoai bao dong IN1","Bao dong mo cua IN2","Bao dong khoi IN3","Bao dong nhiet tang IN4",\
                       "Bao dong ngap nuoc IN5","Bao dong vo kinh IN6"]
        self.highinput=["Hong ngoai binh thuong IN1","Bao dong dong cua IN2","Bao khoi binh thuong IN3","Nhiet do binh thuong IN4",\
                        "Dau bao nuoc binh thuong IN5","Dau bao kinh binh thuong IN6"]
        self.sireninput=[1,1,1,1,1,1]
        
    def Load_setting(self):
        f = codecs.open(self.file, "r",encoding='utf8')
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        #print("IO Setting:",unicodedata.setting)
        if(len(setting)>=43):
            self.alarm=int(setting[0])
            self.sms=int(setting[1])
            self.tinfor=int(setting[2])          #Hour
            self.tupload=int(setting[3])         #Min
            self.tsiren3=int(setting[4])         #Sec
            self.tlamp5=int(setting[5])          #Min
            self.tloopout12=int(setting[6])      #Min
            self.modeoutgen=int(setting[7])      #auto=0, manual=1
            self.temphighon12=int(setting[8])    #oC
            self.templowoff12=int(setting[9])    #oC
            self.humihighon4=int(setting[10])     #%
            self.meslow=str(setting[11])
            self.meshigh=str(setting[12])
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+13])          
                self.lowinput[i]=setting[i*5+14]      
                self.highinput[i]=setting[i*5+15]
                self.sireninput[i]=int(setting[i*5+16])
                self.modeoutput[i]=int(setting[i*5+17])
            print("Read IO Setting ok")
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+"\n"+str(self.tupload)+"\n"+str(self.tsiren3)+"\n"+str(self.tlamp5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.humihighon4)+"\n"+\
                  str(self.meslow)+"\n"+str(self.meshigh)+"\n"
            for i in range(len(self.modeinput)):  
                data=data+str(self.modeinput[i])+"\n"+str(self.lowinput[i])+"\n"+str(self.highinput[i])+"\n"+str(self.sireninput[i])+"\n"+str(self.modeoutput[i])+"\n"
        else:
            data=""
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+str(self.tupload)+"\n"+"\n"+str(self.tsiren3)+"\n"+str(self.tlamp5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.humihighon4)+"\n"+\
                  str(self.meslow)+"\n"+str(self.meshigh)+"\n"
            for i in range(len(self.modeinput)):  
                data=data+str(self.modeinput[i])+"\n"+str(self.lowinput[i])+"\n"+str(self.highinput[i])+"\n"+str(self.sireninput[i])+"\n"+str(self.modeoutput[i])+"\n"
            print(data)
            self.Save_setting(data)
            print("Default IO Setting ok")
            
        return (data)

    def Save_setting(self,data):
        f = codecs.open(self.file, "w",encoding='utf8')
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        #print (setting)
        if(len(setting)>=43):
            self.alarm=int(setting[0])
            self.sms=int(setting[1])
            self.tinfor=int(setting[2])          #Hour
            self.tupload=int(setting[3])         #Min
            self.tsiren3=int(setting[4])         #Sec
            self.tlamp5=int(setting[5])          #Min
            self.tloopout12=int(setting[6])      #Min
            self.modeoutgen=int(setting[7])      #auto=0, manual=1
            self.temphighon12=int(setting[8])    #oC
            self.templowoff12=int(setting[9])    #oC
            self.humihighon4=int(setting[10])     #%
            self.meslow=str(setting[11])
            self.meshigh=str(setting[12])
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+13])          
                self.lowinput[i]=setting[i*5+14]      
                self.highinput[i]=setting[i*5+15]
                self.sireninput[i]=int(setting[i*5+16])
                self.modeoutput[i]=int(setting[i*5+17])
            # Cap nhat thoi gian
            print(str(setting[i*5+18]))
            os.system("sudo date -s '"+str(setting[i*5+18])+"'")
            print("Saved IO Setting")

# -----Cai dat IO----
IOsetting=iosetting()
IOsetting.Load_setting()
# Phan web truy cap
@webiopi.macro
def load_iosetting():
    data=IOsetting.Load_setting()
    return (data)

@webiopi.macro
def save_iosetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    IOsetting.Save_setting(read)
    return (read)

#-----Setting--------------------------------------------
'''Co 4 dia chi va moi dia chi tuong ung voi 1 dong ho Selec
moi dong ho selec co 22 gia tri can do'''
class settings(object):
    def __init__(self):
        self.file = "/home/pi/bts/Setting"
        self.indexweb=0         # gia tri duoc dieu khien bang web
        self.connect=[]         # So luong ket noi duoc cua 1 dia chi
        self.nameslave=[]       # Ten cua dong ho do
        self.addslave=[]        # Dia chi dong ho
        self.maxchannel=[]        
        self.namechannel=[]
        self.functionchannel=[]
        self.startreg=[]
        self.numberreg=[]
        self.typereg=[]
        self.lowset=[]
        self.highset=[]
        self.unitreg=[]
        for j in range(MAXADDRESS):         #4
            self.connect.append(0)          #0
            self.nameslave.append("Dong ho:"+str(j))
            self.addslave.append(j+1)
            self.maxchannel.append([])
            self.namechannel.append([])
            self.functionchannel.append([])
            self.startreg.append([])
            self.numberreg.append([])
            self.typereg.append([])
            self.lowset.append([])
            self.highset.append([])
            self.unitreg.append([])
            for i in range(MAXCHANNEL):     #4+MAXCHANNEL*8
                self.maxchannel[j].append(MAXCHANNEL)
                self.namechannel[j].append(i)
                self.functionchannel[j].append(i)
                self.startreg[j].append(i)
                self.numberreg[j].append(i)
                self.typereg[j].append(i)
                self.lowset[j].append(i)
                self.highset[j].append(i)
                self.unitreg[j].append(i)
                
    def Load_setting(self,address):
        f = codecs.open(self.file+str(address)+".txt", "r+",encoding='utf8')
        data=f.read()
        f.close()                   # Close opend file
        strdata=str(data)
        setting=strdata.split('\n')
        #print(len(setting),"Read Setting:",setting)
        
        if(len(setting)>=4+MAXCHANNEL*8):
            self.nameslave[address]=str(setting[0])
            self.addslave=int(setting[1])
            self.baud=int(setting[2])
            self.maxchannel[address]=int(setting[3])
            if(self.maxchannel[address]>MAXCHANNEL):
                self.maxchannel[address]=MAXCHANNEL
           
            for i in range(MAXCHANNEL):    #4+MAXCHANNEL*8
                self.namechannel[address][i]=setting[i*8+4]      #ten kenh du lieu
                self.functionchannel[address][i]=int(setting[i*8+5])
                self.startreg[address][i]=int(setting[i*8+6])
                self.numberreg[address][i]=int(setting[i*8+7])
                self.typereg[address][i]=int(setting[i*8+8])        
                self.lowset[address][i]=int(setting[i*8+9])       
                self.highset[address][i]=int(setting[i*8+10])         
                self.unitreg[address][i]=setting[i*8+11]
                
            print("Read Setting ok")
            
        else:       # Default
            self.nameslave[address]="Dong ho:"+str(address+1)
            self.addslave=address
            self.baud=9600
            self.maxchannel[address]=MAXCHANNEL
            for i in range(MAXCHANNEL):    #4+MAXCHANNEL*8
                self.namechannel[address][i]="Channel:"+str(i+1)     #ten kenh du lieu
                self.functionchannel[address][i]=3
                self.startreg[address][i]=i
                self.numberreg[address][i]=1
                self.typereg[address][i]=1                              #16bit
                self.lowset[address][i]=0       
                self.highset[address][i]=100         
                self.unitreg[address][i]="oC"
    
            data=str(self.nameslave[address])+"\n"+str(self.addslave)+"\n"+str(self.baud)+"\n"+str(self.maxchannel[address])+"\n"
            for i in range(len(self.namechannel[address])):    #3+MAXCHANNEL*8
                data=data+str(self.namechannel[address][i])+"\n"
                data=data+str(self.functionchannel[address][i])+"\n"
                data=data+str(self.startreg[address][i])+"\n"
                data=data+str(self.numberreg[address][i])+"\n"
                data=data+str(self.typereg[address][i])+"\n"
                data=data+str(self.lowset[address][i])+"\n"
                data=data+str(self.highset[address][i])+"\n"
                data=data+str(self.unitreg[address][i])+"\n"
                
            self.Save_setting(data)
            print("Default Setting")
        #print (data)
        return (data)
    
    def Save_setting(self,data):
        setting=data.split('\n')
        address=int(setting[1])
        self.nameslave[address]=str(setting[0])
        f = codecs.open(self.file+str(address)+".txt", "w",encoding='utf8')
        f.write(data)
        f.close()
        #print (setting)
        if(len(setting)>=4+MAXCHANNEL*8):
            self.baud=int(setting[2])
            self.maxchannel[address]=int(setting[3])
            for i in range(MAXCHANNEL):    #4+MAXCHANNEL*8
                self.namechannel[address][i]=setting[i*8+4]      #ten kenh du lieu
                self.functionchannel[address][i]=int(setting[i*8+5])
                self.startreg[address][i]=int(setting[i*8+6])
                self.numberreg[address][i]=int(setting[i*8+7])
                self.typereg[address][i]=int(setting[i*8+8])        
                self.lowset[address][i]=int(setting[i*8+9])       
                self.highset[address][i]=int(setting[i*8+10])         
                self.unitreg[address][i]=setting[i*8+11] 
            print("Saved Setting")
            

#------------------ Cai dat----------------------------------------
Set=settings()
for i in range(MAXADDRESS):
    Set.Load_setting(i)
# Phan web truy cap
@webiopi.macro
def load_modbussetting(address):
    data=Set.Load_setting(int(address))
    return (data)

@webiopi.macro
def save_modbussetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    Set.Save_setting(read)
    return (read)
#------------------GSM SMS----------------------
class gsmreport(object):
    def __init__(self):
        self.numbersmsrec=None
        self.textsmsrec=None
        self.timesmsrec=None
        self.csq=None
        self.network=None
        self.reportsms=""
        self.reportgsm=""
Gsm=gsmreport()
def handleSms(sms):
    Gsm.numbersmsrec=sms.number
    Gsm.textsmsrec=sms.text
    Gsm.timesmsrec=sms.time
    data=""
    print('== SMS message received ==\nFrom: {0}\nTime: {1}\nMessage:\n{2}\n'.format(sms.number, sms.time, sms.text))
    
    for i in range(len(Netsetting.tel)):    #5 so dien thoai
        if(sms.number.find(Netsetting.tel[i])==0 and len(Netsetting.tel[i])>=4):
            break
    if(i>=len(Netsetting.tel)-1):
        Gsm.reportsms="Not Admin: "+str(sms.number)
        return
    
    Gsm.reportsms="Admin: "+str(sms.number)+"; Sms: "+str(sms.text)
    if(sms.text.find("Alarm off")!=-1):
        IOsetting.alarm=0
        sms.reply(Netsetting.hostname+'\nAlarm off'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/")
    elif(sms.text.find("Alarm on")!=-1):
        IOsetting.alarm=1
        sms.reply(Netsetting.hostname+'\nAlarm on'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/")
        
    elif(sms.text.find("Value?")!=-1):
        data=str(Set.namechannel[addslavesms][0])+":"+str(usbrtu.readdata[addslavesms][0])+" "+str(Set.unitreg[addslavesms][0])+"\n"+str(Set.namechannel[addslavesms][1])+":"+str(usbrtu.readdata[addslavesms][1])+" "+str(Set.unitreg[addslavesms][1])+"\n"+\
              str(Set.namechannel[addslavesms][2])+":"+str(usbrtu.readdata[addslavesms][2])+" "+str(Set.unitreg[addslavesms][2])+"\n"+str(Set.namechannel[addslavesms][3])+":"+str(usbrtu.readdata[addslavesms][3])+" "+str(Set.unitreg[addslavesms][3])+"\n"+\
              str(Set.namechannel[addslavesms][4])+":"+str(usbrtu.readdata[addslavesms][4])+" "+str(Set.unitreg[addslavesms][4])+"\n"+str(Set.namechannel[addslavesms][5])+":"+str(usbrtu.readdata[addslavesms][5])+" "+str(Set.unitreg[addslavesms][5])+"\n"+\
              str(Set.namechannel[addslavesms][6])+":"+str(usbrtu.readdata[addslavesms][6])+" "+str(Set.unitreg[addslavesms][6])+"\n"+str(Set.namechannel[addslavesms][7])+":"+str(usbrtu.readdata[addslavesms][7])+" "+str(Set.unitreg[addslavesms][7])
        print(data)
        addslavesms=addslavesms+1
        if(addslavesms>=MAXADDRESS):
            addslavesms=0
        sms.reply(Netsetting.hostname+'\n'+data)
        
    elif(sms.text.find("Infor?")!=-1):
        if(IOsetting.alarm):
            data='ARMING\n'
        else:
            data='DISARM\n'
        data=data+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
        data=data+"Output: "+bin(outputstatus)[2:].zfill(6)[::-1]+"\n"
        data=data+"Mode Output:"+bin(modeoutputstatus)[2:].zfill(6)[::-1] +"\n"
        data=data+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
        print(data)
        sms.reply(Netsetting.hostname+'\n'+data)
    else:
        sms.reply(Netsetting.hostname+'\nSai cú pháp SMS!\nInfor?\nValue?\nAlarm on\nAlarm off')
    print('Replying to SMS...')
        
def reportsms(sms):
    if(sms.report==sms.ENROUTE):
        Gsm.reportsms="Status indicating message is still enroute to destination"
    elif(sms.report==sms.DELIVERED):
        Gsm.reportsms="Status indicating message has been received by destination handset"
    else:
        Gsm.reportsms="Status indicating message delivery has failed"
    
    print("Report:",Gsm.reportsms)
sms=gsm.SerialComms(smsReceivedCallbackFunc=handleSms,smsStatusReportCallback=reportsms)
#--------------------------------------------------------
# Called by WebIOPi at script loading
def setup():
    global Beep
    webiopi.debug("Script with macros - Setup")
    # Setup GPIOs
    GPIO.setwarnings(False) 
    GPIO.setup(LEDRUN, GPIO.OUT) # sets i to output and 0V, off
    GPIO.output(LEDRUN,True) 
    GPIO.setup(LEDERROR, GPIO.OUT) # sets i to output and 0V, off
    GPIO.output(LEDERROR,True)
    GPIO.setup(LEDCONNECT, GPIO.OUT) # sets i to output and 0V, off
    GPIO.output(LEDCONNECT,True)
    GPIO.setup(OUTBEEP, GPIO.OUT) # sets i to output and 0V, off
    for i in range(8):   
        GPIO.setup(OUT1+i, GPIO.OUT) # sets i to output and 0V, off
        GPIO.setup(INP1+i, GPIO.IN) # sets i to output and 0V, off
        GPIO.output(OUT1+i,0)
    # tell the GPIO library to look out for an 
    # event on pin 23 and deal with it by calling 
    # the inputEventHandler function
    '''GPIO.add_event_detect(INP1, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP2, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP3, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP4, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP5, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP6, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    #GPIO.add_event_detect(INP7, GPIO.BOTH, callback=inputEventHandler, bouncetime=5000)
    #GPIO.add_event_detect(INP8, GPIO.BOTH, callback=inputEventHandler, bouncetime=5000)'''
    creat_history_data()
    creat_alarm_tablet()
    #-------
    time.sleep(2)
    sms.connect('/dev/ttyUSB1', 115200)

    if(sms.connected==True):    
        sms.setsms()
        Gsm.network=sms.GetNetwork()
        Gsm.csq=sms.signalStrength()
        #sms.SendSMS('+84915086942', 'ECA-GPIs8.8CE running...')'''
    else:
        Gsm.network='not connect USB3G'
        Gsm.csq=0
        
    #Mo cong RS485
    usbrtu.open()
    d = threading.Thread(name='blink', target=blink)
    d.setDaemon(True)
    d.start()
    Beep=2;
#-----------
serial = Serial("ttyAMA0", 9600)
#---------------
# destroy function is called at WebIOPi shutdown
def destroy():
   usbrtu.close()
   sms.close()
# handle the input event Hong ngoai
def inputEventHandler(pin):
    global OUTGENERATOR,CHANGEOUTGENERATOR
    if(IOsetting.alarm==0):
        return
    if(pin==INP1):
        if(IOsetting.modeinput[0]==0 and GPIO.input(INP1)==0):
            insert_alarm_tablet("1: "+str(IOsetting.lowinput[0]))
            if(IOsetting.sireninput[0]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("1:0 ",str(IOsetting.lowinput[0]))
        elif(IOsetting.modeinput[0]==1 and GPIO.input(INP1)==1):
            insert_alarm_tablet("1: "+str(IOsetting.highinput[0]))
            if(IOsetting.sireninput[0]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("1:1 ",str(IOsetting.highinput[0]))
        elif(IOsetting.modeinput[0]==2):
            if(GPIO.input(INP1)==1):
                insert_alarm_tablet("1: "+str(IOsetting.highinput[0]))
                print ("1:2 ",str(IOsetting.highinput[0])+str(IOsetting.tsiren3))
            else:
                insert_alarm_tablet("1: "+str(IOsetting.lowinput[0]))
                print ("1:2 ",str(IOsetting.lowinput[0])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[0]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
    # handle the input event CB Tu
    if(pin==INP2):
        if(IOsetting.modeinput[1]==0 and GPIO.input(INP2)==0):
            insert_alarm_tablet("2: "+str(IOsetting.lowinput[1]))
            if(IOsetting.sireninput[1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("2:0 ",str(IOsetting.lowinput[1]))
        elif(IOsetting.modeinput[1]==1 and GPIO.input(INP2)==1):
            insert_alarm_tablet("2: "+str(IOsetting.highinput[1]))
            if(IOsetting.sireninput[1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("2:1 ",str(IOsetting.highinput[1]))
        elif(IOsetting.modeinput[1]==2):
            if(GPIO.input(INP2)==1):
                insert_alarm_tablet("2: "+str(IOsetting.highinput[1]))
                print ("2:2 ",str(IOsetting.highinput[1])+str(IOsetting.tsiren3))
            else:
                insert_alarm_tablet("2: "+str(IOsetting.lowinput[1]))
                print ("2:2 ",str(IOsetting.lowinput[1])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
    # handle the input event dau bao khoi
    if(pin==INP3):
        if(IOsetting.modeinput[2]==0 and GPIO.input(INP3)==0):
            insert_alarm_tablet("3: "+str(IOsetting.lowinput[2]))
            if(IOsetting.sireninput[2]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("3:0 ",str(IOsetting.lowinput[2]))
        elif(IOsetting.modeinput[2]==1 and GPIO.input(INP3)==1):
            insert_alarm_tablet("3: "+str(IOsetting.highinput[2]))
            if(IOsetting.sireninput[2]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("3:1 ",str(IOsetting.highinput[2]))
        elif(IOsetting.modeinput[2]==2):
            if(GPIO.input(INP3)==1):
                insert_alarm_tablet("3: "+str(IOsetting.highinput[2]))
                print ("3:2 ",str(IOsetting.highinput[2])+str(IOsetting.tsiren3))
            else:
                insert_alarm_tablet("3: "+str(IOsetting.lowinput[2]))
                print ("3:2 ",str(IOsetting.lowinput[2])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[2]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event dau bao nhiet gia tang
    if(pin==INP4):
        if(IOsetting.modeinput[3]==0 and GPIO.input(INP4)==0):
            insert_alarm_tablet("4: "+str(IOsetting.lowinput[3]))
            if(IOsetting.sireninput[3]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("4:0 ",str(IOsetting.lowinput[3]))
        elif(IOsetting.modeinput[3]==1 and GPIO.input(INP4)==1):
            insert_alarm_tablet("4: "+str(IOsetting.highinput[3]))
            if(IOsetting.sireninput[3]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("4:1 ",str(IOsetting.highinput[3]))
        elif(IOsetting.modeinput[3]==2):
            if(GPIO.input(INP4)==1):
                insert_alarm_tablet("4: "+str(IOsetting.highinput[3]))
                print ("4:2 ",str(IOsetting.highinput[3])+str(IOsetting.tsiren3))
            else:
                insert_alarm_tablet("4: "+str(IOsetting.lowinput[3]))
                print ("4:2 ",str(IOsetting.lowinput[3])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[3]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event dau bao ngap nuoc
    if(pin==INP5):
        if(IOsetting.modeinput[4]==0 and GPIO.input(INP5)==0):
            insert_alarm_tablet("5: "+str(IOsetting.lowinput[4]))
            if(IOsetting.sireninput[4]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("5:0 ",str(IOsetting.lowinput[4]))
        elif(IOsetting.modeinput[4]==1 and GPIO.input(INP5)==1):
            insert_alarm_tablet("5: "+str(IOsetting.highinput[4]))
            if(IOsetting.sireninput[4]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("5:1 ",str(IOsetting.highinput[4]))
        elif(IOsetting.modeinput[4]==2):
            if(GPIO.input(INP5)==1):
                insert_alarm_tablet("5: "+str(IOsetting.highinput[4]))
                print ("5:2 ",str(IOsetting.highinput[4])+str(IOsetting.tsiren3))
            else:
                insert_alarm_tablet("5: "+str(IOsetting.lowinput[4]))
                print ("5:2 ",str(IOsetting.lowinput[4])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[4]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event dau bao vo kinh
    if(pin==INP6):
        if(IOsetting.modeinput[5]==0 and GPIO.input(INP6)==0):
            insert_alarm_tablet("6: "+str(IOsetting.lowinput[5]))
            if(IOsetting.sireninput[5]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("6:0 ",str(IOsetting.lowinput[5]))
        elif(IOsetting.modeinput[5]==1 and GPIO.input(INP6)==1):
            insert_alarm_tablet("5: "+str(IOsetting.highinput[5]))
            if(IOsetting.sireninput[5]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("6:1 ",str(IOsetting.highinput[5]))
        elif(IOsetting.modeinput[5]==2):
            if(GPIO.input(INP6)==1):
                insert_alarm_tablet("6: "+str(IOsetting.highinput[5]))
                print ("6:2 ",str(IOsetting.highinput[5])+str(IOsetting.tsiren3))
            else:
                insert_alarm_tablet("6: "+str(IOsetting.lowinput[5]))
                print ("6:2 ",str(IOsetting.lowinput[5])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[5]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
    # handle the input event dau bao dien may phat
    '''if(pin==INP7):
        if(GPIO.input(INP7)==1):
            insert_alarm_tablet("7: "+str(IOsetting.highinput[6]))
            print ("7:2 ",str(IOsetting.highinput[6])+str(IOsetting.tsiren3))
            # Tat 2 dieu hoa
            if(IOsetting.modeoutput[0]==0):
                GPIO.output(OUT1,False)
                air.CHANGEOUT1=1
            if(IOsetting.modeoutput[1]==0):     
                GPIO.output(OUT2,False)
                air.CHANGEOUT2=1
        else:
            insert_alarm_tablet("7: "+str(IOsetting.lowinput[6]))
            print ("7:2 ",str(IOsetting.lowinput[6])+str(IOsetting.tsiren3))
    # handle the input event dau bao dien luoi
    if(pin==INP8):
        if(GPIO.input(INP8)==1):
            insert_alarm_tablet("8: "+str(IOsetting.highinput[7]))
            print ("8:2 ",str(IOsetting.highinput[7])+str(IOsetting.tsiren3))
            # Bat 2 dieu hoa
            if(IOsetting.modeoutput[0]==0):
                GPIO.output(OUT1,True)
                air.CHANGEOUT1=1
            if(IOsetting.modeoutput[1]==0):       
                GPIO.output(OUT2,True)
                air.CHANGEOUT2=1
            # Lenh dung may phat khi co dien luoi
            if(IOsetting.modeoutgen==0):  #che do tu dong
                OUTGENERATOR=0
                CHANGEOUTGENERATOR=1
        else:
            # Lenh dieu khien may phat khi mat dien luoi
            if(IOsetting.modeoutgen==0):  #che do tu dong
                OUTGENERATOR=1
                CHANGEOUTGENERATOR=1
            insert_alarm_tablet("8: "+str(IOsetting.lowinput[7]))
            print ("8:2 ",str(IOsetting.lowinput[7])+str(IOsetting.tsiren3))'''
#-------------------------------------------------------
def messagetoserver(types,message):
    data=""
    if(len(Netsetting.ipserver)):
        data=str(Netsetting.id)+"&"+str(Netsetting.hostname)+ "&"+types+"&"+message+"&"+str(inputstatus)+"&"+str(outputstatus)+"&"+str(modeoutputstatus)+"&"+\
              str(usbrtu.readdata[0])+"&"+str(usbrtu.readdata[1])+"&"+str(usbrtu.readdata[2])+"&"+str(usbrtu.readdata[3])+"&"+str(usbrtu.readdata[4])+"&"+\
              str(usbrtu.readdata[5])+"&"+str(usbrtu.readdata[6])+"&"+str(usbrtu.readdata[7])+"&"+str(usbrtu.readdata[8])+"&"+str(usbrtu.readdata[9])
        print(data)
        client(Netsetting.ipserver, int(Netsetting.portserver), data)
    else:
        Netsetting.reportserver="Not connect Server!"

def client(ip, port, message):
    global Beep,OUTGENERATOR,CHANGEOUTGENERATOR
    readreportserver=""
    binaryoutput=""
    binaryoutputmode=""
    get_bin = lambda x, n: x >= 0 and str(bin(x))[2:].zfill(n) or "-" + str(bin(x))[3:].zfill(n)
    try:
        #create an AF_INET, STREAM socket (TCP)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as msg:
        print ('Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1])
        Netsetting.reportserver='Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]
        sys.exit();
    print ('Socket Created')
  
    try:
        remote_ip = socket.gethostbyname(ip)
    except socket.gaierror:
        #could not resolve
        print ('Hostname could not be resolved. Exiting')
        sys.exit()
        
    sock.settimeout(10)    
    #Connect to remote server
    try:
        sock.connect((ip, port))
    except socket.error as msg:
        Netsetting.reportserver='Failed to connect socket. Error code: '+str(msg)
        print ('Failed to connect socket. Error code: ',str(msg))
        return
    #Netsetting.reportserver='Connected to remote server:'+  str(ip)+':'+str(port)  
    try :
        #Set the whole string
        sock.sendall(bytes(message+"\n","utf8"))
    except socket.error:
        #Send failed
        print ('Send failed')
        return
    Netsetting.sizedatatoserver=Netsetting.sizedatatoserver+len(message)
 
    #Now receive dataread[0]=ID, dataread[1]=Name, dataread[2]= command
    sock.settimeout(10)  
    try:
        dataclient = sock.recv(1024).strip()
    except socket.error as msg:
        Netsetting.reportserver='Failed to recv socket. Error code: '+str(msg)
        sock.close()
        return
    sock.settimeout(None)
    response = str(dataclient, encoding='utf8')
    sock.close()
    print(response)
    # Phan tich du lieu dieu khien tu server toi thiet bi
    '''ID&Name&data0&data1&data2
    Data0=disarm || arming || error || ok
    Data1=output, dữ liệu nhị phân 9 bit, bit thứ 9 điều khiển máy phát
    Data2=mode output, dữ liệu nhị phân 9 bit, bit thứ 9 điều khiển máy phát'''
    if(len(response)>0):
        dataread=response.split('&')
        if(dataread[0].find(Netsetting.id)==0):
            readreportserver="Reiceved: "+response
            #Data0=disarm || arming || error || ok
            if(dataread[2].find("alarmon")==0 or dataread[2].find("ARMING")==0):
                IOsetting.alarm=1
                Beep=1
            elif(dataread[2].find("alarmoff")==0 or dataread[2].find("DISARM")==0):
                IOsetting.alarm=0
                Beep=1
            elif(dataread[2].find("OK")!=-1):
                readreportserver="Reiceved: "+response
            else:
                readreportserver="Error command!"
            print(readreportserver)
            #Data2=mode output, dữ liệu nhị phân 9 bit, bit thứ 9 điều khiển máy phát   
            if(len(dataread[4])>0):
                binaryoutputmode=bin(int(dataread[4]))[2:].zfill(9)[::-1]
                print(binaryoutputmode)
                i=0
                while(i<len(binaryoutputmode)):
                    if(binaryoutputmode[i]=='1' and i<8):
                        IOsetting.modeoutput[i]=1       #che do bang tay
                    elif(binaryoutputmode[i]=='0' and  i<8):
                        if(IOsetting.modeoutput[i]==1):
                            IOsetting.modeoutput[i]=0       #che do tu dong
                    elif(binaryoutputmode[i]=='1' and i==8):
                        OUTGENERATOR=0  
                        CHANGEOUTGENERATOR=1
                    i+=1
                Beep=1 
            #Data1=output, dữ liệu nhị phân 9 bit, bit thứ 9 điều khiển máy phát    
            if(len(dataread[3])>0):
                #binaryoutput=str(get_bin(int(dataread[3]),9))
                binaryoutput=bin(int(dataread[3]))[2:].zfill(9)[::-1] 
                print(binaryoutput)
                i=0
                while(i<len(binaryoutput)):
                    if(binaryoutput[i]=='1' and i<8):
                        #if(IOsetting.modeoutput[i]==1):
                        GPIO.output(OUT1+i,1)
                    elif(binaryoutput[i]=='1' and i==8):
                        OUTGENERATOR=3  #khoi dong may phat bang tay
                        CHANGEOUTGENERATOR=1
                    elif(binaryoutput[i]=='0' and i<8):
                        #if(IOsetting.modeoutput[i]==1): 
                        GPIO.output(OUT1+i,0)
                    elif(binaryoutput[i]=='1' and i==8):
                        OUTGENERATOR=2  #dung may phat bang tay
                        CHANGEOUTGENERATOR=1
                    i+=1
                Beep=1 
        else:
            readreportserver="Error: "+response
            
    Netsetting.reportserver='Sent: '+str(convertSize(Netsetting.sizedatatoserver))+'. '+readreportserver
    '''if(readreportserver.find("Error")!=-1):
        messagetoserver("status","ERROR")
    else:
        messagetoserver("status","OK")'''
    print(Netsetting.reportserver)
#-------------------------------------------------------
# loop function is kiem tra cac tram co ket noi hay khong 
def loop():
    # gives CPU some time before looping again 180 seconds
    global countmin,Beep, inputstatus, outputstatus,modeoutputstatus,lastminute,lasthour,datetimealarms,addslave,addslavesms,looprunning
    data=0
    # Ghi du lieu History data
    now = datetime.datetime.now()
    if(now.year>2016 and now.month > 4):
        return
    looprunning=1
    if(now.minute!=lastminute):
        lastminute=now.minute
        countmin=countmin+1
        print("Den phut:",countmin)
        try:
            url ="http://ecapro.com.vn/vi/tin-tuc/tin-sn-phm/243-giamsatquanlydiennangems"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                the_page = response.read()
                #print(the_page)
        except Exception as e:
            Netsetting.reportserver="Not connect internet:"+str(e)
            print(Netsetting.reportserver)
        # Hen gio nhan tin-------------------------------------
        if(lastminute==0 and IOsetting.tinfor==now.hour):
            Beep=1
            textsms=""
            if(IOsetting.alarm):
                textsms=Netsetting.hostname+'\nARMING\n'
            else:
                textsms=Netsetting.hostname+'\nDISARM\n'
            textsms=textsms+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
            #textsms=textsms+"Output: "+bin(outputstatus)[2:].zfill(6)[::-1]+"\n"
            for j in range(MAXADDRESS):
                if(Set.connect[j]>0):
                    textsms=textsms+str(Set.namechannel[j][0])+":"+str(usbrtu.readdata[j][0])+" "+str(Set.unitreg[j][0])+"\n"
            textsms=textsms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
            
            '''textsms=textsms+str(Set.namechannel[addslavesms][0])+":"+str(usbrtu.readdata[addslavesms][0])+" "+str(Set.unitreg[addslavesms][0])+"\n"+\
                str(Set.namechannel[addslavesms][1])+":"+str(usbrtu.readdata[addslavesms][1])+" "+str(Set.unitreg[addslavesms][1])+"\n"+\
                str(Set.namechannel[addslavesms][2])+":"+str(usbrtu.readdata[addslavesms][2])+" "+str(Set.unitreg[addslavesms][2])+"\n"+\
                str(Set.namechannel[addslavesms][3])+":"+str(usbrtu.readdata[addslavesms][3])+" "+str(Set.unitreg[addslavesms][3])+"\n"
            textsms=textsms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
            addslavesms=addslavesms+1
            if(addslavesms>=MAXADDRESS):
                addslavesms=0
            '''
                
            try:
                MAIL(textsms)
                Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
            except:
                Netsetting.reportserver="Error Mail"   #Khac phuc loi khi nhan tin het tien.
            for i in range(len(Netsetting.tel)):    #5 so dien thoai
                if(len(Netsetting.tel[i])>=4):
                    if(sms.connected==True):
                        try:
                            if(len(textsms)>159):
                                numbersms=int(len(textsms)/159)
                                for j in range(numbersms):
                                    sms.SendSMS(Netsetting.tel[i],textsms[j*159:j*159+159])
                            else:
                                sms.SendSMS(Netsetting.tel[i],textsms[:159])
                            Gsm.reportsms="Sent SMS"
                            print("Sent SMS")
                        except Exception as e:
                            Gsm.reportsms="Error SMS"+str(e)
                            print("Error SMS:",e)                
            
        # Ghi du lieu vao SQL
        if(countmin >= IOsetting.tupload):
            countmin=0
            # Kiem tra song di dong
            if(sms.connected==True):
                try:
                    Gsm.csq=sms.signalStrength()
                except Exception as e:
                    print("CSQ error:",e)
                    
            # Luu tru du lieu
            for j in range(MAXADDRESS):
                if(Set.connect[j]>0):
                    for i in range(Set.maxchannel[j]):
                        print("Write data to sql:",i)
                        try:
                            insert_history_data(j,i,usbrtu.readdata[j][i],usbrtu.status[j][i])
                        except Exception as e:
                            Netsetting.reportserver="Error database:"+str(e)
                            webiopi.debug(Netsetting.reportserver)
            webiopi.debug("Write data to sql.")
      
        # Dieu khien loi ra dieu hoa
        '''air.CountMin=air.CountMin+1
        air.control()'''
        # Huy bao dong ra loa
        if(IOsetting.tsiren3buff>0):
            IOsetting.tsiren3buff=IOsetting.tsiren3buff-1
            print("Tsiren:",IOsetting.tsiren3buff)
            if(IOsetting.tsiren3buff==0 and IOsetting.modeoutput[2]==0):
                GPIO.output(OUT3,False)
        # Ngat den
        if(IOsetting.tlamp5buff>0):
            IOsetting.tlamp5buff=IOsetting.tlamp5buff-1
            if(IOsetting.tlamp5buff==0 and IOsetting.modeoutput[4]==0):
                GPIO.output(OUT5,False)
        # Gui du lieu toi server cu 1 phut 1 lan
        if(IOsetting.alarm):
            data="ARMING"
        else:
            data="DISARM"
        #messagetoserver("status",data)
    if(not q.empty() and IOsetting.alarm):
        alarms=q.get()
        try:
            MAIL(Netsetting.hostname+"\n"+alarms+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/")
        except:
            Netsetting.reportserver="Error Mail"   #Khac phuc loi khi nhan tin het tien.
        for i in range(len(Netsetting.tel)):    #5 so dien thoai
            if(len(Netsetting.tel[i])>=4):
                if(sms.connected==True):
                    text=Netsetting.hostname+"\n"+alarms+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880"
                    print(text)
                    try:
                        sms.SendSMS(Netsetting.tel[i],text[:159])
                        Gsm.reportsms="Sent SMS"
                        Beep=1
                    except:
                        Gsm.reportsms="Error SMS"
        
    #-------------------
    if(now.hour!=lasthour):
        lasthour=now.hour
        Beep=1
    #-------------------
    # Time | Channel | Value | Status | Input | Output
    # Trang thai cac IO
    inputstatus=GPIO.input(INP1)+2*GPIO.input(INP2)+4*GPIO.input(INP3)+8*GPIO.input(INP4)+16*GPIO.input(INP5)+32*GPIO.input(INP6)
    outputstatus=GPIO.input(OUT1)+2*GPIO.input(OUT2)+4*GPIO.input(OUT3)+8*GPIO.input(OUT4)+16*GPIO.input(OUT5)+32*GPIO.input(OUT6)
    modeoutputstatus=IOsetting.modeoutput[0]+2*IOsetting.modeoutput[1]+4*IOsetting.modeoutput[2]+8*IOsetting.modeoutput[3]+16*IOsetting.modeoutput[4]+\
                      32*IOsetting.modeoutput[5]
    
    #for addslave in range(MAXADDRESS):
    con=0    
    try:
        for i in range(Set.maxchannel[addslave]):
            usbrtu.readmodbus(i,addslave+1,Set.functionchannel[addslave][i],Set.startreg[addslave][i],Set.numberreg[addslave][i],Set.typereg[addslave][i])
            if(usbrtu.status[addslave][i]>0):
                con=con+1
    except:
        webiopi.debug("Error loop: "+str(addslave+1)+str(i)+str(sys.exc_info()))
        pass

    Set.connect[addslave]=con
    addslave=addslave+1
    if(addslave>=MAXADDRESS):
        addslave=0
        

    # Su kien canh bao nhiet do,do am
    if(IOsetting.alarm):
        alarmth.Eventtemphumi()
    GPIO.output(LEDCONNECT,not GPIO.input(LEDCONNECT))
    looprunning=1
#---------------------------------------
class AlarmEvents(object):
    def __init__(self):
        self.FlagEventTH=[]
        for j in range(MAXADDRESS):         #4
            self.FlagEventTH.append([])
            for i in range(Set.maxchannel[j]):
                self.FlagEventTH[j].append(0)     #0 Normal, 1 Alarm
                
        GPIO.setup(OUT3, GPIO.OUT)    # Siren
        
    def init(self):                         # Setup output
        GPIO.output(OUT3,False)                 # Siren off
    def finish(self):
        GPIO.output(OUT3,False)
        
    def Eventtemphumi(self):
        global Beep,datetimealarms
        for j in range(MAXADDRESS):
            if(Set.connect[j]>0):
                for i in range(Set.maxchannel[j]):
                    #print(i,"> gia tri kenh:",Set.highset,Set.lowset,self.FlagEventTH)
                    if(usbrtu.readdata[j][i]>int(Set.highset[j][i]) and self.FlagEventTH[j][i]!=1):
                        insert_alarm_tablet(str(IOsetting.meshigh)+"\n"+str(Set.namechannel[j][i])+": "+str(usbrtu.readdata[j][i])+">"+str(Set.highset[j][i])+" "+str(Set.unitreg[j][i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventTH[j][i]=1
                        usbrtu.status[j][i]=3
                        IOsetting.tsiren3buff=IOsetting.tsiren3
                    elif(usbrtu.readdata[j][i]<int(Set.lowset[j][i]) and self.FlagEventTH[j][i]!=2):
                        insert_alarm_tablet(str(IOsetting.meslow)+"\n"+str(Set.namechannel[j][i])+": "+str(usbrtu.readdata[j][i])+"<"+str(Set.lowset[j][i])+" "+str(Set.unitreg[j][i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventTH[j][i]=2
                        usbrtu.status[j][i]=2
                        IOsetting.tsiren3buff=IOsetting.tsiren3
                    elif(usbrtu.readdata[j][i]>int(Set.lowset[j][i]) and usbrtu.readdata[j][i]<int(Set.highset[j][i]) and self.FlagEventTH[j][i]>0):
                        insert_alarm_tablet(str(Set.namechannel[j][i])+": "+str(usbrtu.readdata[j][i])+" "+str(Set.unitreg[j][i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventTH[j][i]=0
                        usbrtu.status[j][i]=1
                
# Khai bao
alarmth=AlarmEvents()
#---------------------------------------
# usbrtu.readdata[0] nhiet do dieu khien dieu hoa Out12
# usbrtu.readdata[1] do am de dieu khien hut am Out4
class Aircontrol(object):
    def __init__(self):
        self.CountSequence=0
        self.CountMin=IOsetting.tloopout12 
        self.Flagoff12=0        #khi may phat hoat dong thi tat 2 dieu hoa
        self.CHANGEOUT1=0
        self.CHANGEOUT2=0
        
        try:
            self.init()
        except Exception as e:
            print("Error Output:",e)
            #self.finish()
    def init(self):    # Setup output
        GPIO.setup(OUT1, GPIO.OUT) # sets i to output and 0V, off
        GPIO.setup(OUT2, GPIO.OUT) # sets i to output and 0V, off
        GPIO.setup(OUT4, GPIO.OUT) # sets i to output and 0V, off
        GPIO.output(OUT1,False)
        GPIO.output(OUT2,False)
        GPIO.output(OUT4,False)
    def finish(self):
        GPIO.output(OUT1,False)
        GPIO.output(OUT2,False)
        GPIO.output(OUT4,False)
    def control(self):
        if(usbrtu.readdata[0]>IOsetting.temphighon12 and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
            GPIO.output(OUT1,True)
            GPIO.output(OUT2,True)
            self.CHANGEOUT1=1
            self.CHANGEOUT2=1
        elif((usbrtu.readdata[0]>0 and usbrtu.readdata[0]<IOsetting.templowoff12 or self.Flagoff12==1) and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
            GPIO.output(OUT1,False)
            GPIO.output(OUT2,False)
            self.CHANGEOUT1=1
            self.CHANGEOUT2=1
        elif(self.CountMin>IOsetting.tloopout12 and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
            self.CountMin=0
            self.CountSequence=self.CountSequence+1
            if(self.CountSequence==2):
                self.CountSequence=0
            if(self.CountSequence==0):
                GPIO.output(OUT1,True)
                GPIO.output(OUT2,False)
                self.CHANGEOUT1=1
                self.CHANGEOUT2=1
            elif(self.CountSequence==1):
                GPIO.output(OUT1,False)
                GPIO.output(OUT2,True)
                self.CHANGEOUT1=1
                self.CHANGEOUT2=1
        if(usbrtu.readdata[1]>IOsetting.humihighon4 and IOsetting.modeoutput[3]==0):
            GPIO.output(OUT4,True)
        elif(IOsetting.modeoutput[3]==0):
            GPIO.output(OUT4,False)
            
# Setup Output
#air=Aircontrol()
#---------------------------------------     
class ModbusRTU(object):
    def __init__(self):
        self.reportmodbus="Start Modbus"
        self.readdata=[]
        self.counterror=[]
        self.status=[]
        for j in range(MAXADDRESS):         #4
            self.readdata.append([])
            self.counterror.append([])
            self.status.append([])
            for i in range(MAXCHANNEL):         #3+MAXCHANNEL*8
                self.readdata[j].append(0)
                self.counterror[j].append(0)
                self.status[j].append(0)        #0 loi, 1 ok connected

        print("Cai dat du lieu:",self.readdata)    
        '''try:
            self.open()
        except Exception as e:
            print("Error USB:",e)
            sys.exit(1)'''
    def open(self):
        self.instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1) # port name, slave address (in decimal)
        self.instrument.debug = False
        self.instrument.serial.port          # this is the serial port name
        self.instrument.serial.baudrate = 9600   # Baud
        self.instrument.serial.bytesize = 8
        self.instrument.serial.stopbits = 1
        self.instrument.serial.timeout  = 1   # seconds
        self.instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode
        self.instrument.precalculate_read_size = False
        """If this is :const:`False`, the serial port reads until timeout
        instead of just reading a specific number of bytes. Defaults to :const:`True`.
        """
        self.instrument.CLOSE_PORT_AFTER_EACH_CALL=True
        print("Port RS485 Open.")
        
    def close(self):
        #sys.exit(1)
        print("Port closed")
        #self.instrument.close()
           
    def readmodbus(self,indexaddress,address,functionchannel,startreg,numberreg,typereg):
        global Beep,CHANGEOUTGENERATOR
        self.instrument.address=address                         # this is the slave address number
        print("Read modbus:",address,startreg,numberreg,functionchannel)
        self.data=0
        try:
            # Cài dat gia tri dieu khien cho may phat voi FC=06
            if(functionchannel==6):
                if(CHANGEOUTGENERATOR==1):
                    self.data = self.instrument.write_register(startreg,OUTGENERATOR,1,6)
                    print("OK read 6 Generator:",self.data)
                    self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
                    if(self.data==OUTGENERATOR):
                        CHANGEOUTGENERATOR=0
                        self.status[address-1][indexaddress]=1
                    else:
                        self.status[address-1][indexaddress]=0
                else:
                    print("Not value 6 Generator:",CHANGEOUTGENERATOR) 
                return 1
            
            #write_bit(registeraddress, value, functioncode=5) For function code 5, the only valid values are 0000 (hex) or FF00 (hex)
            elif(functionchannel==5 and air.CHANGEOUT1==1 and startreg==0):
                self.instrument.write_bit(startreg,GPIO.input(OUT1),5)
                self.status[address-1][indexaddress]=1
                self.data=GPIO.input(OUT1)
                self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
                '''print("OK read 5 Out1:",self.data)
                if((self.data ==0 and GPIO.input(OUT1)==0) or (self.data>0 and GPIO.input(OUT1)==1)):
                    air.CHANGEOUT1=0'''
                return 1

            #write_bit(registeraddress, value, functioncode=5) For function code 5, the only valid values are 0000 (hex) or FF00 (hex)
            elif(functionchannel==5 and air.CHANGEOUT2==1 and startreg==1):
                self.instrument.write_bit(startreg,GPIO.input(OUT2),5)
                self.status[address-1][indexaddress]=1
                self.data=GPIO.input(OUT2)
                self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
                '''print("OK read 5 Out2:",self.data)
                if((self.data ==0 and GPIO.input(OUT2)==0) or (self.data>0 and GPIO.input(OUT2)==1)):
                    air.CHANGEOUT2=0'''
                return 1
            
            #The slave register can hold integer values in the range 0 to 65535 (“Unsigned INT16”).
            elif(Set.typereg[address-1][indexaddress]==1):                          
                self.data = self.instrument.read_register(startreg, numberreg,functionchannel)
                
            #read_long(registeraddress, functioncode=3, signed=False)
            elif(Set.typereg[address-1][indexaddress]==2):                         
                self.data = self.instrument.read_long(startreg,functionchannel, False)
                
            #read_float(registeraddress, functioncode=3, numberOfRegisters=2)
            elif(Set.typereg[address-1][indexaddress]==3):                
                self.data = round(self.instrument.read_float(startreg,functionchannel,numberreg),1)
                
            #read_string(registeraddress, numberOfRegisters=16, functioncode=3)
            elif(Set.typereg[address-1][indexaddress]==4):                
                self.data = self.instrument.read_string(startreg,numberreg,functionchannel)
                
                
            #GPIO.output(LEDERROR,False)
            self.readdata[address-1][indexaddress]=self.data
            self.counterror[address-1][indexaddress]=0
            if(self.status[address-1][indexaddress]==0):
                self.status[address-1][indexaddress]=1
            print("OK read:",self.data)
            self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
            self.instrument.serial.timeout  = 0.1   # seconds
            #print("Doc du lieu:",self.readdata) 
            return self.data
        except Exception as e:
            #GPIO.output(LEDERROR,True)
            #self.open()
            self.counterror[address-1][indexaddress]=self.counterror[address-1][indexaddress]+1
            if(self.counterror[address-1][indexaddress]>10):
                self.counterror[address-1][indexaddress]=0
                if(self.status[address-1][indexaddress]>0):   #Co ket noi roi mat ket noi
                    self.status[address-1][indexaddress]=0
                print("Error read 10:",address,startreg,self.counterror[address-1][indexaddress])
                return 0
            else:
                #Strerror="Error read:"+str(address)+str(self.counterror[indexaddress])+str(e)
                #webiopi.debug(Strerror)
                print("Error read:",address,startreg,indexaddress,self.counterror[address-1][indexaddress],e)
                self.reportmodbus="Error Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
                if(self.status[address-1][indexaddress]==0):   #Mat ket noi                    
                    self.readdata[address-1][indexaddress]=0
                return 0
# Setup USB RS485
usbrtu=ModbusRTU()

#------------------------------------------
def HNI420command(read):
    global outputstatus
    data=""
    if(read.find("Infor?")!=-1):
        
        if(IOsetting.alarm):
            data='ARMING\n'
        else:
            data='DISARM\n'
        data=data+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
        data=data+"Output: "+bin(outputstatus)[2:].zfill(6)[::-1]+"\n"
        data=data+"Mode Output:"+bin(modeoutputstatus)[2:].zfill(6)[::-1] +"\n"
        data=data+strftime("%H:%M:%S, %d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
        print(data)
        serial.writeString(data)       # write a string
        
    elif(read.find("Test?")!=-1):
        data="Network:"+Gsm.network+",CSQ:"+str(Gsm.csq)+"\n"
        data=data+"SMS:"+str(Gsm.reportsms)+"\n"
        data=data+str(Netsetting.reportserver)+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
        print(data)
        serial.writeString(data)       # write a string
        
    elif(read.find("Setting?")!=-1):
        data="My IP:"+str(Netsetting.ip)+"\n"
        data=data+"Gateway:"+str(Netsetting.gateway)+"\n"
        data=data+"Server:"+str(Netsetting.ipserver)+":"+str(Netsetting.portserver)+"\n"        
        print(data)
        serial.writeString(data)       # write a string

    elif(read.find("Temper?")!=-1):
        data=str(Set.namechannel[addslavesms][0])+":"+str(usbrtu.readdata[addslavesms][0])+" "+str(Set.unitreg[addslavesms][0])+"\n"+str(Set.namechannel[addslavesms][1])+":"+str(usbrtu.readdata[addslavesms][1])+" "+str(Set.unitreg[addslavesms][1])+"\n"+\
              str(Set.namechannel[addslavesms][2])+":"+str(usbrtu.readdata[addslavesms][2])+" "+str(Set.unitreg[addslavesms][2])+"\n"+str(Set.namechannel[addslavesms][3])+":"+str(usbrtu.readdata[addslavesms][3])+" "+str(Set.unitreg[addslavesms][3])+"\n"+\
              str(Set.namechannel[addslavesms][4])+":"+str(usbrtu.readdata[addslavesms][4])+" "+str(Set.unitreg[addslavesms][4])+"\n"+str(Set.namechannel[addslavesms][5])+":"+str(usbrtu.readdata[addslavesms][5])+" "+str(Set.unitreg[addslavesms][5])+"\n"+\
              str(Set.namechannel[addslavesms][6])+":"+str(usbrtu.readdata[addslavesms][6])+" "+str(Set.unitreg[addslavesms][6])+"\n"+str(Set.namechannel[addslavesms][7])+":"+str(usbrtu.readdata[addslavesms][7])+" "+str(Set.unitreg[addslavesms][7])
        print(data)
        addslavesms=addslavesms+1
        if(addslavesms>=MAXADDRESS):
            addslavesms=0
        serial.writeString(data)       # write a string
        
        
    elif(read.find("Output")!=-1):      # Output 1 on
        OutputMatch=read.split(" ")
        indexoutput=int(OutputMatch[1])
        if(indexoutput<10 and OutputMatch[2]=="on"):
            GPIO.output(OUT1+indexoutput,1)
        elif(indexoutput<10 and OutputMatch[2]=="off"):
            GPIO.output(OUT1+indexoutput,0)

        outputstatus=GPIO.input(OUT1)+2*GPIO.input(OUT2)+4*GPIO.input(OUT3)+8*GPIO.input(OUT4)+16*GPIO.input(OUT5)+32*GPIO.input(OUT6)
        data="Input: "+bin(inputstatus)[2:].zfill(6)[::-1] 
        data=data+"\nOutput:"+bin(outputstatus)[2:].zfill(6)[::-1] +"\n"
        data=data+strftime("%H:%M:%S, %d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
        print(data)
        serial.writeString(data)       # write a string     
    else:
        print("Error command HMI420")
        serial.writeString("Error command HMI420")       # write a string
#------------------------------------------
# blinking and store history data
from urllib.request import urlretrieve
def blink():
    global Alarmspk,Beep,looprunning
    lastminute=0
    count=0
    while True:
        now = datetime.datetime.now()
        if(looprunning==1 and now.minute==0): #60 phut kiem tra 1 lan
            looprunning=0
        elif(looprunning==0 and now.minute>10):
            looprunning=1
            textsms=Netsetting.hostname+'\nLoop Stop...\n'
            textsms=textsms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880"
            try:
                MAIL(textsms)
                Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
            except:
                Netsetting.reportserver="Error Mail"   #Khac phuc loi khi nhan tin het tien.
            if(sms.connected==True):
                try:
                    sms.SendSMS(Netsetting.tel[0],textsms[:159])
                    Gsm.reportsms="Sent SMS"
                    print("Sent SMS")
                except Exception as e:
                    Gsm.reportsms="Error SMS"+str(e)
                    print("Error SMS:",e)
                    
        # Bat bao dong ra loa
        if(IOsetting.tsiren3buff>0):
            GPIO.output(OUT3,True)
        # Bat den khi bao dong
        if(IOsetting.tlamp5buff>0):
            GPIO.output(OUT5,True)
            
        if(Alarmspk):   # Khi xay ra bao dong
            count=5
            Alarmspk=0
        elif(Beep):
            count=Beep
            Beep=0
        else:
            GPIO.setup(LEDRUN, GPIO.OUT)    # LEDRUN
            GPIO.output(LEDRUN,True)
            time.sleep(0.5)
            GPIO.output(LEDRUN,False)
            time.sleep(0.5)
        while count:
            GPIO.output(OUTBEEP,True)  
            time.sleep(0.1)  
            GPIO.output(OUTBEEP,False)  
            time.sleep(0.1)
            print ("threadName: %s : %d"% (time.ctime(time.time()),count))
            count-=1
        # Ket noi HMI420
        if (serial.available() > 0):
            data = serial.readString()        # read available data as string
            IOsetting.reporthmi=data
            HNI420command(data)

#---Thu nghiem voi chuc nang MAIL----
def MAIL(mailtext):   
    # Construct email
    msg = MIMEText(mailtext.encode('utf-8'), _charset='utf-8')
    msg['To'] = Netsetting.mailto
    msg['From'] = Netsetting.mailfrom
    msg['Subject'] = 'Email alarm from ECA-GPIs6.6CE device'
    # Send the message via an SMTP server
    s = smtplib.SMTP(Netsetting.mailserver,int(Netsetting.mailport))
    '''s.ehlo()
    s.starttls()
    s.ehlo'''
    s.login(Netsetting.mailfrom,Netsetting.mailpass)
    s.sendmail(Netsetting.mailfrom, Netsetting.mailto, msg.as_string())
    s.quit()
#--------------------------------------------------------
# Create new threads with Queue
#queueLock = threading.Lock()
q = queue.Queue()
#--------------------
def convertSize(size):
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB")
   i = int(math.floor(math.log(size,1024)))
   p = math.pow(1024,i)
   s = round(size/p,2)
   if (s > 0):
       return '%s %s' % (s,size_name[i])
   else:
       return '0B'
#---------------------------------------
# Du phong chua dung den
class Gencontrol(object):
    def __init__(self):
        self.SetupMincount=2 
        self.CurrentMincount=0         #2 phut mat dien bat dau khoi dong may phat
        self.SetupSecPreheat=10   
        self.CurrentSecPreheat=0      #Lam nong may 10 sec
        self.CountStart=3       #Khoi dong 3 lan     
        self.SecStart=5         #Moi lan khoi dong 5 giay
        self.OutputPreheat=0    #Loi ra dieu khien lam nong may
        self.OutputStart=0      #Loi ra dieu khien khoi dong
        self.OutputPreheat=0    #Loi ra dieu khien tat may

    def control(self):
        # Mat dien luoi
        if(GPIO.input(INP8)==0):
            self.CurrentMincount=self.CurrentMincount+1
        else:
            self.CurrentMincount=0
        if(self.CurrentMincount>self.SetupMincount):
            self.OutputPreheat=1
            self.CurrentSecPreheat=self.CurrentSecPreheat+1
            if(self.CurrentSecPreheat>self.SetupSecPreheat):
                self.OutputPreheat=0
                self.OutputStart=1   
    def finish(self):
        self.OutputPreheat=0    #Loi ra dieu khien lam nong may
        self.OutputStart=0      #Loi ra dieu khien khoi dong
        self.OutputPreheat=0    #Loi ra dieu khien tat may
