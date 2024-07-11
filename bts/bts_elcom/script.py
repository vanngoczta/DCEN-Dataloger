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
# 10 LOI RA DK BANG RS485, AUTO=0, MANUAL=1
#OUTPUT485   = [0,0,0,0,0,0,0,0,0,0]
#MODOUTPUT485= [0,0,0,0,0,0,0,0,0,0]
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
MAXINPUTGEN=5
MAXMODULEIR=10
MAXINPUTSMOKE=10
MAXCHANNEL=20
MAXINPUT=6
MAXPAGE=7
# Variable global
global inputstatus,outputstatus,modeoutputstatus,Alarmspk,countsec,countmin,Beep,lastsecond,lastminute,lasthour,datetimealarms,pageindex,pageindexsms,looprunning
global indextask,countminsql,lastminutesql
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
pageindex=0
pageindexsms=0
looprunning=1
indextask=0
countminsql=0
lastminutesql=0
#-----
GPIO.setwarnings(False) 
GPIO.setup(LEDRUN, GPIO.OUT) # sets i to output and 0V, off
GPIO.setup(LEDERROR, GPIO.OUT) # sets i to output and 0V, off
GPIO.setup(OUTBEEP, GPIO.OUT) # sets i to output and 0V, off
#---------------------------------------------------------------------------
version="BTS:29.09.16" 
dbname='/home/pi/bts/database.db'
sys.path.append("/home/pi/webiopi/htdocss")  #<--- or whatever your path is !

# Enable debug output
# webiopi.setDebug()
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
    for row in curs.fetchmany(100):
        data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"

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
    for row in curs.fetchmany(6):
        data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +","+ str(IOsetting.lowinput[i])+","+str(IOsetting.highinput[i])+","+\
              str(GPIO.input(INP1+i))+","+ str(GPIO.input(OUT1+i))+","+str(IOsetting.modeoutput[i])+"\r\n"
        i=i+1
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
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ SetModbus.namechannel[address][row[4]] + "," + str(row[5])+","+SetModbus.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)==0 and len(enddate)>0):
        for row in curs.execute("SELECT * FROM historydata  WHERE address=='%s' AND tdate=='%s'  ORDER BY ID DESC" % (address,enddate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ SetModbus.namechannel[address][row[4]] + "," + str(row[5])+","+SetModbus.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
            i=i+1
            if(i>1000):
                break
    elif (len(startdate)>0 and len(enddate)==0):
        for row in curs.execute("SELECT * FROM historydata WHERE address=='%s' AND tdate=='%s'  ORDER BY ID DESC" % (address,startdate)):
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ SetModbus.namechannel[address][row[4]] + "," + str(row[5])+","+SetModbus.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
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
            data=data+str(row[0])+","+str(row[1])+","+str(row[2])+","+str(row[4])+","+ SetModbus.namechannel[address][row[4]] + "," + str(row[5])+","+SetModbus.unitreg[address][row[4]]+","+str(row[6])+"\r\n"
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
#--------------------------------------------
# Dieu khien loi ra bang tay.
# Cac loi ra nay doc lap voi module dieu khien qua RS485
@webiopi.macro
def Output(index):
    global Beep,OUTGENERATOR,CHANGEOUTGENERATOR
    if(index=='1'):
        if (GPIO.input(OUT1) == GPIO.LOW):
            GPIO.output(OUT1,1)
        else:
            GPIO.output(OUT1,0)

    if(index=='2'):
        if (GPIO.input(OUT2) == GPIO.LOW):
            GPIO.output(OUT2,1)
        else:
            GPIO.output(OUT2,0)
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
    page=int(indexadd)
    for i in range(SetModbus.maxchannel[page]):
        data=data+SetModbus.namechannel[page][i]+"\n"
    return(data)

#-----------------------------        
# Hien thi trang thai dieu khien may phat
# SetModbus.readvalue[17] là 1 byte có 8 bit voi 4 bit dau la input và 4 bit sau la output
@webiopi.macro
def UpdateGenerator():
    data=""
    data=str(IOsetting.modeoutgen) +","+str(OUTGENERATOR) +","+ str(SetModbus.readvalue[17])+"\r\n"
    return(data)
#-----------------------------        
# Hien thi du lieu tren Graph Scada
@webiopi.macro
def UpdatePower():
    # namechannel | value | unit | status | lowset | high
    data=""
    for page in range(MAXPAGE):
        for i in range(SetModbus.indexweb,SetModbus.indexweb+3):
            data=data+ SetModbus.namechannel[page][i] +","+str(SetModbus.readvalue[page][i])+","+SetModbus.unitreg[page][i] +","
            data=data+ str(SetModbus.statusconnect[page][i])+","+str(SetModbus.lowset[page][i]) +","+ str(SetModbus.highset[page][i])+"\r\n"
        
    return(data)
@webiopi.macro
def Modedisplay(control):
    if(control=='1' and SetModbus.indexweb<MAXCHANNEL-3):
        SetModbus.indexweb=SetModbus.indexweb+3
    elif (control=='2' and SetModbus.indexweb>=3):
        SetModbus.indexweb=SetModbus.indexweb-3
    return(SetModbus.indexweb) 
#-----------------------------        
# Hien thi du lieu tren Index
@webiopi.macro
def UpdateMonitor(indexadd):
    # Time | channel | namechannel | value | unit | status | Input | 
    data=""
    address=int(indexadd)
    for i in range(SetModbus.maxchannel[address]):
        data=data+strftime("%H:%M:%S",localtime())+","+str(i+1)+"," + SetModbus.namechannel[address][i] +","
        data=data+str(SetModbus.readvalue[address][i])+","
        data=data+SetModbus.unitreg[address][i] +","+ str(SetModbus.statusconnect[address][i])+","+str(inputstatus)+","+str(outputstatus)+"\r\n"
        
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
    for i in range(MAXPAGE):
        data=data+str(SetModbus.nameslave[i])+","+str(SetModbus.connect[i])+","+str(SetModbus.maxchannel[i])+"\r\n"
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
    data=data+Netsetting.reportserver[:30]+","+IOsetting.reporthmi[:30]+". "+ usbrtu.reportmodbus[:40]+','+str(IOsetting.modehome)+"\r\n"
    return(data)
#-----Hien thi tren index cac lenh cusd-----
@webiopi.macro
def SendCusd(data):
    sms.dial(data+"#")
    print(sms._ussdResponse)
    return (sms._ussdResponse)
#-------------------------
def validate_ip(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True
#---------Net setting----------------------
class netsetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/Netsetting.txt"
        open(self.file, "r")
        self.sizedatatoserver=0
        self.reportserver=""
        self.id=""
        self.mac=""
        self.hostname="GPIs6.6CE-BTS"
        self.dhcp=1
        self.ip="192.168.1.211"
        self.gateway="192.168.1.1"
        self.mask="255.255.255.0"
        self.ipserver="192.168.1.210"
        self.portserver="9999"
        self.tel=["+84915086942","0","0","0","0"]
        self.username=""
        self.newpass=""
        self.conpass=""
        self.mailserver="ecapro.com.vn"
        self.mailport="25"
        self.mailfrom="info@ecapro.com.vn"
        self.mailpass="ecaprovn"
        self.mailto0="giamsatnhietdo.ecapro@gmail.com"
        self.mailto1=""
        self.mailto2=""
        self.bodysms=""
        self.bodyemail=""
    def Load_setting(self):
        f = open(self.file, "r")
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        print("Network Setting:",setting)
        if(len(setting)>=23):
            '''self.mac=setting[0]
            self.hostname=setting[1]
            self.dhcp=int(setting[2])
            self.ip=setting[3]
            self.gateway=setting[4]
            self.mask=setting[5]'''
            try:
                self.getiface()
                self.hostname=setting[1]
            except Exception as e:
                self.mac=setting[0]
                self.hostname=setting[1]
                self.dhcp=int(setting[2])
                self.ip=setting[3]
                self.gateway=setting[4]
                self.mask=setting[5]
           
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
            self.mailto0=setting[20]
            self.mailto1=setting[21]
            self.mailto2=setting[22]
            print("Read Net Setting ok")
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            for i in range(len(self.tel)):   
                data=data+str(self.tel[i])+"\n"
            #data=data+str(self.username)+"\n"+str(self.newpass)+"\n"+str(self.conpass)+"\n"\
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto0)+"\n"+str(self.mailto1)+"\n"+str(self.mailto2)+"\n"
        else:
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            for i in range(len(self.tel)):   
                data=data+str(self.tel[i])+"\n"
            #data=data+str(self.username)+"\n"+str(self.newpass)+"\n"+str(self.conpass)+"\n"\
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto0)+"\n"+str(self.mailto1)+"\n"+str(self.mailto2)+"\n"
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
        if(len(setting)>=23):
            self.mac=setting[0]
            self.hostname=setting[1]
            self.dhcp=int(setting[2])
            #if(validate_ip(setting[3])):
            self.ip=setting[3]
            #if(validate_ip(setting[4])):
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
            self.mailto0=setting[20]
            self.mailto1=setting[21]
            self.mailto2=setting[22]
            if(len(self.username)>0 and len(self.newpass)>0 and len(self.conpass)>0):
                if(self.save_pass()==False):
                    return
            self.setiface()
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            for i in range(len(self.tel)):   
                data=data+str(self.tel[i])+"\n"
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto0)+"\n"+str(self.mailto1)+"\n"+str(self.mailto2)+"\n"
            print("Saved Net Setting")
            return (data)
            
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
    return (Netsetting.Save_setting(read))

