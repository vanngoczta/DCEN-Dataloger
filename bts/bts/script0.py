#!/usr/local/bin/python
# -*- coding: utf-8 -*-
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
MAXCHANNEL=21
# Variable global
global inputstatus,outputstatus,modeoutputstatus,Alarmspk,countsec,countmin,Beep,lastsecond,lastminute,lasthour,datetimealarms
inputstatus=0
outputstatus=0
modeoutputstatus=0
Alarmspk=0
countsec=0
countmin=0
lastsecond=0
lastminute=0
lasthour=0
Beep=0
datetimealarms=""
#-----
# to use Raspberry Pi board pin numbers
#GPIO.setmode(GPIO.BOARD)
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
        data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +","+ str(IOsetting.lowinput[i])+","+str(IOsetting.highinput[i])+","+\
              str(GPIO.input(INP1+i))+","+ str(GPIO.input(OUT1+i))+","+str(IOsetting.modeoutput[i])+"\r\n"
        i=i+1
        if(i>5):
            break
    #print (data)
    conn.close()
    return (data)

# Doc du lieu canh bao theo ngay
@webiopi.macro
def load_alarm_tablet_day(days):
    i=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
     # Hien thi theo kenh va ngay thang
    if(len(days)>0):
        for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate>date('now','localtime','-%s day')  ORDER BY ID DESC" % (days)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
            i=i+1
            if(i>1000):
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
def creat_history_data():
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    print ("Opened database successfully")
    conn.execute('''CREATE TABLE if not exists historydata
    (ID INTEGER PRIMARY KEY AUTOINCREMENT,
    tdate DATE,
    ttime TIME,
    channel NUMERIC,
    value   NUMERIC,
    status  NUMERIC
    );''')
    print ("Table history created successfully")
    conn.close()
    
# store data in the database ok, number
def insert_history_data(channel,value,status):
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    curs.execute("INSERT INTO historydata values(null,date('now','localtime'),time('now','localtime'),(?),(?),(?))",\
                 (channel,value,status))
    # commit the changes
    conn.commit()
    conn.close()
    

# Doc du lieu theo chu ky, khong qua 100 su kien, hien thi index
@webiopi.macro
def load_history_data():
    data=""
    i=0
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # ID |date | time | channel | namechannel | value | unit | status | 
    curs.execute("SELECT * FROM historydata WHERE tdate=date('now','localtime') ORDER BY ID DESC" )
    for row in curs.fetchall():
        data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
        i=i+1
        if(i>30):
            break
    print (data)
    conn.close()
    return (data)


# display the contents of the database channel
@webiopi.macro
def load_history_data_date(startdate,enddate):
    i=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(startdate)>0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (startdate,enddate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)==0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata  WHERE tdate=='%s'  ORDER BY ID DESC" % (enddate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)>0 and len(enddate)==0):
        for row in curs.execute("SELECT * FROM historydata WHERE tdate=='%s'  ORDER BY ID DESC" % (startdate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    print (data)
    conn.close()
    return (data)
# display the contents of the database channel
@webiopi.macro
def load_history_data_day(days):
    i=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(days)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE tdate>date('now','localtime','-%s day')  ORDER BY ID DESC" % (days)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    print (data)
    conn.close()
    return (data)

# display the contents for trend
# Time | Value
@webiopi.macro
def load_history_days_channel(channel,days):
    i=0
    j=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(days)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate>date('now','localtime','-%s day')  ORDER BY tdate DESC, ttime DESC" % (channel,days)):
            j=j+1
            if(j>100):
                j=0
                data=data+str(row[1])+","+ str(row[4])+"\r\n"
            else:
                data=data+str(row[2])+","+ str(row[4])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    print (data)
    conn.close()
    return (data)
# display the contents for trend
# Time | Value
@webiopi.macro
def load_history_date_channel(channel,startdate,enddate):
    i=0
    data=""
    conn=sqlite3.connect(dbname)
    curs=conn.cursor()
    # Hien thi theo kenh va ngay thang
    if(len(startdate)>0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (channel,startdate,enddate)):
            data=data+str(row[2])+","+ str(row[4])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)==0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata  WHERE channel='%s' AND tdate=='%s'  ORDER BY ttime DESC" % (channel,enddate)):
            data=data+str(row[2])+","+ str(row[4])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)>0 and len(enddate)==0):
        for row in curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate=='%s'  ORDER BY ttime DESC" % (channel,startdate)):
            data=data+str(row[2])+","+ str(row[4])+"\r\n"
            i=i+1
            if(i>1000):
                break
                
    print (data)
    conn.close()
    return (data)