@webiopi.macro
def Reboot():
    # shutdown our Raspberry Pi
    os.system("sudo reboot")

#---------IO setting----------------------
class iosetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/iosetting.txt"
        self.modehome=0
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
        if(len(setting)>=44):
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
            self.modehome=int(setting[13])          #0= full, 1= value
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+14])          
                self.lowinput[i]=setting[i*5+15]      
                self.highinput[i]=setting[i*5+16]
                self.sireninput[i]=int(setting[i*5+17])
                self.modeoutput[i]=int(setting[i*5+18])
            print("Read IO Setting ok")
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+"\n"+str(self.tupload)+"\n"+str(self.tsiren3)+"\n"+str(self.tlamp5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.humihighon4)+"\n"+\
                  str(self.meslow)+"\n"+str(self.meshigh)+"\n"+\
                  str(self.modehome)+"\n"
            for i in range(len(self.modeinput)):  
                data=data+str(self.modeinput[i])+"\n"+str(self.lowinput[i])+"\n"+str(self.highinput[i])+"\n"+str(self.sireninput[i])+"\n"+str(self.modeoutput[i])+"\n"
        else:       #default
            data=""
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+"\n"+str(self.tupload)+"\n"+str(self.tsiren3)+"\n"+str(self.tlamp5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.humihighon4)+"\n"+\
                  str(self.meslow)+"\n"+str(self.meshigh)+"\n"+\
                  str(self.modehome)+"\n"
            for i in range(len(self.modeinput)):  
                data=data+str(self.modeinput[i])+"\n"+str(self.lowinput[i])+"\n"+str(self.highinput[i])+"\n"+str(self.sireninput[i])+"\n"+str(self.modeoutput[i])+"\n"
            #print(data)
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
        if(len(setting)>=44):
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
            self.modehome=int(setting[13])          #0= full, 1= value
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+14])          
                self.lowinput[i]=setting[i*5+15]      
                self.highinput[i]=setting[i*5+16]
                self.sireninput[i]=int(setting[i*5+17])
                self.modeoutput[i]=int(setting[i*5+18])
            # Cap nhat thoi gian
            os.system("sudo date -s '"+str(setting[i*5+19])+"'")
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

#-----Smoke Setting-------
# Sua moi danh cho BTS Elcom
# 17/09/16
class smokesetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/smokesetting.txt"
        self.reportmodule="Not connect"             
        self.InputSmokeInt1=0
        self.InputSmokeInt2=0
        self.maxinputmodule1=10         # So loi vao toi da module1 =10
        self.maxinputmodule2=10         # So loi vao toi da module2 =10
        self.timeout3=10     # 10 phut
        self.mesalarm="Alarm"
        self.mesnormal="Normal"
        self.namemodule1=[]
        self.modemodule1=[]
        self.namemodule2=[]
        self.modemodule2=[]
        self.FlagEventSmoke1=[]
        self.FlagEventSmoke2=[]
        for i in range(MAXINPUTSMOKE):
            self.namemodule1.append("Smoke1:"+str(i+1))
            self.modemodule1.append(1)      #0 Close alarm, 1 Open Alarm, 2 Not use
            self.namemodule2.append("Smoke2:"+str(i+1))
            self.modemodule2.append(1)      #0 Close alarm, 1 Open Alarm, 2 Not use
            self.FlagEventSmoke1.append(0)  #0 Normal, 1 Alarm
            self.FlagEventSmoke2.append(0)  #0 Normal, 1 Alarm

    def Load_setting(self):
        f = codecs.open(self.file, "r+",encoding='utf8')
        data=f.read()
        f.close()                   # Close opend file
        strdata=str(data)
        setting=strdata.split('\n')
        
        if(len(setting)>=5+MAXINPUTSMOKE*4):                       # 5 gia tri dau va 4 gia tri lap lai  
            self.maxinputmodule1=int(setting[0])
            self.maxinputmodule2=int(setting[1])
            self.timeout3=int(setting[2])
            self.mesalarm=str(setting[3])
            self.mesnormal=str(setting[4])
            for i in range(MAXINPUTSMOKE):    
                self.namemodule1[i]=str(setting[i*2+5])     
                self.modemodule1[i]=int(setting[i*2+6])
                
            for i in range(MAXINPUTSMOKE): 
                self.namemodule2[i]=str(setting[i*2+25])
                self.modemodule2[i]=int(setting[i*2+26])
                
            print("Read Smoke Setting ok")
            
        else:       # Default
            self.maxinputmodule1=10         # dia chi module 1
            self.maxinputmodule2=11         # dia chi module 2
            self.timeout3=10     # 10 phut
            self.mesalarm="Alarm"
            self.mesnormal="Normal"
            for i in range(MAXINPUTSMOKE):
                self.namemodule1[i]=    "Smoke1:"+str(i+1)
                self.modemodule1[i]=    1      #0 Close alarm, 1 Open Alarm, 2 Not use
            for i in range(MAXINPUTSMOKE): 
                self.namemodule2[i]=    "Smoke2:"+str(i+1)
                self.modemodule2[i]=    1      #0 Close alarm, 1 Open Alarm, 2 Not use
    
            data=str(self.maxinputmodule1)+"\n"+str(self.maxinputmodule2)+"\n"+str(self.timeout3)+"\n"+str(self.mesalarm)+"\n"+str(self.mesnormal)+"\n"
            for i in range(MAXINPUTSMOKE):
                data=data+str(self.namemodule1[i])+"\n"
                data=data+str(self.modemodule1[i])+"\n"  
            for i in range(MAXINPUTSMOKE): 
                data=data+str(self.namemodule2[i])+"\n"
                data=data+str(self.modemodule2[i])+"\n"
               
            self.Save_setting(data)
            print("Default Smoke Setting")
        return (data)
    
    def Save_setting(self,data):
        f = codecs.open(self.file, "w",encoding='utf8')
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        #print (setting)
        if(len(setting)>=5+MAXINPUTSMOKE*4):
            self.maxinputmodule1=int(setting[0])
            self.maxinputmodule2=int(setting[1])
            self.timeout3=int(setting[2])
            self.mesalarm=str(setting[3])
            self.mesnormal=str(setting[4])
            for i in range(MAXINPUTSMOKE):    
                self.namemodule1[i]=str(setting[i*2+5])     
                self.modemodule1[i]=int(setting[i*2+6])
                
            for i in range(MAXINPUTSMOKE): 
                self.namemodule2[i]=str(setting[i*2+25])
                self.modemodule2[i]=int(setting[i*2+26])

            print("Saved Smoke Setting")
            
    # Canh bao khoi chay
    def EventAlarm(self):   
        global Beep,datetimealarms
        # Module 1
        if(SetModbus.statusconnect[4][0]>0):
            self.InputSmokeInt1=int(SetModbus.readvalue[4][0])
            binarydatainput=bin(int(SetModbus.readvalue[4][0]))[2:].zfill(10)[::-1]
            i=0
            if(IOsetting.alarm):
                while(i<self.maxinputmodule1):
                    if(binarydatainput[i]=='1' and self.modemodule1[i]==1 and self.FlagEventSmoke1[i]==0):
                        q.put(str(self.mesalarm)+": "+str(self.namemodule1[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke1[i]=1
                        SetModbus.statusconnect[4][0]=2
                        IOsetting.tsiren3buff=self.timeout3
                        print("Alarm Smoke: ",SetModbus.readvalue[4][0],i,len(binarydatainput),binarydatainput)
                        
                    elif(binarydatainput[i]=='0' and self.modemodule1[i]==1 and self.FlagEventSmoke1[i]>0):
                        q.put(str(self.mesnormal)+": "+str(self.namemodule1[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke1[i]=0
                        SetModbus.statusconnect[4][0]=1
                        print("Normal Smoke: ",SetModbus.readvalue[4][0],i)
                        
                    elif(binarydatainput[i]=='0' and self.modemodule1[i]==0 and self.FlagEventSmoke1[i]==0):
                        q.put(str(self.mesalarm)+": "+str(self.namemodule1[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke1[i]=1
                        SetModbus.statusconnect[4][0]=2
                        IOsetting.tsiren3buff=self.timeout3
                        print("Alarm Smoke:",SetModbus.readvalue[4][0],i,len(binarydatainput),binarydatainput)
                        
                    elif(binarydatainput[i]=='1' and self.modemodule1[i]==0 and self.FlagEventSmoke1[i]>0):
                        q.put(str(self.mesnormal)+": "+str(self.namemodule1[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke1[i]=0
                        SetModbus.statusconnect[4][0]=1
                        print("Normal Smoke: ",int(SetModbus.readvalue[4][0]),i)
                    i=i+1
        elif(SetModbus.statusconnect[4][0]==0):
            self.reportmodule="Not connect 1"
            
        # Module 2
        if(SetModbus.statusconnect[4][1]>0):
            self.InputSmokeInt2=int(SetModbus.readvalue[4][1])
            binarydatainput=bin(int(SetModbus.readvalue[4][1]))[2:].zfill(10)[::-1]
            i=0
            if(IOsetting.alarm):
                while(i<self.maxinputmodule2):
                    if(binarydatainput[i]=='1' and self.modemodule2[i]==1 and self.FlagEventSmoke2[i]==0):
                        q.put(str(self.mesalarm)+": "+str(self.namemodule2[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke2[i]=1
                        SetModbus.statusconnect[4][1]=2
                        IOsetting.tsiren3buff=self.timeout3
                        print("Alarm Smoke: ",SetModbus.readvalue[4][1],i,len(binarydatainput),binarydatainput)
                        
                    elif(binarydatainput[i]=='0' and self.modemodule2[i]==1 and self.FlagEventSmoke2[i]>0):
                        q.put(str(self.mesnormal)+": "+str(self.namemodule2[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke2[i]=0
                        SetModbus.statusconnect[4][1]=1
                        print("Normal Smoke: ",SetModbus.readvalue[4][1],i)
                        
                    elif(binarydatainput[i]=='0' and self.modemodule2[i]==0 and self.FlagEventSmoke2[i]==0):
                        q.put(str(self.mesalarm)+": "+str(self.namemodule2[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke2[i]=1
                        SetModbus.statusconnect[4][1]=2
                        IOsetting.tsiren3buff=self.timeout3
                        print("Alarm Smoke: ",SetModbus.readvalue[4][1],i,len(binarydatainput),binarydatainput)
                        
                    elif(binarydatainput[i]=='1' and self.modemodule2[i]==0 and self.FlagEventSmoke2[i]>0):
                        q.put(str(self.mesnormal)+": "+str(self.namemodule2[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventSmoke2[i]=0
                        SetModbus.statusconnect[4][1]=1
                        print("Normal Smoke: ",int(SetModbus.readvalue[4][1]),i)
                        
                    i=i+1
        elif(SetModbus.statusconnect[4][1]==0):
            self.reportmodule="Not connect 2"
            
         
# -----Smoke Setting----
SmokeSetting=smokesetting()
SmokeSetting.Load_setting()
# Phan web truy cap
@webiopi.macro
def load_smokesetting():
    data=SmokeSetting.Load_setting()
    return (data)

@webiopi.macro
def save_smokesetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    SmokeSetting.Save_setting(read)
    return (read)

# Phan giam sat trang thai dau bao khoi
# connect1,inputsmoke1, connect2, inputsmoke2
# Smoke, Page=4, STT: 0,1
@webiopi.macro
def load_smokestatus():
    data=""
    data=data+str(SetModbus.statusconnect[4][0])+','
    data=data+str(SetModbus.readvalue[4][0])+','
    data=data+str(SetModbus.statusconnect[4][1])+','
    data=data+str(SetModbus.readvalue[4][1])+','
    return (data)

# Mes0,Mode0,Mes1,Mode1....
@webiopi.macro
def UpdateModuleSmoke():
    data=""
    for i in range(MAXINPUTSMOKE):
        data=data+str(SmokeSetting.namemodule1[i])+','
        data=data+str(SmokeSetting.modemodule1[i])+','

    for i in range(MAXINPUTSMOKE):
        data=data+str(SmokeSetting.namemodule2[i])+','
        data=data+str(SmokeSetting.modemodule2[i])+','
    return (data)

#----------------------GENERATOR MONITOR-------------------------
# Sua moi danh cho BTS Elcom
# 20/09/16
class generatorsetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/generatorsetting.txt"

        self.InputGenneratorInt=0
        
        self.close1=["1 Low Oil","1 Low  Fuel","1 High Water Temp","1 Low Battery Volt","1 Gennerator On"]
        self.open1=["1 Normal Oil","1 Full  Fuel","1 Normal Water Temp","1 Normal Battery Volt","1 Gennerator Off"]
        self.close2=["2 Low Oil","2 Low  Fuel","2 High Water Temp","2 Low Battery Volt","2 Gennerator On"]
        self.open2=["2 Normal Oil","2 Full  Fuel","2 Normal Water Temp","2 Normal Battery Volt","2 Gennerator Off"]
        

    def Load_setting(self):
        f = codecs.open(self.file, "r+",encoding='utf8')
        data=f.read()
        f.close()                   # Close opend file
        strdata=str(data)
        setting=strdata.split('\n')
        
        if(len(setting)>=MAXINPUTGEN*4):                       # 2 gia tri dau va 5 gia tri lap lai  
            for i in range(MAXINPUTGEN): 
                self.close1[i]= str(setting[i*2])
                self.open1[i]=  str(setting[i*2+1])
            for i in range(MAXINPUTGEN):
                self.close2[i]= str(setting[i*2+10])
                self.open2[i]=  str(setting[i*2+11])
            print("Read Generator Setting ok")
            
        else:       # Default
            self.close1=["1 Low Oil","1 Low  Fuel","1 High Water Temp","1 Low Battery Volt","1 Gennerator On"]
            self.open1=["1 Normal Oil","1 Full  Fuel","1 Normal Water Temp","1 Normal Battery Volt","1 Gennerator Off"]
            self.close2=["2 Low Oil","2 Low  Fuel","2 High Water Temp","2 Low Battery Volt","2 Gennerator On"]
            self.open2=["2 Normal Oil","2 Full  Fuel","2 Normal Water Temp","2 Normal Battery Volt","2 Gennerator Off"]
            for i in range(MAXINPUTGEN):
                data=data+str(self.close1[i])+"\n"
                data=data+str(self.open1[i])+"\n"
            for i in range(MAXINPUTGEN):
                data=data+str(self.close2[i])+"\n"
                data=data+str(self.open2[i])+"\n"  
               
            self.Save_setting(data)
            print("Default Generator Setting")
        return (data)
    
    def Save_setting(self,data):
        f = codecs.open(self.file, "w",encoding='utf8')
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        #print (setting)
        if(len(setting)>=MAXINPUTGEN*4):                       # 2 gia tri dau va 5 gia tri lap lai  
            for i in range(MAXINPUTGEN): 
                self.close1[i]= str(setting[i*2])
                self.open1[i]=  str(setting[i*2+1])
            for i in range(MAXINPUTGEN):
                self.close2[i]= str(setting[i*2+10])
                self.open2[i]=  str(setting[i*2+11])

        print("Saved Generator Setting")
        
    # Canh bao loi may phat
    def EventGenerator(self):   
        global Beep,datetimealarms
        self.InputGenneratorInt=0
        # Module 1
        if(SetModbus.statusconnect[5][0]>0):
            self.InputGenneratorInt=int(SetModbus.statusconnect[5][0])
            binarydatainput=bin(int(SetModbus.statusconnect[5][0]))[2:].zfill(5)[::-1]
            i=0
            if(IOsetting.alarm):
                while(i<MAXINPUTGEN):
                    if(binarydatainput[i]=='1' and self.FlagEventGen1[i]==0):
                        q.put(str(self.close1[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventGen1[i]=1
                        SetModbus.statusconnect[5][0]=3
                        print("Generator1: ",SetModbus.readvalue[5][0],i,len(binarydatainput),binarydatainput)
                        
                    elif(binarydatainput[i]=='0' and  self.FlagEventGen1[i]>0):
                        q.put(str(self.open1[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventGen1[i]=0
                        SetModbus.statusconnect[5][0]=1
                        print("Generator1: ",SetModbus.readvalue[5][0],i)   
                    i=i+1
                
        # Module 2
        if(SetModbus.statusconnect[5][1]>0):
            self.InputGenneratorInt=int(SetModbus.statusconnect[5][0])|int(SetModbus.statusconnect[5][1])<<5
            binarydatainput=bin(int(SetModbus.statusconnect[5][1]))[2:].zfill(5)[::-1]
            i=0
            if(IOsetting.alarm):
                while(i<MAXINPUTGEN):
                    if(binarydatainput[i]=='1' and self.FlagEventGen2[i]==0):
                        q.put(str(self.close2[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventGen2[i]=1
                        SetModbus.statusconnect[5][1]=3
                        print("Generator2: ",SetModbus.readvalue[5][1],i,len(binarydatainput),binarydatainput)
                        
                    elif(binarydatainput[i]=='0' and  self.FlagEventGen2[i]>0):
                        q.put(str(self.open2[i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventGen2[i]=0
                        SetModbus.statusconnect[5][1]=1
                        print("Generator2: ",SetModbus.readvalue[5][1],i)   
                    i=i+1

        
# -----Generator Setting----
GeneratorSetting=generatorsetting()
GeneratorSetting.Load_setting()
# Phan web truy cap
@webiopi.macro
def load_generatorsetting():
    data=GeneratorSetting.Load_setting()
    return (data)

@webiopi.macro
def save_generatorsetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    GeneratorSetting.Save_setting(read)
    return (read)

@webiopi.macro
def UpdateModuleGenerator():
    data=""
    for i in range(MAXINPUTGEN):
        data=data+str(GeneratorSetting.close1[i])+','
        data=data+str(GeneratorSetting.open1[i])+','
    for i in range(MAXINPUTGEN):
        data=data+str(GeneratorSetting.close2[i])+','
        data=data+str(GeneratorSetting.open2[i])+','
    return (data)

@webiopi.macro
def load_generatorstatus():
    data=""
    data=data+str(SetModbus.statusconnect[5][0])+','
    data=data+str(SetModbus.readvalue[5][0])+','
    data=data+str(SetModbus.statusconnect[5][1])+','
    data=data+str(SetModbus.readvalue[5][1])+','
    return (data)

#----------------AIR CONDITION-------------------------------
# Sua moi danh cho BTS Elcom
# 19/09/16
class airsetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/airsetting.txt"
        self.OutputAirInt=0
        self.ModeOutputAirInt=0
        self.OutputAir=[0,0,0,0,0,0,0,0,0,0]    # trang thai 0=off va 1=on
        self.ChangeOutputAir=[0,0,0,0,0,0,0,0,0,0]    # trang thai 0=not va 1=change
        self.ConnectAir=[0,0,0,0,0,0,0,0,0,0]    # trang thai 0=not va 1=ok
        
        self.timerefresh=10     # 10 phut
        self.maxmoduleair=10    # 10 module
        
        self.namemoduleair=[]
        self.addmoduleair=[]    # dia chi module ECA-TH485IR
        self.modemoduleair=[]
        self.lowtemp=[]
        self.hightemp=[]
        for i in range(MAXMODULEIR):
            self.namemoduleair.append("Dieu Hoa "+str(i+1))
            self.addmoduleair.append(i+1)   
            self.modemoduleair.append(0)    #0 Auto, 1 Manual
            self.lowtemp.append(22)         # 22oC
            self.hightemp.append(26)        # 26oC

    def Load_setting(self):
        f = codecs.open(self.file, "r+",encoding='utf8')
        data=f.read()
        f.close()                   # Close opend file
        strdata=str(data)
        setting=strdata.split('\n')
        
        if(len(setting)>=2+MAXMODULEIR*5):                       # 2 gia tri dau va 5 gia tri lap lai  
            self.timerefresh=int(setting[0])
            self.maxmoduleair=int(setting[1])
            for i in range(MAXMODULEIR): 
                self.namemoduleair[i]=str(setting[i*5+2])
                self.addmoduleair[i]=int(setting[i*5+3])
                self.modemoduleair[i]=int(setting[i*5+4])
                self.lowtemp[i]=int(setting[i*5+5])
                self.hightemp[i]=int(setting[i*5+6])
            print("Read Air Setting ok")
            
        else:       # Default
            self.timerefresh=10     # 10 phut
            self.maxmoduleair=10    # 10 module
            for i in range(MAXMODULEIR):
                self.namemoduleair.append("Dieu Hoa "+str(i+1))
                self.addmoduleair.append(i+1)   
                self.modemoduleair.append(0)    #0 Auto, 1 Manual
                self.lowtemp.append(22)         # 22oC
                self.hightemp.append(26)        # 26oC
    
            data=str(self.timerefresh)+"\n"+str(self.maxmoduleair)+"\n"
            for i in range(MAXMODULEIR):
                data=data+str(self.namemoduleair[i])+"\n"
                data=data+str(self.addmoduleair[i])+"\n"  
                data=data+str(self.modemoduleair[i])+"\n"
                data=data+str(self.lowtemp[i])+"\n"
                data=data+str(self.hightemp[i])+"\n"
               
            self.Save_setting(data)
            print("Default Air Setting")
        return (data)
    
    def Save_setting(self,data):
        f = codecs.open(self.file, "w",encoding='utf8')
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        #print (setting)
        if(len(setting)>=2+MAXMODULEIR*5):                       # 2 gia tri dau va 5 gia tri lap lai  
            self.timerefresh=int(setting[0])
            self.maxmoduleair=int(setting[1])
            for i in range(MAXMODULEIR): 
                self.namemoduleair[i]=str(setting[i*5+2])
                self.addmoduleair[i]=int(setting[i*5+3])
                self.modemoduleair[i]=int(setting[i*5+4])
                self.lowtemp[i]=int(setting[i*5+5])
                self.hightemp[i]=int(setting[i*5+6])

            print("Saved Air Setting")

    def ControlAuto(self):
        global Beep
        for i in range(MAXMODULEIR):
            if(self.modemoduleair[i]==0):         #Auto
                if(SetModbus.readvalue[0][i]>=self.hightemp[i] and self.OutputAir[i]==0):
                    self.OutputAir[i]=1
                    self.ChangeOutputAir[i]=1
                    Beep=1
                elif(SetModbus.readvalue[0][i]<=self.lowtemp[i] and self.OutputAir[i]==1):
                    self.OutputAir[i]=0
                    self.ChangeOutputAir[i]=1
                    Beep=1
        # Chuyen doi bit thanh byte         
        self.OutputAirInt=0
        self.ModeOutputAirInt=0
        for i in range(self.maxmoduleair):
            maskoutair = self.OutputAir[i]<< i
            self.OutputAirInt=self.OutputAirInt|maskoutair
            maskmodeair = self.modemoduleair[i]<< i
            self.ModeOutputAirInt=self.ModeOutputAirInt|maskmodeair
          
# -----Air condition Setting----
AirSetting=airsetting()
AirSetting.Load_setting()
# Phan web truy cap
@webiopi.macro
def load_airsetting():
    data=AirSetting.Load_setting()
    return (data)

@webiopi.macro
def save_airsetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    AirSetting.Save_setting(read)
    return (read)

# Dieu khien loi ra dieu hoa bang tay.
# ECA-TH485IR
@webiopi.macro
def OutputAir(index):
    global Beep
    if (AirSetting.OutputAir[int(index)] == 0):
        AirSetting.OutputAir[int(index)]=1
        AirSetting.ChangeOutputAir[int(index)]=1
    else:
        AirSetting.OutputAir[int(index)]=0
        AirSetting.ChangeOutputAir[int(index)]=1
    Beep=1
    #numberchannel,namechannel0,out0,mode0,status0...
    data=str(AirSetting.maxmoduleair)+'\n';
    for i in range(MAXMODULEIR):
        data=data+str(AirSetting.namemoduleair[i])+"\n"+ str(AirSetting.OutputAir[i])+"\n"+str(AirSetting.modemoduleair[i])+"\n"
        data=data+str(SetModbus.readvalue[0][i])+"\n"+str(AirSetting.lowtemp[i])+"\n"+str(AirSetting.hightemp[i])+"\n"+str(AirSetting.ConnectAir[i])+"\n"         
    return(data)

# aircontrol.htm
@webiopi.macro
def UpdateModuleAir():
    data=str(AirSetting.maxmoduleair)+'\n';
    for i in range(MAXMODULEIR):
        data=data+str(AirSetting.namemoduleair[i])+"\n"+ str(AirSetting.OutputAir[i])+"\n"+str(AirSetting.modemoduleair[i])+"\n"
        data=data+str(SetModbus.readvalue[0][i])+"\n"+str(AirSetting.lowtemp[i])+"\n"+str(AirSetting.hightemp[i])+"\n"+str(AirSetting.ConnectAir[i])+"\n"         
    return(data)
    

#--------------------------Setting Modbus------------------------------------
# Sua moi danh cho BTS Elcom
# 17/09/16
class modbussettings(object):
    def __init__(self):
        self.file = "/home/pi/bts/Setting"
        self.indexweb=0         # gia tri duoc dieu khien bang web
        self.connect=[]         # So luong ket noi duoc cua 1 dia chi
        self.nameslave=["Nhiet do","Do am","Dien Xoay Chieu AC","Dien Acquy DC","Bao chay","May Phat","Dieu khien Dieu Hoa"]       # Ten cua dong ho do
        self.maxchannel=[20,20,16,18,2,2,10]       
        self.namechannel=[]
        self.addslave=[]        # Dia chi modbus
        self.functionchannel=[]
        self.startreg=[]
        self.numberreg=[]
        self.typereg=[]
        self.lowset=[]
        self.highset=[]
        self.unitreg=[]

        self.readvalue=[]       # Cac gia tri doc modbus
        self.counterror=[] 
        self.statusconnect=[] 
        for j in range(MAXPAGE):         # So luong trang toi da la 7
            self.connect.append(0)          #0
            #self.maxchannel.append([])
            self.namechannel.append([])
            self.addslave.append([])
            self.functionchannel.append([])
            self.startreg.append([])
            self.numberreg.append([])
            self.typereg.append([])
            self.lowset.append([])
            self.highset.append([])
            self.unitreg.append([])
            self.readvalue.append([])
            self.counterror.append([])
            self.statusconnect.append([]) 
            for i in range(MAXCHANNEL):     
                #self.maxchannel[j].append(MAXCHANNEL)
                self.namechannel[j].append(i)
                self.addslave[j].append(i+1)           # Dia chi modbus danh cho tung cam bien khac voi phien ban Power
                self.functionchannel[j].append(i)
                self.startreg[j].append(i)
                self.numberreg[j].append(i)
                self.typereg[j].append(i)
                self.lowset[j].append(i)
                self.highset[j].append(i)
                self.unitreg[j].append(i)
                self.readvalue[j].append(0)
                self.counterror[j].append(0)
                self.statusconnect[j].append(0) 
                
    def Load_setting(self,page):
        f = codecs.open(self.file+str(page)+".txt", "r+",encoding='utf8')
        data=f.read()
        f.close()                   # Close opend file
        strdata=str(data)
        setting=strdata.split('\n')
        #print(len(setting),"Read Setting:",setting)
        
        if(len(setting)>=4+MAXCHANNEL*9):                       # 4 gia tri dau va lap lai 9 gia tri cai dat tiep theo    
            self.nameslave[page]=str(setting[0])
            self.baud=int(setting[2])
            self.maxchannel[page]=int(setting[3])
            if(self.maxchannel[page]>MAXCHANNEL):
                self.maxchannel[page]=MAXCHANNEL
           
            for i in range(MAXCHANNEL):    
                self.namechannel[page][i]=setting[i*9+4]      # Ten kenh du lieu
                self.addslave[page][i]=  int(setting[i*9+5])  # Dia chi modbus danh cho tung cam bien khac voi phien ban Power
                self.functionchannel[page][i]=int(setting[i*9+6])
                self.startreg[page][i]=int(setting[i*9+7])
                self.numberreg[page][i]=int(setting[i*9+8])
                self.typereg[page][i]=int(setting[i*9+9])        
                self.lowset[page][i]=int(setting[i*9+10])       
                self.highset[page][i]=int(setting[i*9+11])         
                self.unitreg[page][i]=setting[i*9+12]
                
            print("Read Setting ok")
            
        else:       # Default
            self.nameslave=["Nhiet do","Do am","Dien Xoay Chieu AC","Dien Acquy DC","Bao chay","May Phat","Dieu khien Dieu Hoa"]       # Ten cua dong ho do
            self.maxchannel=[20,20,16,18,2,2,10] 
            self.baud=9600
            #self.maxchannel[page]=MAXCHANNEL
            for i in range(MAXCHANNEL):   
                self.namechannel[page][i]="Channel:"+str(page*9+i+1)    # Ten kenh du lieu
                self.addslave[page][i]=  int(page*9+i+1)                     # Dia chi modbus danh cho tung cam bien khac voi phien ban Power
                self.functionchannel[page][i]=3
                self.startreg[page][i]=i
                self.numberreg[page][i]=1
                self.typereg[page][i]=1                              #16bit
                self.lowset[page][i]=0       
                self.highset[page][i]=100         
                self.unitreg[page][i]="oC"
    
            data=str(self.nameslave[page])+"\n"+str(page)+"\n"+str(self.baud)+"\n"+str(self.maxchannel[page])+"\n"
            for i in range(MAXCHANNEL):    #3+MAXCHANNEL*8
                data=data+str(self.namechannel[page][i])+"\n"
                data=data+str(self.addslave[page][i])+"\n"
                data=data+str(self.functionchannel[page][i])+"\n"
                data=data+str(self.startreg[page][i])+"\n"
                data=data+str(self.numberreg[page][i])+"\n"
                data=data+str(self.typereg[page][i])+"\n"
                data=data+str(self.lowset[page][i])+"\n"
                data=data+str(self.highset[page][i])+"\n"
                data=data+str(self.unitreg[page][i])+"\n"
                
            self.Save_setting(data)
            print("Default Setting")
        #print (data)
        return (data)
    
    def Save_setting(self,data):
        setting=data.split('\n')
        page=int(setting[1])
        print("add:",page)
        self.nameslave[page]=str(setting[0])
        f = codecs.open(self.file+str(page)+".txt", "w",encoding='utf8')
        f.write(data)
        f.close()
        #print (setting)
        if(len(setting)>=4+MAXCHANNEL*9):                        # 4 gia tri dau va lap lai 9 gia tri cai dat tiep theo 
            self.baud=int(setting[2])
            self.maxchannel[page]=int(setting[3])
            for i in range(MAXCHANNEL):   
                self.namechannel[page][i]=setting[i*9+4]      # Ten kenh du lieu
                self.addslave[page][i]=  int(setting[i*9+5])  # Dia chi modbus danh cho tung cam bien khac voi phien ban Power
                self.functionchannel[page][i]=int(setting[i*9+6])
                self.startreg[page][i]=int(setting[i*9+7])
                self.numberreg[page][i]=int(setting[i*9+8])
                self.typereg[page][i]=int(setting[i*9+9])        
                self.lowset[page][i]=int(setting[i*9+10])       
                self.highset[page][i]=int(setting[i*9+11])         
                self.unitreg[page][i]=setting[i*9+12]
            print("Saved Setting")
            

#------------------ Cai dat Modbus---------------------------------
SetModbus=modbussettings()
for i in range(MAXPAGE):
    SetModbus.Load_setting(i)
# Phan web truy cap
@webiopi.macro
def load_modbussetting(page):
    data=SetModbus.Load_setting(int(page))
    return (data)

@webiopi.macro
def save_modbussetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    SetModbus.Save_setting(read)
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
    global pageindexsms
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
    
    Gsm.reportsms="Admin: "+str(sms.number)+"; "+str(sms.text)
    if(sms.text.find("Alarm off")!=-1):
        IOsetting.alarm=0
        textsms=Netsetting.hostname+'\nAlarm off'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
    elif(sms.text.find("Alarm on")!=-1):
        IOsetting.alarm=1
        textsms=Netsetting.hostname+'\nAlarm on'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
        
    elif(sms.text.find("Value?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[pageindexsms]):
            data=data+str(SetModbus.namechannel[pageindexsms][i])+":"+str(SetModbus.readvalue[pageindexsms][i])+" "+str(SetModbus.unitreg[pageindexsms][i])+"\n"
        print(data)
        pageindexsms=pageindexsms+1
        if(pageindexsms>3):
            pageindexsms=0
        textsms=Netsetting.hostname+'\nModbus Add '+str(pageindexsms)+":\n"+data
        
    elif(sms.text.find("Temp?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[0]):
            data=data+str(SetModbus.namechannel[0][i])+":"+str(SetModbus.readvalue[0][i])+" "+str(SetModbus.unitreg[0][i])+"\n"
        print(data)
        textsms=Netsetting.hostname+'\nTemp oC:\n'+data
        
    elif(sms.text.find("Humi?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[1]):
            data=data+str(SetModbus.namechannel[1][i])+":"+str(SetModbus.readvalue[1][i])+" "+str(SetModbus.unitreg[1][i])+"\n"
        print(data)
        textsms=Netsetting.hostname+'\nHumi %:\n'+data
        
    elif(sms.text.find("Vac?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[2]):
            data=data+str(SetModbus.namechannel[2][i])+":"+str(SetModbus.readvalue[2][i])+" "+str(SetModbus.unitreg[2][i])+"\n"
        print(data)
        textsms=Netsetting.hostname+'\nVac:\n'+data

    elif(sms.text.find("Vdc?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[3]):
            data=data+str(SetModbus.namechannel[3][i])+":"+str(SetModbus.readvalue[3][i])+" "+str(SetModbus.unitreg[3][i])+"\n"
        print(data)
        textsms=Netsetting.hostname+'\nVdc:\n'+data
        
    elif(sms.text.find("Test?")!=-1):
        data="Network:"+Gsm.network+",CSQ:"+str(Gsm.csq)+"\n"
        data=data+str(Gsm.reportsms)+"\n"
        data=data+str(Netsetting.reportserver)+"\n"+str(Netsetting.ip)+":8880\n"
        data=data+"Modbus conneted "+str(pageindexsms)+": "+str(SetModbus.connect[pageindexsms])+"/"+str(SetModbus.maxchannel[pageindexsms])
        textsms=Netsetting.hostname+'\n'+data+'\n'+version
        pageindexsms=pageindexsms+1
        if(pageindexsms>=MAXPAGE):
            pageindexsms=0
        
    elif(sms.text.find("Infor?")!=-1):
        if(IOsetting.alarm):
            data='ARMING\n'
        else:
            data='DISARM\n'
        data=data+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
        for j in range(MAXPAGE-3):
            if(SetModbus.connect[j]>0):
                data=data+str(SetModbus.namechannel[j][0])+":"+str(SetModbus.readvalue[j][0])+" "+str(SetModbus.unitreg[j][0])+"\n"
        textsms=Netsetting.hostname+'\n'+data
    else:
        textsms=Netsetting.hostname+'\n'+Gsm.textsmsrec+': Error SMS!\nInfor?\nValue?\nTemp?\nHumi?\nVac?\nVdc?\nTest?\nAlarm on/off'

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
    for i in range(6):   
        GPIO.setup(OUT1+i, GPIO.OUT) # sets i to output and 0V, off
        GPIO.setup(INP1+i, GPIO.IN) # sets i to output and 0V, off
        GPIO.output(OUT1+i,0)
    # tell the GPIO library to look out for an 
    # event on pin 23 and deal with it by calling 
    # the inputEventHandler function
    GPIO.add_event_detect(INP1, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP2, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP3, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP4, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP5, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    GPIO.add_event_detect(INP6, GPIO.BOTH, callback=inputEventHandler, bouncetime=1000)
    #GPIO.add_event_detect(INP7, GPIO.BOTH, callback=inputEventHandler, bouncetime=5000)
    #GPIO.add_event_detect(INP8, GPIO.BOTH, callback=inputEventHandler, bouncetime=5000)
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

    time.sleep(2)   
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
# Update 29/09/2016
def inputEventHandler(pin):
    global OUTGENERATOR,CHANGEOUTGENERATOR
    if(IOsetting.alarm==0):
        return
    if(pin>=INP1 and pin<=INP6):
        if(IOsetting.modeinput[pin-INP1]==0 and GPIO.input(pin)==0):
            q.put(str(pin-INP1+1)+": "+str(IOsetting.lowinput[pin-INP1]))
            if(IOsetting.sireninput[pin-INP1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("1:0 ",str(IOsetting.lowinput[pin-INP1]))
        elif(IOsetting.modeinput[pin-INP1]==1 and GPIO.input(INP1)==1):
            q.put(str(pin-INP1+1)+": "+str(IOsetting.highinput[pin-INP1]))
            if(IOsetting.sireninput[pin-INP1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
                print ("1:1 ",str(IOsetting.highinput[pin-INP1]))
        elif(IOsetting.modeinput[pin-INP1]==2):
            if(GPIO.input(INP1)==1):
                q.put(str(pin-INP1+1)+": "+str(IOsetting.highinput[pin-INP1]))
                print ("1:2 ",str(IOsetting.highinput[pin-INP1])+str(IOsetting.tsiren3))
            else:
                q.put(str(pin-INP1+1)+": "+str(IOsetting.lowinput[pin-INP1]))
                print ("1:2 ",str(IOsetting.lowinput[pin-INP1])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[pin-INP1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                IOsetting.tlamp5buff=IOsetting.tlamp5
   
#-------------------------------------------------------
# Update 29/09/16
#   self.OutputAirInt,self.ModeOutputAirInt  self.InputSmokeInt1=0
def messagetoserver(types,message):
    inputval=inputstatus|SmokeSetting.InputSmokeInt1<<6|SmokeSetting.InputSmokeInt2<<(SmokeSetting.maxinputmodule1+6)|\
             GeneratorSetting.InputGenneratorInt<<(SmokeSetting.maxinputmodule2+SmokeSetting.maxinputmodule1+6)
    data=""
    if(len(Netsetting.ipserver)):
        data=str(Netsetting.id)+"&"+str(Netsetting.hostname)+ "&"+types+"&"+message+"&"+str(inputval)+"&"+str(AirSetting.OutputAirInt)+"&"+str(AirSetting.ModeOutputAirInt)
        for pageindex in range(4):   
            for i in range(SetModbus.maxchannel[pageindex]):
                data=data+"&"+str(SetModbus.readvalue[pageindex][i])
                
        #print(data)
        try:
            client(Netsetting.ipserver, int(Netsetting.portserver), data)
        except:
            print ('Error client to server.')
            
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
  
    '''try:
        remote_ip = socket.gethostbyname(ip)
    except socket.gaierror:
        #could not resolve
        print ('Hostname could not be resolved. Exiting')
        sys.exit()'''
        
    sock.settimeout(5)    
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
    sock.settimeout(5)  
    try:
        dataclient = sock.recv(1024).strip()
    except socket.error as msg:
        Netsetting.reportserver='Failed to recv socket. Error code: '+str(msg)
        sock.close()
        return
    sock.settimeout(None)
    response = str(dataclient, encoding='utf8')
    sock.close()
    #print(response)
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
            #print(readreportserver)
            #update 29/09/16 BTS  
            if(len(dataread[4])>0):
                binaryoutputmode=bin(int(dataread[4]))[2:].zfill(10)[::-1]
                print(binaryoutputmode)
                i=0
                while(i<len(binaryoutputmode)):
                    if(binaryoutputmode[i]=='1' and i<MAXMODULEIR):
                        AirSetting.modemoduleair[i]=1       #che do bang tay
                    elif(binaryoutputmode[i]=='0' and  i<MAXMODULEIR):
                        AirSetting.modemoduleair[i]=0       #che do tu dong
                    i+=1
                Beep=1 
            #Data1=output, dữ liệu nhị phân 9 bit, bit thứ 9 điều khiển máy phát    
            if(len(dataread[3])>0):
                binaryoutput=bin(int(dataread[3]))[2:].zfill(10)[::-1] 
                print(binaryoutput)
                i=0
                while(i<len(binaryoutput)):
                    if(binaryoutput[i]=='1' and i<MAXMODULEIR):
                        AirSetting.OutputAir[i]=1
                        AirSetting.ChangeOutputAir[i]=1
                    elif(binaryoutput[i]=='0' and i<MAXMODULEIR):
                        AirSetting.OutputAir[i]=0
                        AirSetting.ChangeOutputAir[i]=1
                    i+=1
                Beep=1 
        else:
            readreportserver="Rec: "+response
            
    Netsetting.reportserver='Sent: '+str(convertSize(Netsetting.sizedatatoserver))+'. '+readreportserver
    '''if(readreportserver.find("Error")!=-1):
        messagetoserver("status","ERROR")
    else:
        messagetoserver("status","OK")'''
    #print(Netsetting.reportserver)
#-------------------------------------------------------
# loop function is kiem tra cac tram co ket noi hay khong 
def loop():
    # gives CPU some time before looping again 180 seconds
    global countsec,countmin,Beep, inputstatus, outputstatus,modeoutputstatus,lastsecond,lastminute,lasthour,datetimealarms,pageindex,pageindexsms,looprunning,indextask
    data=0
    indextask=0
    counttimefresh=0
    # Ghi du lieu History data
    now = datetime.datetime.now()
    if(now.year>2017 and now.month > 9):
        return
    looprunning=1
    indextask=0.1
    # ---Kiem tra theo giay---
    if(now.second!=lastsecond):
        if(lastsecond>now.second):
            #print('Countsec:',countsec,lastsecond,now.second)
            countsec=countsec+lastsecond-now.second
        else:
            #print('Countsec:',countsec,lastsecond,now.second)
            countsec=countsec+now.second-lastsecond
        lastsecond=now.second
        if(countsec>50):    #20 giay kiem tra tin nhan toi 1 lan
            countsec=0
            # Kiem tra tin nhan toi, dung Huawei E303H
            if(sms.connected==True):
                try:
                    sms.processStoredSms(False)
                    GPIO.output(LEDCONNECT,False)
                except:
                    GPIO.output(LEDCONNECT,True)
            indextask=0.21
            # Gui du lieu toi server cu 30 giay 1 lan
            if(IOsetting.alarm):
                data="ARMING"
            else:
                data="DISARM"
            try:
                messagetoserver("status",data)
            except Exception as e:
                Netsetting.reportserver="Error send to server:"+str(e)
                
        # Huy bao dong ra loa
        if(IOsetting.tsiren3buff>0):
            IOsetting.tsiren3buff=IOsetting.tsiren3buff-1
            print("Tsiren:",IOsetting.tsiren3buff)
        if(IOsetting.tsiren3buff==0 and IOsetting.modeoutput[2]==0):
            GPIO.output(OUT3,False)
            
    # ----Chay 1 phut----
    if(now.minute!=lastminute):
        lastminute=now.minute
        countmin=countmin+1
        counttimefresh=counttimefresh+1
        print("Den phut:",countmin)
        
        # Dieu khien dieu hoa o che do tu dong
        # 27/09/16
        AirSetting.ControlAuto()
        if(AirSetting.timerefresh>=counttimefresh):
            counttimefresh=0
            for i in range(MAXMODULEIR):
                AirSetting.ChangeOutputAir[i]=1

        # Hen gio nhan tin-------------------------------------
        indextask=0.2
        if(lastminute==0 and IOsetting.tinfor==now.hour):
            Beep=1
            Netsetting.bodysms=""
            if(IOsetting.alarm):
                Netsetting.bodysms=Netsetting.hostname+'\nARMING\n'
            else:
                Netsetting.bodysms=Netsetting.hostname+'\nDISARM\n'
            Netsetting.bodysms=Netsetting.bodysms+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
            for j in range(MAXPAGE-3):
                if(SetModbus.connect[j]>0):
                    Netsetting.bodysms=Netsetting.bodysms+str(SetModbus.namechannel[j][0])+":"+str(SetModbus.readvalue[j][0])+" "+str(SetModbus.unitreg[j][0])+"\n"
            Netsetting.bodysms=Netsetting.bodysms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
            
            '''Netsetting.bodysms=Netsetting.bodysms+str(SetModbus.namechannel[pageindexsms][0])+":"+str(SetModbus.readvalue[pageindexsms][0])+" "+str(SetModbus.unitreg[pageindexsms][0])+"\n"+\
                str(SetModbus.namechannel[pageindexsms][1])+":"+str(SetModbus.readvalue[pageindexsms][1])+" "+str(SetModbus.unitreg[pageindexsms][1])+"\n"+\
                str(SetModbus.namechannel[pageindexsms][2])+":"+str(SetModbus.readvalue[pageindexsms][2])+" "+str(SetModbus.unitreg[pageindexsms][2])+"\n"+\
                str(SetModbus.namechannel[pageindexsms][3])+":"+str(SetModbus.readvalue[pageindexsms][3])+" "+str(SetModbus.unitreg[pageindexsms][3])+"\n"
            Netsetting.bodysms=Netsetting.bodysms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
            pageindexsms=pageindexsms+1
            if(pageindexsms>=MAXPAGE):
                pageindexsms=0
            '''              
            
        # Kiem tra xong di dong
        indextask=1
        if(countmin >= IOsetting.tupload):
            countmin=0
            # Kiem tra song di dong
            if(sms.connected==True):
                try:
                    Gsm.csq=sms.signalStrength()
                    if(Gsm.network==None):
                        Gsm.network=sms.GetNetwork()
                except Exception as e:
                    print("CSQ error:",e)
                    Gsm.csq=0
                    Reboot()

    #Phan canh bao qua mail va sms
    indextask=2.3  
    if(data==0 and IOsetting.alarm and not q.empty()):
        Beep=3
        alarms=""
        alarmone=""
        while(not q.empty()):
            alarmone=q.get()
            try:
                insert_alarm_tablet(alarmone)
                if(Netsetting.reportserver.find("Error database alarm:")!=-1):
                    Netsetting.reportserver="Written database alarm"
            except Exception as e:
                Netsetting.reportserver="Error database alarm:"+str(e)
                
            alarms=alarms+"\n"+alarmone
        # Gui canh bao ve server
        messagetoserver("alarm",alarms)
        Netsetting.bodysms=Netsetting.hostname+alarms+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880"

    indextask=3 
    #-------------------
    if(now.hour!=lasthour):
        lasthour=now.hour
        Beep=1
    #-------------------
    # Time | Channel | Value | Status | Input | Output
    # Trang thai cac IO
    inputstatus=0
    outputstatus=0
    modeoutputstatus=0
    for i in range(6):
        maskout = GPIO.input(OUT1+i)<< i
        outputstatus=outputstatus|maskout
        maskmode = IOsetting.modeoutput[i]<< i
        modeoutputstatus=modeoutputstatus|maskmode
        maskin  = GPIO.input(INP1+i)<< i
        inputstatus=inputstatus|maskin
    
    #for pageindex in range(MAXPAGE):
    con=0    
    for i in range(SetModbus.maxchannel[pageindex]):
        try:
            usbrtu.readmodbus(pageindex,i,SetModbus.addslave[pageindex][i],SetModbus.functionchannel[pageindex][i],SetModbus.startreg[pageindex][i],SetModbus.numberreg[pageindex][i],SetModbus.typereg[pageindex][i]) 
            if(SetModbus.statusconnect[pageindex][i]>0):
                con=con+1
        except:
            webiopi.debug("Error loop: "+str(pageindex+1)+','+str(i)+','+str(sys.exc_info()))
            pass

    if(IOsetting.alarm and SetModbus.connect[pageindex]>0 and con==0):
        Netsetting.bodysms=Netsetting.hostname+"\nNot connect Modbus Address:"+str(pageindex+1)+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880"
    SetModbus.connect[pageindex]=con
    pageindex=pageindex+1
    if(pageindex>=MAXPAGE):
        pageindex=0

    # Nhan tin va gui mail
    indextask=3.0
    if(len(Netsetting.bodysms)):
        try:
            MAIL(Netsetting.bodysms)
            Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
        except Exception as e:
            Netsetting.reportserver="Error Mail:" +str(e)
        indextask=3.1
        for i in range(len(Netsetting.tel)):    #5 so dien thoai
            if(len(Netsetting.tel[i])>=4):
                if(sms.connected==True and IOsetting.sms):
                    try:
                        if(len(Netsetting.bodysms)>159):
                            numbersms=int(len(Netsetting.bodysms)/159)
                            for j in range(numbersms):
                                sms.SendSMS(Netsetting.tel[i],Netsetting.bodysms[j*159:j*159+159])
                        else:
                            sms.SendSMS(Netsetting.tel[i],Netsetting.bodysms[:159])
                        Gsm.reportsms="Sent SMS"
                        print("Sent SMS")
                    except Exception as e:
                        Gsm.reportsms="Error SMS:"+str(e)
                        print("Error SMS:",e)
                    indextask=3.2
        Netsetting.bodysms=""
                    
    # Su kien canh bao nhiet do,do am
    indextask=4.0
    if(IOsetting.alarm):
        alarmth.Eventtemphumi()
        
    # Bao chay bao khoi
    indextask=4.1    
    if(pageindex==4):
        SmokeSetting.EventAlarm()
        
    # Bao may phat dien
    indextask=4.2    
    if(pageindex==5):
        GeneratorSetting.EventGenerator()

    indextask=5
    GPIO.output(LEDCONNECT,not GPIO.input(LEDCONNECT))
    looprunning=1
#---------------------------------------
class AlarmEvents(object):
    def __init__(self):
        self.FlagEventTH=[]
        for j in range(MAXPAGE):         #4
            self.FlagEventTH.append([])
            for i in range(SetModbus.maxchannel[j]):
                self.FlagEventTH[j].append(0)     #0 Normal, 1 Alarm
                
        GPIO.setup(OUT3, GPIO.OUT)    # Siren
        
    def init(self):                         # Setup output
        GPIO.output(OUT3,False)                 # Siren off
    def finish(self):
        GPIO.output(OUT3,False)
        
    def Eventtemphumi(self):
        global Beep,datetimealarms,indextask
        for j in range(MAXPAGE-3):
            if(SetModbus.connect[j]>0):
                for i in range(SetModbus.maxchannel[j]):
                    #print(i,"> gia tri kenh:",SetModbus.highset,SetModbus.lowset,self.FlagEventTH)
                    if(SetModbus.readvalue[j][i]>int(SetModbus.highset[j][i]) and self.FlagEventTH[j][i]!=1):
                        indextask=4.1
                        q.put(str(IOsetting.meshigh)+"\n"+str(SetModbus.namechannel[j][i])+": "+str(SetModbus.readvalue[j][i])+">"+str(SetModbus.highset[j][i])+" "+str(SetModbus.unitreg[j][i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventTH[j][i]=1
                        SetModbus.statusconnect[j][i]=3
                        IOsetting.tsiren3buff=IOsetting.tsiren3
                        indextask=4.2
                    elif(SetModbus.readvalue[j][i]<int(SetModbus.lowset[j][i]) and self.FlagEventTH[j][i]!=2):
                        indextask=4.3
                        q.put(str(IOsetting.meslow)+"\n"+str(SetModbus.namechannel[j][i])+": "+str(SetModbus.readvalue[j][i])+"<"+str(SetModbus.lowset[j][i])+" "+str(SetModbus.unitreg[j][i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventTH[j][i]=2
                        SetModbus.statusconnect[j][i]=2
                        IOsetting.tsiren3buff=IOsetting.tsiren3
                        indextask=4.4
                    elif(SetModbus.readvalue[j][i]>int(SetModbus.lowset[j][i]) and SetModbus.readvalue[j][i]<int(SetModbus.highset[j][i]) and self.FlagEventTH[j][i]>0):
                        indextask=4.5
                        q.put(str(SetModbus.namechannel[j][i])+": "+str(SetModbus.readvalue[j][i])+" "+str(SetModbus.unitreg[j][i]))
                        datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                        self.FlagEventTH[j][i]=0
                        SetModbus.statusconnect[j][i]=1
                        indextask=4.6
# Khai bao
alarmth=AlarmEvents()
#---------------------------------------
# SetModbus.readvalue[0] nhiet do dieu khien dieu hoa Out12
# SetModbus.readvalue[1] do am de dieu khien hut am Out4
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
        if(SetModbus.readvalue[0]>IOsetting.temphighon12 and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
            GPIO.output(OUT1,True)
            GPIO.output(OUT2,True)
            self.CHANGEOUT1=1
            self.CHANGEOUT2=1
        elif((SetModbus.readvalue[0]>0 and SetModbus.readvalue[0]<IOsetting.templowoff12 or self.Flagoff12==1) and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
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
        if(SetModbus.readvalue[1]>IOsetting.humihighon4 and IOsetting.modeoutput[3]==0):
            GPIO.output(OUT4,True)
        elif(IOsetting.modeoutput[3]==0):
            GPIO.output(OUT4,False)
            
# Setup Output
#air=Aircontrol()
#---------------------------------------     
class ModbusRTU(object):
    def __init__(self):
        self.reportmodbus="Start Modbus"  
        '''try:
            self.open()
        except Exception as e:
            print("Error USB:",e)
            sys.exit(1)'''
    def open(self):
        try:
            self.instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1) # port name, slave address (in decimal)
        except Exception as e:
            self.reportmodbus="Error RS485:"+str(e)
            pass
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
           
    def readmodbus(self,pageindex,indexaddress,address,functionchannel,startreg,numberreg,typereg):
        global Beep,CHANGEOUTGENERATOR
        self.instrument.address=address                         # this is the slave address number
        print("Read modbus:",address,startreg,numberreg,functionchannel)
        self.data=0
        try:
        
            # DIEU KHIEN CAC LOI RA QUA RS485
            if(functionchannel==5 and AirSetting.ChangeOutputAir[indexaddress]==1):
                AirSetting.ChangeOutputAir[indexaddress]=0
                if(AirSetting.OutputAir[indexaddress]>0):
                    self.instrument.write_bit(startreg,1,5)
                    print("write_bit=1")
                else:
                    self.instrument.write_bit(startreg,0,5)
                    print("write_bit=0")

                
            #The slave register can hold integer values in the range 0 to 65535 (“Unsigned INT16”).
            elif(typereg==1):                          
                self.data = self.instrument.read_register(startreg, numberreg,functionchannel)
                
            #read_long(registeraddress, functioncode=3, signed=False)
            elif(typereg==2):                         
                self.data = self.instrument.read_long(startreg,functionchannel, False)
                
            #read_float(registeraddress, functioncode=3, numberOfRegisters=2)
            elif(typereg==3):                
                self.data = round(self.instrument.read_float(startreg,functionchannel,numberreg),1)
                
            #read_string(registeraddress, numberOfRegisters=16, functioncode=3)
            elif(typereg==4):                
                self.data = self.instrument.read_string(startreg,numberreg,functionchannel)
                
                
            print("OK read:",self.data)
            self.reportmodbus="Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
            self.instrument.serial.timeout  = 0.1   # seconds
            #print("Doc du lieu:",self.readdata)
            SetModbus.readvalue[pageindex][indexaddress]=self.data
            SetModbus.counterror[pageindex][indexaddress]=0
            if(SetModbus.statusconnect[pageindex][indexaddress]==0):
                SetModbus.statusconnect[pageindex][indexaddress]=1
            return 1
        
        except Exception as e:
            #GPIO.output(LEDERROR,True)
            #self.open()
            self.reportmodbus="Error Modbus:"+str(address)+"+"+str(startreg)+"="+str(self.data)+":"+str(SetModbus.counterror[pageindex][indexaddress]) +str(e)
            SetModbus.counterror[pageindex][indexaddress]=SetModbus.counterror[pageindex][indexaddress]+1
            print("Error read:",address,startreg,indexaddress,SetModbus.counterror[pageindex][indexaddress],e)
            if(SetModbus.counterror[pageindex][indexaddress]>=20):
                SetModbus.counterror[pageindex][indexaddress]=0
                SetModbus.readvalue[pageindex][indexaddress]=0
                SetModbus.statusconnect[pageindex][indexaddress]=0
            return 0
        
# Setup USB RS485
usbrtu=ModbusRTU()

#------------------------------------------
def HNI420command(read):
    global outputstatus,pageindexsms
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
        data=""
        for i in range(SetModbus.maxchannel[0]):
            data=data+str(SetModbus.namechannel[0][i])+":"+str(SetModbus.readvalue[0][i])+" "+str(SetModbus.unitreg[0][i])+"\n"
        print(data)
        serial.writeString(data)       # write a string
        
    elif(read.find("Humi?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[1]):
            data=data+str(SetModbus.namechannel[1][i])+":"+str(SetModbus.readvalue[1][i])+" "+str(SetModbus.unitreg[1][i])+"\n"
        print(data)
        serial.writeString(data)       # write a string
        
    elif(read.find("Vac?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[2]):
            data=data+str(SetModbus.namechannel[2][i])+":"+str(SetModbus.readvalue[2][i])+" "+str(SetModbus.unitreg[2][i])+"\n"
        print(data)
        serial.writeString(data)       # write a string  

    elif(read.find("Vdc?")!=-1):
        data=""
        for i in range(SetModbus.maxchannel[3]):
            data=data+str(SetModbus.namechannel[3][i])+":"+str(SetModbus.readvalue[3][i])+" "+str(SetModbus.unitreg[3][i])+"\n"
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
    global Alarmspk,Beep,looprunning,indextask
    global countminsql,lastminutesql
    lastminute=0
    count=0
    while True:
        now = datetime.datetime.now()
        if(looprunning==1 and now.minute==0): #60 phut kiem tra 1 lan
            looprunning=0
        elif(looprunning==0 and now.minute>10):
            looprunning=1
            webiopi.debug("Error SysNet: "+str(indextask))
            Netsetting.bodysms=Netsetting.hostname+'\nError SysNet: '+str(indextask) + '\n'+usbrtu.reportmodbus+ '\n'+Netsetting.reportserver+'\n'
            Netsetting.bodysms=Netsetting.bodysms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880"
            try:
                MAIL(Netsetting.bodysms)
                #Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
            except:
                Netsetting.reportserver="Error Mail"   #Khac phuc loi khi nhan tin het tien.
            if(sms.connected==True):
                try:
                    sms.SendSMS(Netsetting.tel[0],Netsetting.bodysms[:159])
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
        if (serial.available()):
            try:
                data = serial.readString()        # read available data as string
                IOsetting.reporthmi=data
                HNI420command(data)
            except:
                IOsetting.reporthmi="Error UART!"
                webiopi.debug("Error UART!")
                pass
            
        # Thoi gian ghi du lieu SQL
        if(now.minute!=lastminutesql):
            lastminutesql=now.minute
            countminsql=countminsql+1
        if(countminsql >= IOsetting.tupload):
            countminsql=0
            # Luu tru du lieu SQL, kenh: 1 nhiet do, 2 do am, 3 dien AC, 4 dien DC
            # update 07/04/16
            for j in range(MAXPAGE-3):
                if(SetModbus.connect[j]>0):
                    for i in range(SetModbus.maxchannel[j]):
                        print("Write data to sql:",i)
                        try:
                            insert_history_data(j,i,SetModbus.readvalue[j][i],SetModbus.statusconnect[j][i])
                            if(Netsetting.reportserver.find("Error database:")!=-1):
                                Netsetting.reportserver="Written database:"+str(j+1)+": "+ str(i+1)
                        except Exception as e:
                            Netsetting.reportserver="Error database:"+str(e)
            
#---Thu nghiem voi chuc nang MAIL----
def MAIL(mailtext):   
    # Construct email
    msg = MIMEText(mailtext.encode('utf-8'), _charset='utf-8')
    
    msg['To'] = Netsetting.mailto0
    recips = Netsetting.mailto0
    if(len(Netsetting.mailto1)>0):
        msg["Cc"] = Netsetting.mailto1
        recips  = [Netsetting.mailto0,Netsetting.mailto1]
    if(len(Netsetting.mailto2)>0):
        msg['Bcc'] = Netsetting.mailto2
        recips  = [Netsetting.mailto0,Netsetting.mailto2]
    if(len(Netsetting.mailto0)>0 and len(Netsetting.mailto1)>0 and len(Netsetting.mailto2)>0):
        recips  = [Netsetting.mailto0,Netsetting.mailto1,Netsetting.mailto2]
         
    msg['From'] = Netsetting.mailfrom
    msg['Subject'] = 'Email alarm from ECA-GPIs6.6CE for BTS device'
    # Send the message via an SMTP server
    s = smtplib.SMTP(Netsetting.mailserver,int(Netsetting.mailport))
    '''s.ehlo()
    s.starttls()
    s.ehlo'''
    s.login(Netsetting.mailfrom,Netsetting.mailpass)
    s.sendmail(Netsetting.mailfrom, recips, msg.as_string())
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