# Dieu khien loi ra
@webiopi.macro
def Output(index):
    global Beep,OUTGENERATOR,CHANGEOUTGENERATOR
    if(index=='1'):
        if (GPIO.input(OUT1) == GPIO.LOW):
            GPIO.output(OUT1,1)
            air.CHANGEOUT1=1
        else:
            GPIO.output(OUT1,0)
            air.CHANGEOUT1=1

    if(index=='2'):
        if (GPIO.input(OUT2) == GPIO.LOW):
            GPIO.output(OUT2,1)
            air.CHANGEOUT2=1
        else:
            GPIO.output(OUT2,0)
            air.CHANGEOUT2=1
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
    '''
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
        
    Beep=1
    data=""
    for i in range(Set.maxchannel):
        data=data+strftime("%H:%M:%S",localtime())+","+str(i+1)+"," + Set.namechannel[i] +","
        data=data+str(usbrtu.readdata[i])+","
        data=data+Set.unitreg[i] +","+ str(usbrtu.status[i])+","+str(inputstatus)+","+str(outputstatus)+"\r\n"
        
    return(data)
#-----------------------------
# Liet ke ten cac kenh du lieu
@webiopi.macro
def Listnamechannel():
    data=""
    for i in range(Set.maxchannel):
        data=data+Set.namechannel[i]+"\n"
    return(data)

#-----------------------------        
# Hien thi trang thai dieu khien may phat
# usbrtu.readdata[17] la 1 byte co 8 bit voi 4 bit dau la input và 4 bit sau la output
@webiopi.macro
def UpdateGenerator():
    data=""
    data=str(IOsetting.modeoutgen) +","+str(OUTGENERATOR) +","+ str(usbrtu.readdata[17])+"\r\n"
    return(data)
#-----------------------------        
# Hien thi du lieu tren Index
@webiopi.macro
def UpdateMonitor():
    # Time | channel | namechannel | value | unit | status | Input | 
    data=""
    for i in range(Set.maxchannel):
        data=data+strftime("%H:%M:%S",localtime())+","+str(i+1)+"," + Set.namechannel[i] +","
        data=data+str(usbrtu.readdata[i])+","
        data=data+Set.unitreg[i] +","+ str(usbrtu.status[i])+","+str(inputstatus)+","+str(outputstatus)+"\r\n"
        
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
    data=data+Netsetting.reportserver+","+IOsetting.reporthmi+". "+ usbrtu.reportmodbus+"\r\n"
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
        open(self.file, "r")
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
            time.sleep(2)
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
        self.tlamp5buff=0
        self.tsiren3buff=0
        self.reporthmi=""
        
        self.alarm=1
        self.sms=1
        self.tinfor=24          #Hour
        self.tsiren3=10         #Sec
        self.tlamp5=10          #Min
        self.tloopout12=20      #Min
        self.modeoutgen=0       #auto=0, manual=1
        self.temphighon12=30    #oC
        self.templowoff12=10    #oC
        self.humihighon4=90     #%
        self.modeinput=[2,2,2,2,2,2,2,2]
        self.modeoutput=[0,0,0,0,0,0,0,0]   #=0 che do tu dong, =1 che do bang tay
        self.lowinput=["Hong ngoai bao dong IN1","Bao dong mo cua IN2","Bao dong khoi IN3","Bao dong nhiet tang IN4",\
                       "Bao dong ngap nuoc IN5","Bao dong vo kinh IN6","Co dien may phat IN7","Co dien luoi IN8"]
        self.highinput=["Hong ngoai binh thuong IN1","Bao dong dong cua IN2","Bao khoi binh thuong IN3","Nhiet do binh thuong IN4",\
                        "Dau bao nuoc binh thuong IN5","Dau bao kinh binh thuong IN6","Mat dien may phat IN7","Mat dien luoi IN8"]
        self.sireninput=[1,1,1,1,1,1,1,1]
        
    def Load_setting(self):
        f = codecs.open(self.file, "r",encoding='utf8')
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        #print("IO Setting:",unicodedata.setting)
        if(len(setting)>=50):
            self.alarm=int(setting[0])
            self.sms=int(setting[1])
            self.tinfor=int(setting[2])          #Hour
            self.tsiren3=int(setting[3])         #Sec
            self.tlamp5=int(setting[4])          #Min
            self.tloopout12=int(setting[5])      #Min
            self.modeoutgen=int(setting[6])      #auto=0, manual=1
            self.temphighon12=int(setting[7])    #oC
            self.templowoff12=int(setting[8])    #oC
            self.humihighon4=int(setting[9])     #%
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+10])          
                self.lowinput[i]=setting[i*5+11]      
                self.highinput[i]=setting[i*5+12]
                self.sireninput[i]=int(setting[i*5+13])
                self.modeoutput[i]=int(setting[i*5+14])
            print("Read IO Setting ok")
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+"\n"+str(self.tsiren3)+"\n"+str(self.tlamp5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.humihighon4)+"\n"
            for i in range(len(self.modeinput)):  
                data=data+str(self.modeinput[i])+"\n"+str(self.lowinput[i])+"\n"+str(self.highinput[i])+"\n"+str(self.sireninput[i])+"\n"+str(self.modeoutput[i])+"\n"
        else:
            data=""
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+"\n"+str(self.tsiren3)+"\n"+str(self.tlamp5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.humihighon4)+"\n"
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
        if(len(setting)>=50):
            self.alarm=int(setting[0])
            self.sms=int(setting[1])
            self.tinfor=int(setting[2])     #Hour
            self.tsiren3=int(setting[3])     #Sec
            self.tlamp5=int(setting[4] )         #Min
            self.tloopout12=int(setting[5] )     #Min
            self.modeoutgen=int(setting[6])      #auto=0, manual=1
            self.temphighon12=int(setting[7])    #oC
            self.templowoff12=int(setting[8])    #oC
            self.humihighon4=int(setting[9])     #%
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+10])          
                self.lowinput[i]=setting[i*5+11]      
                self.highinput[i]=setting[i*5+12]
                self.sireninput[i]=int(setting[i*5+13])
                self.modeoutput[i]=int(setting[i*5+14])
            # Cap nhat thoi gian
            print(str(setting[i*5+15]))
            os.system("sudo date -s '"+str(setting[i*5+15])+"'")
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
class settings(object):
    def __init__(self):
        self.file = "/home/pi/bts/Setting.txt"
        self.timeout=1         # Mac dinh 1 sec
        self.connect=0         # So luong ket noi modbus duoc cua 1 dia chi
        self.namechannel=[]
        self.addchannel=[]
        self.functionchannel=[]
        self.startreg=[]
        self.numberreg=[]
        self.typereg=[]
        self.lowset=[]
        self.highset=[]
        self.unitreg=[]
        for i in range(MAXCHANNEL):    #6+MAXCHANNEL*9
            self.namechannel.append(i)
            self.addchannel.append(i)
            self.functionchannel.append(i)
            self.startreg.append(i)
            self.numberreg.append(i)
            self.typereg.append(i)
            self.lowset.append(i)
            self.highset.append(i)
            self.unitreg.append(i)
    def Load_setting(self):
        f = codecs.open(self.file, "r",encoding='utf8')
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        print(len(setting),"Read Setting:",setting)
        if(len(setting)>=6+MAXCHANNEL*9):
            self.baud=int(setting[0])
            self.timeout=float(setting[1])
            self.maxchannel=int(setting[2])
            if(self.maxchannel>MAXCHANNEL):
                self.maxchannel=MAXCHANNEL
            self.tupload=int(setting[3])
            self.meslow=setting[4]
            self.meshigh=setting[5]
            for i in range(MAXCHANNEL):    #6+MAXCHANNEL*9
                #print("index:",i)
                self.namechannel[i]=setting[i*9+6]      #ten kenh du lieu
                self.addchannel[i]=int(setting[i*9+7])        #dia chi slave
                self.functionchannel[i]=int(setting[i*9+8])
                self.startreg[i]=int(setting[i*9+9])
                self.numberreg[i]=int(setting[i*9+10])
                self.typereg[i]=int(setting[i*9+11])        
                self.lowset[i]=int(setting[i*9+12])       
                self.highset[i]=int(setting[i*9+13])         
                self.unitreg[i]=setting[i*9+14]
            
      
            print("Read Setting ok")
        else:
            self.baud=9600
            self.timeout=1
            self.maxchannel=MAXCHANNEL
            self.tupload=1                                  #1 phut
            self.meslow="Low Alarm"
            self.meshigh="High Alarm"
            for i in range(MAXCHANNEL):    #6+MAXCHANNEL*9
                self.namechannel[i]="Channel:"+str(i+1)     #ten kenh du lieu
                self.addchannel[i]=i+1                         #dia chi slave
                self.functionchannel[i]=3
                self.startreg[i]=0
                self.numberreg[i]=1
                self.typereg[i]=1                              #16bit
                self.lowset[i]=0       
                self.highset[i]=100         
                self.unitreg[i]="oC"
    
            data=str(self.baud)+"\n"+str(self.timeout)+"\n"+str(self.maxchannel)+"\n"+str(self.tupload)+"\n"+str(self.meslow)+"\n"+str(self.meshigh)+"\n"
            for i in range(len(self.namechannel)):    #5+MAXCHANNEL*9
                data=data+str(self.namechannel[i])+"\n"
                data=data+str(self.addchannel[i])+"\n"
                data=data+str(self.functionchannel[i])+"\n"
                data=data+str(self.startreg[i])+"\n"
                data=data+str(self.numberreg[i])+"\n"
                data=data+str(self.typereg[i])+"\n"
                data=data+str(self.lowset[i])+"\n"
                data=data+str(self.highset[i])+"\n"
                data=data+str(self.unitreg[i])+"\n"
                
            self.Save_setting(data)
            print("Default Setting")
        #print (data)
        return (data)
    
    def Save_setting(self,data):
        f = codecs.open(self.file, "w",encoding='utf8')
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        #print (setting)
        if(len(setting)>=6+MAXCHANNEL*9):
            self.baud=int(setting[0])
            self.timeout=float(setting[1])
            self.maxchannel=int(setting[2])
            if(self.maxchannel>MAXCHANNEL):
                self.maxchannel=MAXCHANNEL
            self.tupload=int(setting[3])
            self.meslow=setting[4]
            self.meshigh=setting[5]
            for i in range(MAXCHANNEL):    #6+MAXCHANNEL*9
                #print("index:",i)
                self.namechannel[i]=setting[i*9+6]      #ten kenh du lieu
                self.addchannel[i]=int(setting[i*9+7])        #dia chi slave
                self.functionchannel[i]=int(setting[i*9+8])
                self.startreg[i]=int(setting[i*9+9])
                self.numberreg[i]=int(setting[i*9+10])
                self.typereg[i]=int(setting[i*9+11])        
                self.lowset[i]=int(setting[i*9+12])       
                self.highset[i]=int(setting[i*9+13])         
                self.unitreg[i]=setting[i*9+14]
            print("Saved Setting")
            

#------------------ Cai dat----------------------------------------
Set=settings()
Set.Load_setting()
# Phan web truy cap
@webiopi.macro
def load_modbussetting():
    data=Set.Load_setting()
    return (data)

@webiopi.macro
def save_modbussetting(data):
    read=urlparse.unquote(data)
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
Gsm=gsmreport()
def handleSms(sms):
    Gsm.numbersmsrec=sms.number
    Gsm.textsmsrec=sms.text
    Gsm.timesmsrec=sms.time
    data=""
    textsms=""
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
        textsms=Netsetting.hostname+'\nAlarm off'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"

    elif(sms.text.find("Alarm on")!=-1):
        IOsetting.alarm=1
        textsms=Netsetting.hostname+'\nAlarm on'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
        
    elif(sms.text.find("Value?")!=-1):
        data=str(Set.namechannel[0])+":"+str(usbrtu.readdata[0])+" "+str(Set.unitreg[0])+"\n"+str(Set.namechannel[1])+":"+str(usbrtu.readdata[1])+" "+str(Set.unitreg[1])+"\n"+\
              str(Set.namechannel[2])+":"+str(usbrtu.readdata[2])+" "+str(Set.unitreg[2])+"\n"+str(Set.namechannel[3])+":"+str(usbrtu.readdata[3])+" "+str(Set.unitreg[3])+"\n"+\
              str(Set.namechannel[4])+":"+str(usbrtu.readdata[4])+" "+str(Set.unitreg[4])+"\n"+str(Set.namechannel[5])+":"+str(usbrtu.readdata[5])+" "+str(Set.unitreg[5])+"\n"+\
              str(Set.namechannel[6])+":"+str(usbrtu.readdata[6])+" "+str(Set.unitreg[6])+"\n"+str(Set.namechannel[7])+":"+str(usbrtu.readdata[7])+" "+str(Set.unitreg[7])+"\n"+\
              str(Set.namechannel[8])+":"+str(usbrtu.readdata[8])+" "+str(Set.unitreg[8])+"\n"+str(Set.namechannel[9])+":"+str(usbrtu.readdata[9])+" "+str(Set.unitreg[9])
        textsms=Netsetting.hostname+'\n'+data

    elif(sms.text.find("Test?")!=-1):
        data="Network:"+Gsm.network+",CSQ:"+str(Gsm.csq)+"\n"
        data=data+str(Gsm.reportsms)+"\n"
        data=data+str(Netsetting.reportserver)+"\n"+str(Netsetting.ip)+":8880\n"
        data=data+"Modbus conneted:"+str(Set.connect)+"/"+str(Set.maxchannel)
        textsms=Netsetting.hostname+'\n'+data
        
    elif(sms.text.find("Infor?")!=-1):
        if(IOsetting.alarm):
            data='ARMING\n'
        else:
            data='DISARM\n'
        data=data+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
        data=data+"Output: "+bin(outputstatus)[2:].zfill(6)[::-1]+"\n"
        data=data+str(Set.namechannel[0])+":"+str(usbrtu.readdata[0])+" "+str(Set.unitreg[0])+"\n"+\
                str(Set.namechannel[1])+":"+str(usbrtu.readdata[1])+" "+str(Set.unitreg[1])+"\n"+\
                str(Set.namechannel[2])+":"+str(usbrtu.readdata[2])+" "+str(Set.unitreg[2])+"\n"+\
                str(Set.namechannel[3])+":"+str(usbrtu.readdata[3])+" "+str(Set.unitreg[3])+"\n"
        data=data+str(Netsetting.ip)+":8880"
        textsms=Netsetting.hostname+'\n'+data
    else:
        textsms=Netsetting.hostname+'\n'+Gsm.textsmsrec+': Error SMS!\nInfor?\nValue?\nTest?\nAlarm on\nAlarm off'

    print(textsms[:100])
    sms.reply(textsms[:159])
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
    GPIO.setup(OUT1, GPIO.OUT) # sets i to output and 0V, off
    GPIO.setup(OUT2, GPIO.OUT) # sets i to output and 0V, off
    GPIO.setup(OUT3, GPIO.OUT) # sets i to output and 0V, off
    GPIO.setup(OUT4, GPIO.OUT) # sets i to output and 0V, off
    GPIO.setup(OUT5, GPIO.OUT) # sets i to output and 0V, off
    GPIO.setup(OUT6, GPIO.OUT) # sets i to output and 0V, off
    GPIO.setup(INP1, GPIO.IN) # sets i to output and 0V, off
    GPIO.setup(INP2, GPIO.IN) # sets i to output and 0V, off
    GPIO.setup(INP3, GPIO.IN) # sets i to output and 0V, off
    GPIO.setup(INP4, GPIO.IN) # sets i to output and 0V, off
    GPIO.setup(INP5, GPIO.IN) # sets i to output and 0V, off
    GPIO.setup(INP6, GPIO.IN) # sets i to output and 0V, off
    '''for i in range(6):   
        GPIO.setup(int(OUT1+i), GPIO.OUT) # sets i to output and 0V, off
        GPIO.setup(int(INP1+i), GPIO.IN) # sets i to output and 0V, off
        GPIO.output(int(OUT1+i),0)'''
    # tell the GPIO library to look out for an 
    # event on pin 23 and deal with it by calling 
    # the inputEventHandler function
    GPIO.add_event_detect(INP1, GPIO.BOTH, callback=inputEventHandler, bouncetime=100)
    GPIO.add_event_detect(INP2, GPIO.BOTH, callback=inputEventHandler, bouncetime=100)
    GPIO.add_event_detect(INP3, GPIO.BOTH, callback=inputEventHandler, bouncetime=100)
    GPIO.add_event_detect(INP4, GPIO.BOTH, callback=inputEventHandler, bouncetime=100)
    GPIO.add_event_detect(INP5, GPIO.BOTH, callback=inputEventHandler, bouncetime=100)
    GPIO.add_event_detect(INP6, GPIO.BOTH, callback=inputEventHandler, bouncetime=100)
    #GPIO.add_event_detect(INP7, GPIO.BOTH, callback=inputEventHandler, bouncetime=5000)
    #GPIO.add_event_detect(INP8, GPIO.BOTH, callback=inputEventHandler, bouncetime=5000)
    creat_history_data()
    creat_alarm_tablet()
    #-------
    time.sleep(5)
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
   GPIO.cleanup()
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
            time.sleep(1)
            if(GPIO.input(INP1)==1):
                insert_alarm_tablet("1: "+str(IOsetting.highinput[0]))
                print ("1:2 1",str(IOsetting.highinput[0])+str(IOsetting.tsiren3),str(GPIO.input(INP1)))
            else:
                insert_alarm_tablet("1: "+str(IOsetting.lowinput[0]))
                print ("1:2 0",str(IOsetting.lowinput[0])+str(IOsetting.tsiren3),str(GPIO.input(INP1)))
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
    elif(len(Netsetting.reportserver)==0):
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
    global countsec,countmin,Beep, inputstatus, outputstatus,modeoutputstatus,lastsecond,lastminute,lasthour,datetimealarms
    data=0
    # Ghi du lieu History data
    now = datetime.datetime.now()
    # Kiem tra theo giay
    if(now.second!=lastsecond):
        if(lastsecond>now.second): 
            countsec=countsec+lastsecond-now.second
        else:
            countsec=countsec+now.second+60-lastsecond
        lastsecond=now.second
        if(countsec>30):    #20 giay kiem tra tin nhan toi 1 lan
            counsec=0
            # Kiem tra tin nhan toi, dung Huawei E303H
            if(sms.connected==True):
                try:
                    sms.processStoredSms(False)
                    GPIO.output(LEDERROR,False)
                except:
                    GPIO.output(LEDERROR,True)
                
    # Kiem tra theo phut            
    if(now.minute!=lastminute):
        lastminute=now.minute
        # Hen gio nhan tin-------------------------------------
        if(lastminute==0 and IOsetting.tinfor==now.hour):
            textsms=""
            if(IOsetting.alarm):
                textsms='ARMING\n'
            else:
                textsms='DISARM\n'
            textsms=textsms+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
            textsms=textsms+"Output: "+bin(outputstatus)[2:].zfill(6)[::-1]+"\n"
            textsms=textsms+str(Set.namechannel[0])+":"+str(usbrtu.readdata[0])+" "+str(Set.unitreg[0])+"\n"+\
                str(Set.namechannel[1])+":"+str(usbrtu.readdata[1])+" "+str(Set.unitreg[1])+"\n"+\
                str(Set.namechannel[2])+":"+str(usbrtu.readdata[2])+" "+str(Set.unitreg[2])+"\n"+\
                str(Set.namechannel[3])+":"+str(usbrtu.readdata[3])+" "+str(Set.unitreg[3])+"\n"
            textsms=textsms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880"
            try:
                MAIL(textsms)
                Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
            except:
                Netsetting.reportserver="Error Mail"   #Khac phuc loi khi nhan tin het tien.
            for i in range(len(Netsetting.tel)):    #5 so dien thoai
                if(len(Netsetting.tel[i])>=4):
                    if(sms.connected==True):
                        try:
                            sms.SendSMS(Netsetting.tel[i],textsms[:159])
                            Gsm.reportsms="Sent SMS"
                            print("Sent SMS")
                        except Exception as e:
                            Gsm.reportsms="Error SMS"+str(e)
                            print("Error SMS:",e)
                    
        countmin=countmin+1
        print("Den phut:",countmin)
        # Tre giua lan bao dong lien tiep
        for i in range(Set.maxchannel):
            alarmth.Tdelay[i]=0
        # Thoi gian ghi du lieu SQL
        if(countmin >= Set.tupload):
            countmin=0
            # Kiem tra song di dong
            try:
                Gsm.csq=sms.signalStrength()
            except Exception as e:
                print("CSQ error:",e)
            # Luu tru du lieu
            for i in range(Set.maxchannel):
                print("Write data to sql:",i)
                insert_history_data(i,usbrtu.readdata[i],usbrtu.status[i])
            
        # Dieu khien loi ra dieu hoa
        air.CountMin=air.CountMin+1
        air.control()
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
        messagetoserver("status",data)
    if(data==0 and not q.empty() and IOsetting.alarm):
        alarms=q.get()
        messagetoserver("alarm",alarms)
        try:
            MAIL(Netsetting.hostname+"\n"+alarms+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/")
            Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
        except:
            Netsetting.reportserver="Error Mail"   #Khac phuc loi khi nhan tin het tien.
        for i in range(len(Netsetting.tel)):    #5 so dien thoai
            if(len(Netsetting.tel[i])>=4):
                if(sms.connected==True and IOsetting.sms):
                    text=Netsetting.hostname+"\n"+alarms+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880"
                    print(text)
                    try:
                        sms.SendSMS(Netsetting.tel[i],text[:159])
                        Gsm.reportsms="Sent SMS"
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
                      32*IOsetting.modeoutput[5]+64*IOsetting.modeoutput[6]+128*IOsetting.modeoutput[7]
    #usbrtu.strdatatable=""
    con=0
    try:
        for i in range(Set.maxchannel):
            usbrtu.readmodbus(i,Set.addchannel[i],Set.functionchannel[i],Set.startreg[i],Set.numberreg[i],Set.typereg[i])
            if(usbrtu.status[i]>0):
                con=con+1
            
    except:
        webiopi.debug("Error loop: "+str(Set.addchannel[i])+str(i)+str(sys.exc_info()[0]))
        pass
    Set.connect=con
       
    # Su kien canh bao nhiet do,do am
    if(IOsetting.alarm):
        alarmth.Eventtemphumi()
    GPIO.output(LEDCONNECT,not GPIO.input(LEDCONNECT))
#---------------------------------------
class AlarmEvents(object):
    def __init__(self):
        self.FlagEventTH=[]
        self.Tdelay=[]
        #self.Tsiren=0
        for i in range(Set.maxchannel):
            self.FlagEventTH.append(0)     #0 Normal, 1 Alarm
            self.Tdelay.append(1)           #1 tinh bang phut
        GPIO.setup(OUT3, GPIO.OUT)    # Siren
        
    def init(self):                         # Setup output
        GPIO.output(OUT3,False)                 # Siren off
    def finish(self):
        GPIO.output(OUT3,False)
        
    def Eventtemphumi(self):
        global Beep,datetimealarms
        for i in range(Set.maxchannel):
            #print(i,"> gia tri kenh:",Set.highset,Set.lowset,self.FlagEventTH)
            if(usbrtu.readdata[i]>int(Set.highset[i]) and self.FlagEventTH[i]!=1 and self.Tdelay[i]==0):
                insert_alarm_tablet(str(Set.meshigh)+"\n"+str(Set.namechannel[i])+": "+str(usbrtu.readdata[i])+">"+str(Set.highset[i])+" "+str(Set.unitreg[i]))
                datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                self.FlagEventTH[i]=1
                usbrtu.status[i]=3
                IOsetting.tsiren3buff=IOsetting.tsiren3
                self.Tdelay[i]=1
            elif(usbrtu.readdata[i]<int(Set.lowset[i]) and self.FlagEventTH[i]!=2 and self.Tdelay[i]==0):
                insert_alarm_tablet(str(Set.meslow)+"\n"+str(Set.namechannel[i])+": "+str(usbrtu.readdata[i])+"<"+str(Set.lowset[i])+" "+str(Set.unitreg[i]))
                datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                self.FlagEventTH[i]=2
                usbrtu.status[i]=2
                IOsetting.tsiren3buff=IOsetting.tsiren3
                self.Tdelay[i]=1
            elif(usbrtu.readdata[i]>int(Set.lowset[i]) and usbrtu.readdata[i]<int(Set.highset[i]) and self.FlagEventTH[i]>0 and self.Tdelay[i]==0):
                insert_alarm_tablet(str(Set.namechannel[i])+": "+str(usbrtu.readdata[i])+" "+str(Set.unitreg[i]))
                datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                self.FlagEventTH[i]=0
                usbrtu.status[i]=1
                self.Tdelay[i]=1
            
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
air=Aircontrol()
#---------------------------------------     
class ModbusRTU(object):
    def __init__(self):
        self.reportmodbus="Start Modbus"
        self.readdata=[]
        self.counterror=[]
        self.status=[]
        self.strdatatable=""
        for i in range(MAXCHANNEL):
            self.readdata.append(0)
            self.status.append(0)       #0 loi, 1 ok connected
            self.counterror.append(0)
        print("Cai dat dulieu =0",self.readdata)    
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
        self.instrument.serial.timeout  = 2   # seconds
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
                        self.status[indexaddress]=1
                    else:
                        self.status[indexaddress]=0
                else:
                    print("Not value 6 Generator:",CHANGEOUTGENERATOR) 
                return 1
            
            #write_bit(registeraddress, value, functioncode=5) For function code 5, the only valid values are 0000 (hex) or FF00 (hex)
            elif(functionchannel==5 and air.CHANGEOUT1==1 and startreg==0):
                self.instrument.write_bit(startreg,GPIO.input(OUT1),5)
                self.status[indexaddress]=1
                self.data=GPIO.input(OUT1)
                self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
                '''print("OK read 5 Out1:",self.data)
                if((self.data ==0 and GPIO.input(OUT1)==0) or (self.data>0 and GPIO.input(OUT1)==1)):
                    air.CHANGEOUT1=0'''
                return 1

            #write_bit(registeraddress, value, functioncode=5) For function code 5, the only valid values are 0000 (hex) or FF00 (hex)
            elif(functionchannel==5 and air.CHANGEOUT2==1 and startreg==1):
                self.instrument.write_bit(startreg,GPIO.input(OUT2),5)
                self.status[indexaddress]=1
                self.data=GPIO.input(OUT2)
                self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
                '''print("OK read 5 Out2:",self.data)
                if((self.data ==0 and GPIO.input(OUT2)==0) or (self.data>0 and GPIO.input(OUT2)==1)):
                    air.CHANGEOUT2=0'''
                return 1
            
            #The slave register can hold integer values in the range 0 to 65535 (“Unsigned INT16”).
            elif(Set.typereg[indexaddress]==1):                          
                self.data = self.instrument.read_register(startreg, numberreg,functionchannel)
                
            #read_long(registeraddress, functioncode=3, signed=False)
            elif(Set.typereg[indexaddress]==2):                         
                self.data = self.instrument.read_long(startreg,functionchannel, False)
                
            #read_float(registeraddress, functioncode=3, numberOfRegisters=2)
            elif(Set.typereg[indexaddress]==3):                
                self.data = round(self.instrument.read_float(startreg,functionchannel,numberreg),1)
                
            #read_string(registeraddress, numberOfRegisters=16, functioncode=3)
            elif(Set.typereg[indexaddress]==4):                
                self.data = self.instrument.read_string(startreg,numberreg,functionchannel)
                
                
            #GPIO.output(LEDERROR,False)
            self.readdata[indexaddress]=self.data
            self.counterror[indexaddress]=0
            if(self.status[indexaddress]==0):
                self.status[indexaddress]=1
            print("OK read:",self.data)
            self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
            self.instrument.serial.timeout  = Set.timeout   # seconds
            return self.data
        except Exception as e:
            #GPIO.output(LEDERROR,True)
            #self.open()
            self.counterror[indexaddress]=self.counterror[indexaddress]+1
            if(self.counterror[indexaddress]>10):
                self.counterror[indexaddress]=0
                if(self.status[indexaddress]>0):   #Co ket noi roi mat ket noi
                    self.status[indexaddress]=0
                print("Error read 10:",address,startreg,self.counterror[indexaddress])
                return 0
            else:
                #Strerror="Error read:"+str(address)+str(self.counterror[indexaddress])+str(e)
                #webiopi.debug(Strerror)
                print("Error read:",address,startreg,indexaddress,self.counterror[indexaddress],e)
                self.reportmodbus="Error Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
                if(self.status[indexaddress]==0):   #Mat ket noi                    
                    self.readdata[indexaddress]=0
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
        data=data+str(Netsetting.reportserver)+"\n"+str(Netsetting.ip)+":8880\nModbus conneted:"+str(Set.connect)+"/"+str(Set.maxchannel)
        print(data)
        serial.writeString(data)       # write a string
        
    elif(read.find("Setting?")!=-1):
        data="My IP:"+str(Netsetting.ip)+"\n"
        data=data+"My Gateway:"+str(Netsetting.gateway)+"\n"
        data=data+"Server:"+str(Netsetting.ipserver)+":"+str(Netsetting.portserver)+"\n"        
        print(data)
        serial.writeString(data)       # write a string

    elif(read.find("Temper?")!=-1):
        data=str(Set.namechannel[0])+":"+str(usbrtu.readdata[0])+" "+str(Set.unitreg[0])+"\n"+str(Set.namechannel[1])+":"+str(usbrtu.readdata[1])+" "+str(Set.unitreg[1])+"\n"+\
              str(Set.namechannel[2])+":"+str(usbrtu.readdata[2])+" "+str(Set.unitreg[2])+"\n"+str(Set.namechannel[3])+":"+str(usbrtu.readdata[3])+" "+str(Set.unitreg[3])+"\n"+\
              str(Set.namechannel[4])+":"+str(usbrtu.readdata[4])+" "+str(Set.unitreg[4])+"\n"+str(Set.namechannel[5])+":"+str(usbrtu.readdata[5])+" "+str(Set.unitreg[5])+"\n"+\
              str(Set.namechannel[6])+":"+str(usbrtu.readdata[6])+" "+str(Set.unitreg[6])+"\n"+str(Set.namechannel[7])+":"+str(usbrtu.readdata[7])+" "+str(Set.unitreg[7])
        print(data)
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
    global Alarmspk,Beep
    lastminute=0
    count=0
    while True:
        if(webiopi.running==False):
            count=1 
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
