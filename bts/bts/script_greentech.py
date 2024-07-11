# Imports
# Import smtplib to provide email functions
import smtplib
# Import the email modules
from email.mime.text import MIMEText
import math
import webiopi
from webiopi.devices.serial import Serial
import glob
import os
import fcntl
import struct
import socket
import codecs
import re
from subprocess import call
from subprocess import *
from ftplib import FTP
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
import urllib.request
import urllib.parse
import netifaces as ni
sys.path.append('/home/pi/bts')
import gsmsms as gsm
scriptpath = "/home/pi/bts/database_script.py"
sys.path.append(os.path.abspath(scriptpath))
import database_script
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
global inputstatus,outputstatus,modeoutputstatus,Alarmspk,countsec,countmin,Beep,lastsecond,lastminute,lasthour,datetimealarms,looprunning,indexmodbus,indextask
global connect485,indexvalue,counthour,datedatahistory,daydatahistory,newdatahistory
global datedatachart,daydatachart,lastchannel
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
looprunning=1
indexmodbus=0
indextask=0
connect485=0
indexvalue=0
counthour=0
datedatahistory=""
daydatahistory=""
newdatahistory=1        #=1 new, =0 not
lastchannel=0           #=1 change channel, =0 not
datedatachart=""
daydatachart=""
#-----
# to use Raspberry Pi board pin numbers
#GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False) 
GPIO.setup(LEDRUN, GPIO.OUT) # sets i to output and 0V, off
GPIO.setup(LEDERROR, GPIO.OUT) # sets i to output and 0V, off
GPIO.setup(OUTBEEP, GPIO.OUT) # sets i to output and 0V, off
#---------------------------------------------------------------------------
# Khac phuc loi khi thay doi sai dia chi IP
# Nguong cai dat la so phay dong
# Greentech
version="Version:19.4.17"    
dbname='/home/pi/bts/database.db'
sys.path.append("/home/pi/webiopi/htdocss")  #<--- or whatever your path is !

# Enable debug output
# webiopi.setDebug()
# Doc du lieu canh bao, khong qua 100 su kien
# 19/04/16
@webiopi.macro
def load_alarm_tablet():
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # ID |date | time | ten su kien canh bao | 
        curs.execute("SELECT * FROM alarmdisplay ORDER BY tdate DESC, ttime DESC" )
        for row in curs.fetchmany(100):
            data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
        #print (data)
        #conn.close()
    return (data)


# Doc du lieu canh bao theo ngay
@webiopi.macro
def load_alarm_tablet_day(days):
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # Hien thi theo kenh va ngay thang
        if(len(days)>0):
            for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate>date('now','localtime','-%s day')  ORDER BY ID DESC" % (days)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break                
        #print (data)
        #conn.close()
    return (data)

# Doc du lieu canh bao, khong qua 6 su kien index.htm
@webiopi.macro
def load_alarm_tablet_index():
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # ID |date | time | ten su kien canh bao | 
        curs.execute("SELECT * FROM alarmdisplay ORDER BY tdate DESC, ttime DESC" )
        for row in curs.fetchall():
            data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +","+ str(IOsetting.lowinput[i])+","+str(IOsetting.highinput[i])+","+\
                  str(GPIO.input(INP1+i))+","+ str(GPIO.input(OUT1+i))+","+str(IOsetting.modeoutput[i])+"\r\n"
            i=i+1
            if(i>5):
                break
        #print (data)
        #conn.close()
    return (data)

    
# Doc du lieu canh bao theo ngay thang: alarmdata.htm
@webiopi.macro
def load_alarm_tablet_date(startdate,enddate):
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # Hien thi theo kenh va ngay thang
        if(len(startdate)>0 and len(enddate)>0):
            for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (startdate,enddate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break
        elif (len(startdate)==0 and len(enddate)>0):
            for row in curs.execute("SELECT * FROM alarmdisplay  WHERE tdate=='%s'  ORDER BY ID DESC" % (enddate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break
        elif (len(startdate)>0 and len(enddate)==0):
            for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate=='%s'  ORDER BY ID DESC" % (startdate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break
                    
        #print (data)
        #conn.close()
    return (data)

# Doc du lieu canh bao theo ngay
@webiopi.macro
def load_alarm_tablet_day_channel(days,channel):
    channel=urllib.parse.unquote(channel)
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # Hien thi theo kenh va ngay thang
        if(len(days)>0):
            for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate>date('now','localtime','-%s day') AND event LIKE '%s' ORDER BY ID DESC" % (days,'%'+channel+'%')):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break                
        #print (data)
        #conn.close()
    return (data)

# Doc du lieu canh bao theo ngay thang: alarmdata.htm
@webiopi.macro
def load_alarm_tablet_date_channel(startdate,enddate,channel):
    channel=urllib.parse.unquote(channel)
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # Hien thi theo kenh va ngay thang
        if(len(startdate)>0 and len(enddate)>0):
            for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate>='%s' AND tdate<='%s' AND event LIKE '%s' ORDER BY ID DESC" % (startdate,enddate,'%'+channel+'%')):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break
        elif (len(startdate)==0 and len(enddate)>0):
            for row in curs.execute("SELECT * FROM alarmdisplay  WHERE tdate=='%s'  ORDER BY ID DESC" % (enddate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break
        elif (len(startdate)>0 and len(enddate)==0):
            for row in curs.execute("SELECT * FROM alarmdisplay WHERE tdate=='%s'  ORDER BY ID DESC" % (startdate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]) +"\r\n"
                i=i+1
                if(i>5000):
                    break
                    
        #print (data)
        #conn.close()
    return (data)

# Doc du lieu theo chu ky, khong qua 100 su kien, hien thi index
@webiopi.macro
def load_history_data():
    data=""
    i=0
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # ID |date | time | channel | namechannel | value | unit | status | 
        curs.execute("SELECT * FROM historydata WHERE tdate=date('now','localtime') ORDER BY ID DESC" )
        for row in curs.fetchmany(30):
            data=data+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"

        #print (data)
        #conn.close()
    return (data)


# display the contents of the database channel
@webiopi.macro
def load_history_data_date(startdate,enddate):
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # Hien thi theo kenh va ngay thang
        if(len(startdate)>0 and len(enddate)>0):
            for row in curs.execute("SELECT * FROM historydata WHERE tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (startdate,enddate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
                i=i+1
                if(i>5000):
                    break
        elif (len(startdate)==0 and len(enddate)>0):
            for row in curs.execute("SELECT * FROM historydata  WHERE tdate=='%s'  ORDER BY ID DESC" % (enddate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
                i=i+1
                if(i>5000):
                    break
        elif (len(startdate)>0 and len(enddate)==0):
            for row in curs.execute("SELECT * FROM historydata WHERE tdate=='%s'  ORDER BY ID DESC" % (startdate)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
                i=i+1
                if(i>5000):
                    break
                    
        #print (data)
        #conn.close()
    return (data)
# display the contents of the database channel
@webiopi.macro
def load_history_data_day(days):
    i=0
    data=""
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # Hien thi theo kenh va ngay thang
        if(len(days)>0):
            for row in curs.execute("SELECT * FROM historydata WHERE tdate>date('now','localtime','-%s day')  ORDER BY ID DESC" % (days)):
                data=data+str(i+1)+","+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
                i=i+1
                if(i>5000):
                    break
                    
        #print (data)
        #conn.close()
    return (data)
#--------------------------------------
# Hien thi o Data Tablet, moi 24/11/2015
# ID | Date | Time | Channel | Name | Value | Unit | Status
# 07/04/16
@webiopi.macro
def load_history_data_channel_day2(channel,days):
    global newdatahistory,daydatahistory,lastchannel
    i=0
    j=0
    if(lastchannel!=channel):
        lastchannel=channel
    newdatahistory=1
        
    if(newdatahistory==1 or len(daydatahistory)==0):
        newdatahistory=0
        daydatahistory=""
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            # Hien thi theo kenh va so ngay
            if(len(days)>0):
                curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate>date('now','localtime','-%s day')  ORDER BY ID DESC" % (channel,days))
                for row in curs.fetchmany(3000):
                    daydatahistory=daydatahistory+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"              
            #conn.close()
    return (daydatahistory)

# 07/04/16
@webiopi.macro
def load_history_data_channel_date2(channel,startdate,enddate):
    global newdatahistory,datedatahistory,lastchannel
    i=0
    if(lastchannel!=channel):
        lastchannel=channel
    newdatahistory=1
        
    if(newdatahistory==1 or len(datedatahistory)==0):
        newdatahistory=0
        datedatahistory=""
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            # Hien thi theo kenh va ngay thang
            if(len(startdate)>0 and len(enddate)>0):
                for row in curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (channel,startdate,enddate)):
                    datedatahistory=datedatahistory+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
                    i=i+1
                    if(i>5000):
                        break
            elif (len(startdate)==0 and len(enddate)>0):
                for row in curs.execute("SELECT * FROM historydata  WHERE channel='%s' AND tdate=='%s'  ORDER BY ID DESC" % (channel,enddate)):
                    datedatahistory=datedatahistory+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
                    i=i+1
                    if(i>5000):
                        break
            elif (len(startdate)>0 and len(enddate)==0):
                for row in curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate=='%s'  ORDER BY ID DESC" % (channel,startdate)):
                    datedatahistory=datedatahistory+str(row[1])+","+str(row[2])+","+str(row[3]+1)+","+ Set.namechannel[row[3]] + "," + str(row[4])+","+Set.unitreg[row[3]]+","+str(row[5])+"\r\n"
                    i=i+1
                    if(i>5000):
                        break
                    
            #print (data)
            #conn.close()
    return (datedatahistory)
#---------------------------------------
# display the contents for trend
# Time | Value
# 07/04/16
@webiopi.macro
def load_history_days_channel(channel,days):
    global newdatahistory,daydatachart,lastchannel
    i=0
    j=0
    if(lastchannel!=channel):
        lastchannel=channel
    newdatahistory=1
        
    if(newdatahistory==1 or len(daydatachart)==0):
        newdatahistory=0
        daydatachart=""
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            # Hien thi theo kenh va ngay thang
            if(len(days)>0):
                curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate>date('now','localtime','-%s day')  ORDER BY tdate DESC, ttime DESC" % (channel,days))
                for row in curs.fetchmany(1000):
                    j=j+1
                    if(j>100):
                        j=0
                        daydatachart=daydatachart+str(row[1])+","+ str(row[4])+"\r\n"
                    else:
                        HM=str(row[2]).split(":")
                        daydatachart=daydatachart+HM[0]+":"+HM[1]+","+ str(row[4])+"\r\n"
                        
            #print (data)
            #conn.close()
    return (daydatachart)

# display the contents for trend
# Time | Value
# 07/04/16
@webiopi.macro
def load_history_date_channel(channel,startdate,enddate):
    global newdatahistory,datedatachart,lastchannel
    i=0
    if(lastchannel!=channel):
        lastchannel=channel
    newdatahistory=1
        
    if(newdatahistory==1 or len(datedatachart)==0):
        newdatahistory=0
        datedatachart=""
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            # Hien thi theo kenh va ngay thang
            if(len(startdate)>0 and len(enddate)>0):
                curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate>='%s' AND tdate<='%s'  ORDER BY ID DESC" % (channel,startdate,enddate))
                for row in curs.fetchmany(1000):
                    datedatachart=datedatachart+str(row[2])+","+ str(row[4])+"\r\n"
      
            elif (len(startdate)==0 and len(enddate)>0):
                curs.execute("SELECT * FROM historydata  WHERE channel='%s' AND tdate=='%s'  ORDER BY ttime DESC" % (channel,enddate))
                for row in curs.fetchmany(1000):
                    datedatachart=datedatachart+str(row[2])+","+ str(row[4])+"\r\n"

            elif (len(startdate)>0 and len(enddate)==0):
                curs.execute("SELECT * FROM historydata WHERE channel='%s' AND tdate=='%s'  ORDER BY ttime DESC" % (channel,startdate))
                for row in curs.fetchmany(1000):
                    datedatachart=datedatachart+str(row[2])+","+ str(row[4])+"\r\n"
            #conn.close()
    return (datedatachart)

# Du lieu cho viec gui dinh kem Email2
def load_history_data_day_attachment2(days):
    i=0
    j=0
    data=Netsetting.hostname+','+strftime("%m/%d/%Y %H:%M",localtime())+','+str(Netsetting.ip)+":8880,http://ecapro.com.vn\r\n"
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        # Hien thi theo kenh va ngay thang
        if(len(days)>0):
            #ID,Date Time,Name1(unit1),Name2(unit2),Name3(unit3)...\r\n
            data=data+"ID,Date Time"
            for i in range(Set.maxchannel):
                data=data+','+Set.namechannel[i]+'('+Set.unitreg[i]+')'
            data=data+'\r\n'
            # Cac gia tri do
            i=0
            for row in curs.execute("SELECT * FROM historydata WHERE tdate>date('now','localtime','-%s day')  ORDER BY ID ASC" % (days)):
                if(j==0):
                    data=data+str(i+1)+","+str(row[1])+" "+str(row[2])+","+ str(row[4])
                else:
                    data=data+","+ str(row[4])
                j=j+1
                if(j>=Set.maxchannel):
                    j=0
                    data=data+'\r\n'
                    i=i+1
                    if(i>10000):
                        break
                    
        #print (data)
        #conn.close()
    return (data)

# Dieu khien loi ra
def Outputs(index):
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
            
# Dieu khien loi ra
@webiopi.macro
def Output(index):
    global Beep,OUTGENERATOR,CHANGEOUTGENERATOR
    Outputs(index)
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
        data=data+str(Calibration.realvalue[i])+","
        data=data+Set.unitreg[i] +","+ str(usbrtu.status[i])+","+str(inputstatus)+","+str(outputstatus)+"\r\n"
        
    return(data)
# Che do Dieu khien loi ra
@webiopi.macro
def ModeOutput(index):
    global Beep,OUTGENERATOR,CHANGEOUTGENERATOR,inputstatus,outputstatus,modeoutputstatus
    if(index=='1'):
        if (IOsetting.modeoutput[0]):
            IOsetting.modeoutput[0]=0
            IOsetting.modeoutput[1]=0
        else:
            IOsetting.modeoutput[0]=1
            IOsetting.modeoutput[1]=1
    if(index=='2'):
        if (IOsetting.modeoutput[1]):
            IOsetting.modeoutput[1]=0
        else:
            IOsetting.modeoutput[1]=1
    if(index=='3'):
        if (IOsetting.modeoutput[2]):
            IOsetting.modeoutput[2]=0
        else:
            IOsetting.modeoutput[2]=1
    if(index=='4'):
        if (IOsetting.modeoutput[3]):
            IOsetting.modeoutput[3]=0
        else:
            IOsetting.modeoutput[3]=1 
    if(index=='5'):
        if (IOsetting.modeoutput[4]):
            IOsetting.modeoutput[4]=0
        else:
            IOsetting.modeoutput[4]=1
    if(index=='6'):
        if (IOsetting.modeoutput[5]):
            IOsetting.modeoutput[5]=0 
        else:
            IOsetting.modeoutput[5]=1
        
    Beep=1
    inputstatus=GPIO.input(INP1)+2*GPIO.input(INP2)+4*GPIO.input(INP3)+8*GPIO.input(INP4)+16*GPIO.input(INP5)+32*GPIO.input(INP6)
    outputstatus=GPIO.input(OUT1)+2*GPIO.input(OUT2)+4*GPIO.input(OUT3)+8*GPIO.input(OUT4)+16*GPIO.input(OUT5)+32*GPIO.input(OUT6)
    modeoutputstatus=IOsetting.modeoutput[0]+2*IOsetting.modeoutput[1]+4*IOsetting.modeoutput[2]+8*IOsetting.modeoutput[3]+16*IOsetting.modeoutput[4]+\
                      32*IOsetting.modeoutput[5]+64*IOsetting.modeoutput[6]+128*IOsetting.modeoutput[7]
    data=""
    data=str(inputstatus) +","+ str(outputstatus)+","+ str(modeoutputstatus)+"\r\n"
    return(data)

# Dieu khien loi ra
@webiopi.macro
def Outputgraph(index):
    global Beep,OUTGENERATOR,CHANGEOUTGENERATOR,inputstatus,outputstatus,modeoutputstatus
    Outputs(index)    
    Beep=1
    inputstatus=GPIO.input(INP1)+2*GPIO.input(INP2)+4*GPIO.input(INP3)+8*GPIO.input(INP4)+16*GPIO.input(INP5)+32*GPIO.input(INP6)
    outputstatus=GPIO.input(OUT1)+2*GPIO.input(OUT2)+4*GPIO.input(OUT3)+8*GPIO.input(OUT4)+16*GPIO.input(OUT5)+32*GPIO.input(OUT6)
    modeoutputstatus=IOsetting.modeoutput[0]+2*IOsetting.modeoutput[1]+4*IOsetting.modeoutput[2]+8*IOsetting.modeoutput[3]+16*IOsetting.modeoutput[4]+\
                      32*IOsetting.modeoutput[5]+64*IOsetting.modeoutput[6]+128*IOsetting.modeoutput[7]
    data=""
    data=str(inputstatus) +","+ str(outputstatus)+","+ str(modeoutputstatus)+"\r\n"
        
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
# Calibration.realvalue[17] là 1 byte có 8 bit voi 4 bit dau la input và 4 bit sau la output
@webiopi.macro
def UpdateGenerator():
    data=""
    data=str(IOsetting.modeoutgen) +","+str(OUTGENERATOR) +","+ str(Calibration.realvalue[17])+"\r\n"
    return(data)
#-----------------------------        
# Hien thi du lieu tren Index
@webiopi.macro
def UpdateMonitor():
    global looprunning
    # Time | channel | namechannel | value | unit | status | Input | 
    data=""
    #if(looprunning==1):
    #    looprunning=0
    for i in range(Set.maxchannel):
        data=data+strftime("%H:%M:%S",localtime())+","+str(i+1)+"," + Set.namechannel[i] +","
        data=data+str(Calibration.realvalue[i])+","
        data=data+Set.unitreg[i] +","+ str(usbrtu.status[i])+","+str(inputstatus)+","+str(outputstatus)+"\r\n"
        
    return(data)
#-----------------------------        
# Hien thi du lieu tren Graph
@webiopi.macro
def UpdateMonitorAll():
    # namechannel | value | unit | status | lowset | high
    data=""
    for i in range(Set.maxchannel):
        data=data+Set.namechannel[i] +","
        data=data+str(Calibration.realvalue[i])+","
        data=data+Set.unitreg[i] +","+ str(usbrtu.status[i])+","
        data=data+str(Set.lowset[i]) +","+ str(Set.highset[i])+"\r\n"
        
    return(data)
@webiopi.macro
def UpdateInOut():
    #  Input | Output | ModeOutput
    data=""
    data=str(inputstatus) +","+ str(outputstatus)+","+ str(modeoutputstatus)+"\r\n"
        
    return(data)
#-----Hien thi tren index voi cac trang thai-----
@webiopi.macro
def UpdateStatus():
    Netsetting.reportserver=Netsetting.reportserver.replace(",", ":")   # Thay dau , thanh : 
    data=""
    data="ID: "+ Netsetting.id + "/ " + str(Netsetting.hostname) +","
    if(IOsetting.alarm):
        data=data+'ARMING,'
    else:
        data=data+'DISARM,'
    if(len(Gsm.reportsms)>0 and Gsm.csq>0):
        data=data+str(Gsm.reportsms)+". GSM:"+str(Gsm.network)+"; CSQ:"+str(Gsm.csq)+","
    elif(len(Gsm.reportsms)>0 and Gsm.csq==0):
        data=data+str(Gsm.reportsms)+". GSM:"+str(Gsm.network)+","    
    elif(Gsm.csq>0):
        data=data+"GSM:"+str(Gsm.network)+"; CSQ:"+str(Gsm.csq)+","
    else:
        data=data+"GSM:"+str(Gsm.network)+","
        
    data=data+Netsetting.reportserver[:40]+","+IOsetting.reporthmi[:20]+". "+ usbrtu.reportmodbus[:20]+"\r\n"
    return(data)
#-----Hien thi tren index cac lenh cusd-----
@webiopi.macro
def SendCusd(data):
    sms.dial(data+"#")
    print(sms._ussdResponse)
    return (sms._ussdResponse)

#---------Net setting----------------------
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,  # SIOCGIFADDR
        struct.pack('256s',  bytes(ifname[:15], 'utf-8')))
        [20:24])
#------------------------
class netsetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/Netsetting.txt"
        open(self.file, "r")
        self.sizedatatoserver=0
        self.reportserver=""
        self.id=""
        self.mac=""
        self.hostname="ECA-GPIs6.6DA"
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
        self.username2=""
        self.newpass2=""
        self.conpass2=""
        self.mailserver="ecapro.com.vn"
        self.mailport="25"
        self.mailfrom="info@ecapro.com.vn"
        self.mailpass="ecaprovn"
        self.mailto0="giamsatnhietdo.ecapro@gmail.com"
        self.mailto1=""
        self.mailto2=""
        # Phien ban FTP1 file txt
        self.serverftp=""
        self.pathftp=""
        self.userftp=""
        self.passftp=""
        # Phien ban FTP2 file csv
        self.serverftp2=""
        self.pathftp2=""
        self.userftp2=""
        self.passftp2=""
        
    def Load_setting(self):
        f = open(self.file, "r")
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        print("Network Setting:",setting)
        if(len(setting)>=29):
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
            self.serverftp=setting[8]
            self.pathftp=setting[9]
            self.userftp=setting[10]
            self.passftp=setting[11]
            self.username=setting[12]
            self.newpass=setting[13]
            self.conpass=setting[14]
            # Update 29/12/16
            self.username2=setting[15]
            self.newpass2=setting[16]
            self.conpass2=setting[17]
            
            self.mailserver=setting[18]
            self.mailport=setting[19]
            self.mailfrom=setting[20]
            self.mailpass=setting[21]
            self.mailto0=setting[22]
            self.mailto1=setting[23]
            self.mailto2=setting[24]

            self.serverftp2=setting[25]
            self.pathftp2=setting[26]
            self.userftp2=setting[27]
            self.passftp2=setting[28]
            
            print("Read Net Setting ok")
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            data=data+str(self.serverftp)+"\n"+str(self.pathftp)+"\n"+str(self.userftp)+"\n"+str(self.passftp)+"\n"   
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto0)+"\n"+str(self.mailto1)+"\n"+str(self.mailto2)+"\n"
            data=data+str(self.serverftp2)+"\n"+str(self.pathftp2)+"\n"+str(self.userftp2)+"\n"+str(self.passftp2)+"\n" 
        else:
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            data=data+str(self.serverftp)+"\n"+str(self.pathftp)+"\n"+str(self.userftp)+"\n"+str(self.passftp)+"\n" 
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto0)+"\n"+str(self.mailto1)+"\n"+str(self.mailto2)+"\n"
            data=data+str(self.serverftp2)+"\n"+str(self.pathftp2)+"\n"+str(self.userftp2)+"\n"+str(self.passftp2)+"\n"
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
        if(len(setting)>=25):
            self.mac=setting[0]
            self.hostname=setting[1]
            self.dhcp=int(setting[2])
            if(validate_ip(setting[3])):
                self.ip=setting[3]
            if(validate_ip(setting[4])):
                self.gateway=setting[4]
            self.mask=setting[5]
            self.ipserver=setting[6]
            self.portserver=setting[7]
            self.serverftp=setting[8]
            self.pathftp=setting[9]
            self.userftp=setting[10]
            self.passftp=setting[11]
            self.username=setting[12]
            self.newpass=setting[13]
            self.conpass=setting[14]
            # Update 29/12/16
            self.username2=setting[15]
            self.newpass2=setting[16]
            self.conpass2=setting[17]
            
            self.mailserver=setting[18]
            self.mailport=setting[19]
            self.mailfrom=setting[20]
            self.mailpass=setting[21]
            self.mailto0=setting[22]
            self.mailto1=setting[23]
            self.mailto2=setting[24]
            # Update 30/12/16
            self.serverftp2=setting[25]
            self.pathftp2=setting[26]
            self.userftp2=setting[27]
            self.passftp2=setting[28]
            if(len(self.username)>0 and len(self.newpass)>0 and len(self.conpass)>0):
                if(self.save_pass()==False):
                    return
            if(len(self.username2)>0 and len(self.newpass2)>0 and len(self.conpass2)>0):
                if(self.save_pass2()==False):
                    return
            self.setiface()
            data=str(self.mac)+"\n"+str(self.hostname)+"\n"+str(self.dhcp)+"\n"+str(self.ip)+"\n"+str(self.gateway)+"\n"
            data=data+str(self.mask)+"\n"+str(self.ipserver)+"\n"+str(self.portserver)+"\n"
            data=data+str(self.serverftp)+"\n"+str(self.pathftp)+"\n"+str(self.userftp)+"\n"+str(self.passftp)+"\n"
            data=data+str(self.mailserver)+"\n"+str(self.mailport)+"\n"+str(self.mailfrom)+"\n"+str(self.mailpass)+"\n"+str(self.mailto0)+"\n"+str(self.mailto1)+"\n"+str(self.mailto2)+"\n"
            data=data+str(self.serverftp2)+"\n"+str(self.pathftp2)+"\n"+str(self.userftp2)+"\n"+str(self.passftp2)+"\n"
            print("Saved Net Setting")
            return (data)
    # Admin
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
            
    # User viewer
    def save_pass2(self):
        file = "/etc/webiopi/passwd2"
        fp = open(file, "w")
        if (self.newpass2!= self.conpass2):
            print("Passwords don't match !")
            return False
        else:
            from webiopi.utils.crypto import encryptCredentials
            auth = encryptCredentials(self.username2, self.newpass2)
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
    read=read.replace(':', '/')
    return (Netsetting.Save_setting(read))

@webiopi.macro
def Reboot():
    # shutdown our Raspberry Pi
    os.system("sudo reboot")
#---------IO setting----------------------
class iosetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/iosetting.txt"
        self.tsiren3buff=0
        self.reporthmi=""
        
        self.alarm=1
        self.sms=1
        self.tinfor=24          #Hour
        self.tdelay=20           #Min
        self.tsiren3=10         #Sec
        self.tloopout12=20      #Min
        self.modeoutgen=0       #auto=0, manual=1
        self.temphighon12=30.0    #oC
        self.templowoff12=10.0    #oC
        self.channel2highon4=90     #Value kenh 2
        self.channel3highon5=90     #Value kenh 3
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
        if(len(setting)>=51):
            self.alarm=int(setting[0])
            self.sms=int(setting[1])
            self.tinfor=int(setting[2])     #Hour
            self.tdelay=int(setting[3])     #Min
            self.tsiren3=int(setting[4])     #Sec
            self.channel3highon5=int(setting[5] )         #Min
            self.tloopout12=int(setting[6] )     #Min
            self.modeoutgen=int(setting[7])      #auto=0, manual=1
            self.temphighon12=float(setting[8])    #oC
            self.templowoff12=float(setting[9])    #oC
            self.channel2highon4=int(setting[10])     #%
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+11])          
                self.lowinput[i]=setting[i*5+12]      
                self.highinput[i]=setting[i*5+13]
                self.sireninput[i]=int(setting[i*5+14])
                self.modeoutput[i]=int(setting[i*5+15])
            print("Read IO Setting ok")
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+"\n"+str(self.tdelay)+"\n"+str(self.tsiren3)+"\n"+str(self.channel3highon5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.channel2highon4)+"\n"
            for i in range(len(self.modeinput)):  
                data=data+str(self.modeinput[i])+"\n"+str(self.lowinput[i])+"\n"+str(self.highinput[i])+"\n"+str(self.sireninput[i])+"\n"+str(self.modeoutput[i])+"\n"
        else:
            data=""
            data=str(self.alarm)+"\n"+str(self.sms)+"\n"+str(self.tinfor)+"\n"+str(self.tdelay)+"\n"+str(self.tsiren3)+"\n"+str(self.channel3highon5)+"\n"+\
                  str(self.tloopout12)+"\n"+str(self.modeoutgen)+"\n"+str(self.temphighon12)+"\n"+str(self.templowoff12)+"\n"+str(self.channel2highon4)+"\n"
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
        if(len(setting)>=51):
            self.alarm=int(setting[0])
            self.sms=int(setting[1])
            self.tinfor=int(setting[2])     #Hour
            self.tdelay=int(setting[3])     #Min
            self.tsiren3=int(setting[4])     #Sec
            self.channel3highon5=int(setting[5] )         #Min
            self.tloopout12=int(setting[6] )     #Min
            self.modeoutgen=int(setting[7])      #auto=0, manual=1
            self.temphighon12=float(setting[8])    #oC
            self.templowoff12=float(setting[9])    #oC
            self.channel2highon4=int(setting[10])     #%
            for i in range(len(self.modeinput)):  
                self.modeinput[i]=int(setting[i*5+11])          
                self.lowinput[i]=setting[i*5+12]      
                self.highinput[i]=setting[i*5+13]
                self.sireninput[i]=int(setting[i*5+14])
                self.modeoutput[i]=int(setting[i*5+15])
            # Cap nhat thoi gian
            print(str(setting[i*5+16]))
            os.system("sudo date -s '"+str(setting[i*5+16])+"'")
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


#------------------ Modbus Setting------------------------
class settings(object):
    def __init__(self):
        self.file = "/home/pi/bts/Setting.txt"
        self.timeout=1         # Mac dinh 1 sec
        self.connect=0         # So luong ket noi modbus duoc cua 1 dia chi
        self.tdelaybuff=[]
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
            self.tdelaybuff.append(0)
            self.namechannel.append(i)
            self.addchannel.append(i)
            self.functionchannel.append(i)
            self.startreg.append(i)
            self.numberreg.append(i)
            self.typereg.append(i)
            self.lowset.append(0.0)
            self.highset.append(100.0)
            self.unitreg.append(i)
    def Load_setting(self):
        f = codecs.open(self.file, "r",encoding='utf8')
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        #print(len(setting),"Read Setting:",setting)
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
                self.lowset[i]=float(setting[i*9+12])       
                self.highset[i]=float(setting[i*9+13])         
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
                self.lowset[i]=0.0       
                self.highset[i]=100.0         
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
                self.lowset[i]=float(setting[i*9+12])       
                self.highset[i]=float(setting[i*9+13])         
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
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    read=read.replace(':', '/')
    Set.Save_setting(read)
    return (read)

#------------------ Scheduler Setting------------------------
class schedulersettings(object):
    def __init__(self):
        self.file = "/home/pi/bts/Scheduler.txt"
        self.ton=[]
        self.tof=[]
        self.tonHour=[]
        self.tofHour=[]
        self.tonMin=[]
        self.tofMin=[]
        self.tonstring=[]
        self.tofstring=[]
        self.wdate=[]
        self.select=[]
        for i in range(10):    
            self.tonstring.append("12:00")
            self.tofstring.append("12:00")
            self.ton.append(0)
            self.tof.append(0)
            self.tonHour.append(0)
            self.tofHour.append(0)
            self.tonMin.append(0)
            self.tofMin.append(0)
            self.wdate.append(0)
            self.select.append(0)

    def TimeConvert(self):
        for i in range(10):
            self.ton[i]=self.tonstring[i].split(':')
            if(len(self.ton[i])==2):
                self.tonHour[i]=int(self.ton[i][0])
                self.tonMin[i]=int(self.ton[i][1])
            else:
                return 0
            self.tof[i]=self.tofstring[i].split(':')
            if(len(self.tof[i])==2):
                self.tofHour[i]=int(self.tof[i][0])
                self.tofMin[i]=int(self.tof[i][1])
            else:
                return 0    
    
        
    def Load_setting(self):
        f = codecs.open(self.file, "r",encoding='utf8')
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        #print(len(setting),"Read Setting:",setting)
        if(len(setting)>=10*4):
            for i in range(10):
                self.tonstring[i]=str(setting[i*4+0])
                self.tofstring[i]=str(setting[i*4+1])
                self.wdate[i]=int(setting[i*4+2])
                self.select[i]=int(setting[i*4+3])

            self.TimeConvert()    
            print("Read Scheduler Setting ok")
        else:
            for i in range(10):  
                self.tonstring[i]="12:00"
                self.tofstring[i]="12:00"
                self.wdate[i]=0
                self.select[i]=0
    
            data=""
            for i in range(10):  
                data=data+str(self.tonstring[i])+"\n"
                data=data+str(self.tofstring[i])+"\n"
                data=data+str(self.wdate[i])+"\n"
                data=data+str(self.select[i])+"\n"
                
            self.Save_setting(data)
            print("Default Scheduler Setting")

        return (data)
    
    def Save_setting(self,data):
        f = codecs.open(self.file, "w",encoding='utf8')
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        #print (setting)
        if(len(setting)>=10*4):
            for i in range(10):
                self.tonstring[i]=str(setting[i*4+0])
                self.tofstring[i]=str(setting[i*4+1])
                self.wdate[i]=int(setting[i*4+2])
                self.select[i]=int(setting[i*4+3])
                
            self.TimeConvert()
            print("Saved Scheduler Setting")
            
    def Run_timer(self):
        global Beep
        now = datetime.datetime.now()
        print('weekday:'+str(now.weekday())+'.hour:'+str(now.hour)+'.min:'+str(now.minute)+'.hourset:'+str(self.tonHour[0])+'.minset:'+str(self.tonMin[0])+'.select:'+str(self.select[0])+'.sday:'+str(self.wdate[0]))
        for i in range(10):
            if(self.select[i]>0 and (self.wdate[i]==0 or (self.wdate[i]==1 and now.weekday()<4) or (self.wdate[i]==2 and now.weekday()==5) or (self.wdate[i]==3 and now.weekday()==6))):
                print('Scheduler Select:'+str(self.select[i])+str(self.wdate[i]))
                if(self.tonHour[i]==now.hour and self.tonMin[i]==now.minute):
                    if(self.select[i]<5):
                        GPIO.add_event_detect(INP1+self.select[i]-1, GPIO.BOTH, callback=inputEventHandler, bouncetime=2000)
                    elif(self.select[i]==5):
                        GPIO.add_event_detect(INP1, GPIO.BOTH, callback=inputEventHandler, bouncetime=2000)
                        GPIO.add_event_detect(INP2, GPIO.BOTH, callback=inputEventHandler, bouncetime=2000)
                        GPIO.add_event_detect(INP3, GPIO.BOTH, callback=inputEventHandler, bouncetime=2000)
                        GPIO.add_event_detect(INP4, GPIO.BOTH, callback=inputEventHandler, bouncetime=2000)
                        GPIO.add_event_detect(INP5, GPIO.BOTH, callback=inputEventHandler, bouncetime=2000)
                        GPIO.add_event_detect(INP6, GPIO.BOTH, callback=inputEventHandler, bouncetime=2000)
                    elif(self.select[i]==6):
                        IOsetting.alarm=1
                    elif(self.select[i]==7):
                        GPIO.output(OUT4,True)
                    elif(self.select[i]==8):
                        GPIO.output(OUT5,True)
                    elif(self.select[i]==9):
                        GPIO.output(OUT6,True)
                    Beep=2
                    print('Scheduler Timer On')
                        
                elif(self.tofHour[i]==now.hour and self.tofMin[i]==now.minute):
                    if(self.select[i]<5):
                        GPIO.remove_event_detect(INP1+self.select[i]-1)
                    elif(self.select[i]==5):
                        GPIO.remove_event_detect(INP1)
                        GPIO.remove_event_detect(INP2)
                        GPIO.remove_event_detect(INP3)
                        GPIO.remove_event_detect(INP4)
                        GPIO.remove_event_detect(INP5)
                        GPIO.remove_event_detect(INP6)
                    elif(self.select[i]==6):
                        IOsetting.alarm=0
                    elif(self.select[i]==7):
                        GPIO.output(OUT4,False)
                    elif(self.select[i]==8):
                        GPIO.output(OUT5,False)
                    elif(self.select[i]==9):
                        GPIO.output(OUT6,False) 
                    Beep=2
                    print('Scheduler Timer Off')
#-------------Run Scheduler-------------
Scheduler=schedulersettings()
Scheduler.Load_setting()
# Phan web truy cap
@webiopi.macro
def load_schedulersetting():
    data=Scheduler.Load_setting()
    return (data)

@webiopi.macro
def save_schedulersetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    #read=read.replace(':', '/')
    Scheduler.Save_setting(read)
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
    #print('== SMS message received ==\nFrom: {0}\nTime: {1}\nMessage:\n{2}\n'.format(sms.number, sms.time, sms.text))
    
    for i in range(len(Netsetting.tel)):    #5 so dien thoai
        if(sms.number.find(Netsetting.tel[i])==0 and len(Netsetting.tel[i])>=4):
            break
    if(i>=len(Netsetting.tel)-1):
        Gsm.reportsms="Not Admin: "+str(sms.number)
        return
    
    Gsm.reportsms="Admin: "+str(sms.number)+"; Sms: "+str(sms.text[:20])
    if(sms.text.find("Alarm off")!=-1):
        IOsetting.alarm=0
        textsms=Netsetting.hostname+'\nAlarm off'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"

    elif(sms.text.find("Alarm on")!=-1):
        IOsetting.alarm=1
        textsms=Netsetting.hostname+'\nAlarm on'+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/"
        
    elif(sms.text.find("Value?")!=-1):
        for i in range(Set.maxchannel):
            data=data+str(Set.namechannel[i])+":"+str(Calibration.realvalue[i])+" "+str(Set.unitreg[i])+"\n"
  
        textsms=Netsetting.hostname+'\n'+data

    elif(sms.text.find("Test?")!=-1):
        data="GSM:"+Gsm.network+",CSQ:"+str(Gsm.csq)+"\n"
        data=data+str(Gsm.reportsms)+"\n"
        data=data+str(Netsetting.reportserver)+"\n"+str(Netsetting.ip)+":8880\n"
        data=data+"Modbus connected:"+str(Set.connect)+"/"+str(Set.maxchannel)
        textsms=Netsetting.hostname+'\n'+data+'\n'+str(version)
        
    elif(sms.text.find("Infor?")!=-1):
        if(IOsetting.alarm):
            data='ARMING\n'
        else:
            data='DISARM\n'
        data=data+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
        data=data+"Output: "+bin(outputstatus)[2:].zfill(6)[::-1]+"\n"
        for i in range(Set.maxchannel):
            data=data+str(Set.namechannel[i])+":"+str(Calibration.realvalue[i])+" "+str(Set.unitreg[i])+"\n"
            
        data=data+str(Netsetting.ip)+":8880"
        textsms=Netsetting.hostname+'\n'+data
    else:
        textsms=Netsetting.hostname+'\n'+Gsm.textsmsrec[:20]+': Error SMS!\nInfor?\nValue?\nTest?\nAlarm on\nAlarm off'

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
    GPIO.output(LEDERROR,False)
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
    database_script.creat_history_data()
    database_script.creat_alarm_tablet()
    #-------
    time.sleep(5)
    '''sms.connect('/dev/ttyUSB1', 115200)

    if(sms.connected==True):    
        sms.setsms()
        Gsm.network=sms.GetNetwork()
        Gsm.csq=sms.signalStrength()
        #sms.SendSMS('+84915086942', 'ECA-GPIs8.8CE running...')
    else:
    '''
    Gsm.network='not USB3G'
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
            q.put("1: "+str(IOsetting.lowinput[0]))
            if(IOsetting.sireninput[0]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("1:0 ",str(IOsetting.lowinput[0]))
        elif(IOsetting.modeinput[0]==1 and GPIO.input(INP1)==1):
            q.put("1: "+str(IOsetting.highinput[0]))
            if(IOsetting.sireninput[0]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("1:1 ",str(IOsetting.highinput[0]))
        elif(IOsetting.modeinput[0]==2):
            time.sleep(1)
            if(GPIO.input(INP1)==1):
                q.put("1: "+str(IOsetting.highinput[0]))
                print ("1:2 1",str(IOsetting.highinput[0])+str(IOsetting.tsiren3),str(GPIO.input(INP1)))
            else:
                q.put("1: "+str(IOsetting.lowinput[0]))
                print ("1:2 0",str(IOsetting.lowinput[0])+str(IOsetting.tsiren3),str(GPIO.input(INP1)))
            if(IOsetting.sireninput[0]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event CB Tu
    if(pin==INP2):
        if(IOsetting.modeinput[1]==0 and GPIO.input(INP2)==0):
            q.put("2: "+str(IOsetting.lowinput[1]))
            if(IOsetting.sireninput[1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("2:0 ",str(IOsetting.lowinput[1]))
        elif(IOsetting.modeinput[1]==1 and GPIO.input(INP2)==1):
            q.put("2: "+str(IOsetting.highinput[1]))
            if(IOsetting.sireninput[1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("2:1 ",str(IOsetting.highinput[1]))
        elif(IOsetting.modeinput[1]==2):
            time.sleep(1)
            if(GPIO.input(INP2)==1):
                q.put("2: "+str(IOsetting.highinput[1]))
                print ("2:2 ",str(IOsetting.highinput[1])+str(IOsetting.tsiren3))
            else:
                q.put("2: "+str(IOsetting.lowinput[1]))
                print ("2:2 ",str(IOsetting.lowinput[1])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[1]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event dau bao khoi
    if(pin==INP3):
        if(IOsetting.modeinput[2]==0 and GPIO.input(INP3)==0):
            q.put("3: "+str(IOsetting.lowinput[2]))
            if(IOsetting.sireninput[2]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("3:0 ",str(IOsetting.lowinput[2]))
        elif(IOsetting.modeinput[2]==1 and GPIO.input(INP3)==1):
            q.put("3: "+str(IOsetting.highinput[2]))
            if(IOsetting.sireninput[2]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("3:1 ",str(IOsetting.highinput[2]))
        elif(IOsetting.modeinput[2]==2):
            time.sleep(1)
            if(GPIO.input(INP3)==1):
                q.put("3: "+str(IOsetting.highinput[2]))
                print ("3:2 ",str(IOsetting.highinput[2])+str(IOsetting.tsiren3))
            else:
                q.put("3: "+str(IOsetting.lowinput[2]))
                print ("3:2 ",str(IOsetting.lowinput[2])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[2]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event dau bao nhiet gia tang
    if(pin==INP4):
        if(IOsetting.modeinput[3]==0 and GPIO.input(INP4)==0):
            q.put("4: "+str(IOsetting.lowinput[3]))
            if(IOsetting.sireninput[3]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("4:0 ",str(IOsetting.lowinput[3]))
        elif(IOsetting.modeinput[3]==1 and GPIO.input(INP4)==1):
            q.put("4: "+str(IOsetting.highinput[3]))
            if(IOsetting.sireninput[3]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("4:1 ",str(IOsetting.highinput[3]))
        elif(IOsetting.modeinput[3]==2):
            time.sleep(1)
            if(GPIO.input(INP4)==1):
                q.put("4: "+str(IOsetting.highinput[3]))
                print ("4:2 ",str(IOsetting.highinput[3])+str(IOsetting.tsiren3))
            else:
                q.put("4: "+str(IOsetting.lowinput[3]))
                print ("4:2 ",str(IOsetting.lowinput[3])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[3]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event dau bao ngap nuoc
    if(pin==INP5):
        if(IOsetting.modeinput[4]==0 and GPIO.input(INP5)==0):
            q.put("5: "+str(IOsetting.lowinput[4]))
            if(IOsetting.sireninput[4]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("5:0 ",str(IOsetting.lowinput[4]))
        elif(IOsetting.modeinput[4]==1 and GPIO.input(INP5)==1):
            q.put("5: "+str(IOsetting.highinput[4]))
            if(IOsetting.sireninput[4]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("5:1 ",str(IOsetting.highinput[4]))
        elif(IOsetting.modeinput[4]==2):
            time.sleep(1)
            if(GPIO.input(INP5)==1):
                q.put("5: "+str(IOsetting.highinput[4]))
                print ("5:2 ",str(IOsetting.highinput[4])+str(IOsetting.tsiren3))
            else:
                q.put("5: "+str(IOsetting.lowinput[4]))
                print ("5:2 ",str(IOsetting.lowinput[4])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[4]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
    # handle the input event dau bao vo kinh
    if(pin==INP6):
        if(IOsetting.modeinput[5]==0 and GPIO.input(INP6)==0):
            q.put("6: "+str(IOsetting.lowinput[5]))
            if(IOsetting.sireninput[5]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("6:0 ",str(IOsetting.lowinput[5]))
        elif(IOsetting.modeinput[5]==1 and GPIO.input(INP6)==1):
            q.put("5: "+str(IOsetting.highinput[5]))
            if(IOsetting.sireninput[5]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
                print ("6:1 ",str(IOsetting.highinput[5]))
        elif(IOsetting.modeinput[5]==2):
            time.sleep(1)
            if(GPIO.input(INP6)==1):
                q.put("6: "+str(IOsetting.highinput[5]))
                print ("6:2 ",str(IOsetting.highinput[5])+str(IOsetting.tsiren3))
            else:
                q.put("6: "+str(IOsetting.lowinput[5]))
                print ("6:2 ",str(IOsetting.lowinput[5])+str(IOsetting.tsiren3))
            if(IOsetting.sireninput[5]==1):
                IOsetting.tsiren3buff=IOsetting.tsiren3
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
        data=str(Netsetting.id)+"&"+str(Netsetting.hostname)+ "&"+types+"&"+message+"&"+str(inputstatus)+"&"+str(outputstatus)+"&"+str(modeoutputstatus)
        for i in range(Set.maxchannel):
            data=data+"&"+str(Calibration.realvalue[i])
        print(data)
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
        Netsetting.reportserver='Failed to recv socket.Error: '+str(msg)
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
                    if(binaryoutput[i]=='1' and i<6):
                        #if(IOsetting.modeoutput[i]==1):
                        out=OUT1+i
                        #print("OUTPUT",out)
                        GPIO.output(out,1)
                    elif(binaryoutput[i]=='1' and i==8):
                        OUTGENERATOR=3  #khoi dong may phat bang tay
                        CHANGEOUTGENERATOR=1
                    elif(binaryoutput[i]=='0' and i<6):
                        #if(IOsetting.modeoutput[i]==1):
                        out=OUT1+i
                        #print("OUTPUT",out)
                        GPIO.output(out,0)
                    elif(binaryoutput[i]=='1' and i==8):
                        OUTGENERATOR=2  #dung may phat bang tay
                        CHANGEOUTGENERATOR=1
                    i+=1
                Beep=1 
        else:
            readreportserver="Rec: "+response
            
    Netsetting.reportserver='Sent: '+str(convertSize(Netsetting.sizedatatoserver))+'. '+readreportserver
    '''if(readreportserver.find("Error")!=-1):
        messagetoserver("status","ERROR")
    else:
        messagetoserver("status","OK")'''
    print(Netsetting.reportserver)
    
#------------------Tao thu muc FTP----------------------
#file_txt_csv="*.csv" or "*.txt"
def creat_directory_ftp12(file_txt_csv):
    try:
        #Truyen file qua FTP, truyen duoc thi xoa file
        if(file_txt_csv=="*.txt"):
            ftp = FTP(Netsetting.serverftp,timeout=30)
            Gsm.reportsms=ftp.login(Netsetting.userftp,Netsetting.passftp)
            print("Login FTP1:"+Gsm.reportsms)
        elif(file_txt_csv=="*.csv"):
            ftp = FTP(Netsetting.serverftp2,timeout=30)
            Gsm.reportsms=ftp.login(Netsetting.userftp2,Netsetting.passftp2)
            print("Login FTP2:"+Gsm.reportsms)
            
        #List ke file trong thu muc, gui file qua FTP, roi xoa file do
        os.chdir("/home/pi/bts/upload/")
        filename_arr={}
        i=0
        for files in glob.glob(file_txt_csv):
            filename_arr[i] = files    
            i=i+1
            length=len(files)
            if(file_txt_csv=="*.txt"):      #KCNDiemThuy20170228145700.txt
                dayftp=str(files[(length-18):(length-10)])
                monthftp="Thang"+str(files[(length-14):(length-12)])
                yearftp=str(files[(length-18):(length-14)])
                if(len(Netsetting.pathftp)==0):
                    nameftp=str(files[0:length-18])
                else:
                    nameftp=Netsetting.pathftp
                    
            elif(file_txt_csv=="*.csv"):    #KCNDiemThuy20170228.csv
                dayftp=str(files[(length-12):(length-4)])
                monthftp="Thang"+str(files[(length-8):(length-6)])
                yearftp=str(files[(length-12):(length-8)])
                if(len(Netsetting.pathftp2)==0):
                    nameftp=str(files[0:length-12])
                else:
                    nameftp=Netsetting.pathftp2
                    
            print("Tach ten file:"+nameftp+"/"+yearftp+"/"+monthftp+"/"+dayftp+":"+files)
            #Gsm.reportsms=nameftp+"/"+yearftp+"/"+monthftp+"/"+dayftp+":"+files
            # Tao thu muc co ten cua thien bi:
            if nameftp in ftp.nlst() : #check if 'Netsetting.hostname' exist inside 'www'
                ftp.cwd(nameftp)    # change into "Netsetting.hostname" directory
                Gsm.reportsms="cwd: "+nameftp
            else : 
                ftp.mkd(nameftp)    #Create a new directory called foo on the server.
                ftp.cwd(nameftp)    # change into 'Netsetting.hostname' directory
                Gsm.reportsms="mkd: "+nameftp
            # Tao thu muc co ten nam YYYY
            if str(yearftp) in ftp.nlst() : #check if 'Year YYYY' exist inside 'name'
                ftp.cwd(str(yearftp))    # change into "now.year" directory
                Gsm.reportsms="cwd: "+str(yearftp)
            else : 
                ftp.mkd(str(yearftp))    #Create a new directory called foo on the server.
                ftp.cwd(str(yearftp))    # change into 'now.year' directory
                Gsm.reportsms="mkd: "+str(yearftp)
            # Tao thu muc co ten thang Month 
            if monthftp in ftp.nlst() : #check if 'thang Month' exist inside 'year'
                ftp.cwd(str(monthftp))    # change into "now.month" directory
                Gsm.reportsms="cwd: "+str(monthftp)
            else : 
                ftp.mkd(str(monthftp))    #Create a new directory called foo on the server.
                ftp.cwd(str(monthftp))    # change into 'now.month' directory
                Gsm.reportsms="mkd: "+str(monthftp)
            # Tao thu muc co ten ngay: ddmmyyyy
            if dayftp  in ftp.nlst() : #check if 'thang Month' exist inside 'month'
                ftp.cwd(str(dayftp))       # change into "now.day" directory
                Gsm.reportsms="cwd: "+str(dayftp)
            else : 
                ftp.mkd(dayftp)        #Create a new directory called foo on the server.
                ftp.cwd(dayftp)        # change into 'now.day' directory
                Gsm.reportsms="mkd: "+str(dayftp)
            print(ftp.retrlines('LIST'))    #list subdirectory contents
            
            # Duong dan toi file du lieu
            path_file_ftp="/home/pi/bts/upload/"+files
            print("List file .txt .csv: "+path_file_ftp)
            # Truyen file
            #fileupload=open(path_file_ftp,'rb')
            #print(fileupload.readlines())
            Gsm.reportsms="FTP12:"+files+" "+ftp.storlines('STOR '+files ,open(path_file_ftp,'rb'))
            #fileupload.close()
            print("Storlines FTP12:"+Gsm.reportsms)
            ftp.sendcmd('cdup')
            ftp.sendcmd('cdup')
            ftp.sendcmd('cdup')
            ftp.sendcmd('cdup')
            #print("List: "+ftp.retrlines('LIST'))    #list subdirectory contents
            # Xoa file
            os.remove(path_file_ftp)
            print(Gsm.reportsms)
    except Exception as e:
        Gsm.reportsms="Error FTP12:"+str(e)
        print(Gsm.reportsms)
    #close connection    
    ftp.quit()
#-------------------------------------------------------
# loop function is kiem tra cac tram co ket noi hay khong
def loop():
    # gives CPU some time before looping again 180 seconds
    global countsec,countmin,Beep, inputstatus, outputstatus,modeoutputstatus,lastsecond,lastminute,lasthour,datetimealarms,looprunning,indexmodbus,indextask,connect485
    global indexvalue,counthour
    global newdatahistory
    try:
        realvalue=0
        data=0
        indextask=0
        # Ghi du lieu History data
        now = datetime.datetime.now()
        if(now.year>2018 and now.month > 5):
            return
        looprunning=1
        indextask=0.1 
        # Kiem tra theo giay
        if(now.second!=lastsecond):
            if(lastsecond>now.second):
                #print('Countsec:',countsec,lastsecond,now.second)
                countsec=countsec+lastsecond-now.second
            else:
                #print('Countsec:',countsec,lastsecond,now.second)
                countsec=countsec+now.second-lastsecond
            lastsecond=now.second
            if(countsec>30):    #20 giay kiem tra tin nhan toi 1 lan
                countsec=0
                # Kiem tra tin nhan toi, dung Huawei E303H
                '''if(sms.connected==True):
                    try:
                        sms.processStoredSms(False)
                        GPIO.output(LEDCONNECT,False)
                    except:
                        GPIO.output(LEDCONNECT,True)
                # TRUY CAP WEB ECAPRO
               
                try:
                    url ="http://ecapro.vn/thiet-bi-giam-sat-canh-bao-nhiet-do-va-do-am-eca-gpis44eth-1-1-900909.html"
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req) as response:
                        the_page = response.read()
                        #print(the_page)
                except Exception as e:
                    Netsetting.reportserver="Not connect internet1:"+str(e)
                    print(Netsetting.reportserver)'''
                indextask=0.2
                # Gui du lieu toi server cu 30 giay 1 lan
                if(IOsetting.alarm):
                    data="ARMING"
                else:
                    data="DISARM"
                try:
                    messagetoserver("status",data)
                except Exception as e:
                    Netsetting.reportserver="Error send to server:"+str(e)
                
        indextask=1         
        # Kiem tra theo phut            
        if(now.minute!=lastminute):
            lastminute=now.minute
            #print("Display led matrix time") String (Reg=0 Time, 1 Alarm)
            for i in range(Set.maxchannel):
                if(Set.functionchannel[i]==6 and Set.typereg[i]==4  and Set.startreg[i]==0 and usbrtu.writefc6[i]==0):
                    usbrtu.writefc6[i]=1
                    usbrtu.writedatafc6[i]=strftime("%A %H:%M %d/%m/%y",localtime())
                    print("Writedatafc6 Time: "+usbrtu.writedatafc6[i])
                    
            #Calculate CPU temperature of Raspberry Pi in Degrees C
            TempCPU = int(open('/sys/class/thermal/thermal_zone0/temp').read()) / 1e3 # Get Raspberry Pi CPU temp
            if(TempCPU <60 and len(Netsetting.reportserver)==0):
                Netsetting.reportserver="Temp CPU: "+str(TempCPU)+" oC"
            elif(TempCPU > 60):
                Netsetting.reportserver="Temp CPU Overheating: "+str(TempCPU)+"oC"
                
            # Gui du lieu *.csv tai thoi diem ket thuc ngay:
            if(now.hour==23 and now.minute==58):
                lasthour=now.hour+1
                counthour=IOsetting.tinfor
                
            # Dem thoi gian Tdelay lap lai bao dong
            if(IOsetting.tdelay>0):
                for i in range(Set.maxchannel):
                    if(alarmth.FlagEventTH[i]>0):
                        Set.tdelaybuff[i]=Set.tdelaybuff[i]+1
                        if(Set.tdelaybuff[i]>IOsetting.tdelay):
                            Set.tdelaybuff[i]=0
                            alarmth.FlagEventTH[i]=0
                        
            countmin=countmin+1
            print("Den phut:",countmin,Set.tupload)
            # Tre giua lan bao dong lien tiep
            '''for i in range(Set.maxchannel):
                alarmth.Tdelay[i]=0'''
            indextask=2.0
            # Thoi gian ghi du lieu SQL
            if(countmin >= Set.tupload):
                countmin=0
                indexvalue=0

                # Kiem tra song di dong
                '''if(sms.connected==True):
                    try:
                        Gsm.csq=sms.signalStrength()
                        if(Gsm.network==None):
                            Gsm.network=sms.GetNetwork()
                    except Exception as e:
                        print("CSQ error:",e)
                        Gsm.csq=0'''
                
                # Luu tru du lieu SQL
                # update 07/04/16
                indextask=2.1 
                newdatahistory=0
                for i in range(Set.maxchannel):
                    print("Write data to sql:",i)
                    try:
                        database_script.insert_history_data(i,Calibration.realvalue[i],usbrtu.status[i])
                        if(Netsetting.reportserver.find("Error database:")!=-1):
                            Netsetting.reportserver="Written database:"+str(i+1)
                    except Exception as e:
                        Netsetting.reportserver="Error database:"+str(i+1)+str(e)
                        print(Netsetting.reportserver)
                newdatahistory=1
                
                indextask=2.2  
                # Truyen file qua giao thuc FTP1
                if(len(Netsetting.serverftp)>0 and len(Netsetting.userftp)>0 and len(Netsetting.passftp)>0):
                    #HUE_20141117003300.txt Tao file
                    file_name_ftp=Netsetting.hostname+strftime("%Y%m%d%H%M%S",localtime())+".txt"
                    path_file_ftp="/home/pi/bts/upload/"+file_name_ftp
                    upload_content=""
                    for i in range(Set.maxchannel):
                        upload_content=upload_content+strftime("%Y%m%d%H%M%S",localtime())+"\t"+str(Set.namechannel[i])+"\t"+str(Calibration.realvalue[i])+"\t"+str(Set.unitreg[i])+"\r\n"
                    f = codecs.open(path_file_ftp, "wb",encoding='utf8')      #f = codecs.open(self.file, "r",encoding='utf8')
                    f.write(upload_content)
                    f.close()
                    print("Write file:"+path_file_ftp)
                    creat_directory_ftp12("*.txt")
                
            # Dieu khien loi ra dieu hoa
            air.CountMin=air.CountMin+1
            air.control()
            # Huy bao dong ra loa
            if(IOsetting.tsiren3buff>0):
                IOsetting.tsiren3buff=IOsetting.tsiren3buff-1
                print("Tsiren:",IOsetting.tsiren3buff)
            if(IOsetting.tsiren3buff==0 and IOsetting.modeoutput[2]==0):
                GPIO.output(OUT3,False)
            
        #Phan canh bao qua mail va sms
        indextask=2.3  
        if(data==0 and IOsetting.alarm and not q.empty()):
            Beep=3
            alarms=""
            alarmone=""
            while(not q.empty()):
                alarmone=q.get()
                alarms=alarms+"\n"+alarmone
                try:
                    database_script.insert_alarm_tablet(alarmone)       # hay bi loi database dan den treo thiet bi
                    if(Netsetting.reportserver.find("Error database alarm:")!=-1):
                        Netsetting.reportserver="Written database alarm"
                except Exception as e:
                    Netsetting.reportserver="Error database alarm:"+str(e)

            indextask=2.4    
            messagetoserver("alarm",alarms)
            try:
                MAIL(Netsetting.hostname+alarms+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880\nhttp://ecapro.com.vn/","Email alarm from ECA-GPIs6.6CE device: "+Netsetting.hostname)
                Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
            except Exception as e:
                Netsetting.reportserver="Error Mail:"+str(e)    #Khac phuc loi khi nhan tin het tien.
            '''for i in range(len(Netsetting.tel)):    #5 so dien thoai
                if(len(Netsetting.tel[i])>=4):
                    if(sms.connected==True and IOsetting.sms):
                        text=Netsetting.hostname+alarms+"\n"+datetimealarms+"\n"+str(Netsetting.ip)+":8880"
                        #print(text) nguyen nhan loi dung quet do dat tieng Viet co dau
                        try:
                            sms.SendSMS(Netsetting.tel[i],text[:159])
                            Gsm.reportsms="Sent SMS"
                        except Exception as e:
                            Gsm.reportsms="Error SMS:"+str(e)'''
            indextask=2.5
            #print("Display led matrix alarm")
            Alarmspk=1
            # Khi co canh bao thi se khong gui du lieu Time ra Led matrix nua. String (Reg=0 Time, 1 Alarm)
            for i in range(Set.maxchannel):
                if(Set.functionchannel[i]==6 and Set.typereg[i]==4 and Set.startreg[i]==1 and usbrtu.writefc6[i]==0):
                    usbrtu.writefc6[i]=1
                    usbrtu.writedatafc6[i]=alarms[:125]
                    indexmodbus=i
                    print("Writedatafc6 Alarm: "+usbrtu.writedatafc6[i])

        indextask=3  
        #-------------------
        if(now.hour!=lasthour):
            lasthour=now.hour
            Beep=1
            # ----Hen gio nhan tin 18/01/16----
            if(IOsetting.tinfor>0):
                counthour=counthour+1
                if(counthour>=IOsetting.tinfor):
                    counthour=0
                    indextask=1.0   # Bao loi ngay 14/10/2016
                    textsms=""
                    if(IOsetting.alarm):
                        textsms=Netsetting.hostname+'\nARMING\n'
                    else:
                        textsms=Netsetting.hostname+'\nDISARM\n'
                    textsms=textsms+"Input : "+bin(inputstatus)[2:].zfill(6)[::-1]+"\n"
                    textsms=textsms+"Output: "+bin(outputstatus)[2:].zfill(6)[::-1]+"\n"
                    for i in range(Set.maxchannel):
                        textsms=textsms+str(Set.namechannel[i])+":"+str(Calibration.realvalue[i])+" "+str(Set.unitreg[i])+"\n"
                    textsms=textsms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880"
                    try:
                        MAIL(textsms,"Email Infor from ECA-GPIs6.6CE device: "+Netsetting.hostname)
                        Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
                    except Exception as e:
                        Netsetting.reportserver="Error Mail:"+str(e)   #Khac phuc loi khi nhan tin het tien.
                        
                    indextask=1.1
                    '''for i in range(len(Netsetting.tel)):    #5 so dien thoai
                        if(len(Netsetting.tel[i])>=4):
                            if(sms.connected==True):
                                try:
                                    sms.SendSMS(Netsetting.tel[i],textsms[:159])
                                    Gsm.reportsms="Sent SMS"
                                    print("Sent SMS")
                                except Exception as e:
                                    Gsm.reportsms="Error SMS"+str(e)
                                    print("Error SMS:",e)'''
                                    
                    # Truyen file qua giao thuc FTP2 file .csv
                    if(len(Netsetting.serverftp2)>0 and len(Netsetting.userftp2)>0 and len(Netsetting.passftp2)>0):
                        #ECA-GPIs66DA20161230.csv
                        # Tao file csv
                        file_name_ftp=Netsetting.hostname+strftime("%Y%m%d",localtime())+".csv"
                        path_file_ftp="/home/pi/bts/upload/"+file_name_ftp
                        path_file_download=str(Netsetting.ip)+":8880/upload/"+file_name_ftp
                        dayy='1'
                        if(IOsetting.tinfor>=12 and IOsetting.tinfor<24):
                            dayy='2'
                        elif(IOsetting.tinfor>=24 and IOsetting.tinfor<48):
                            dayy='3'
                        elif(IOsetting.tinfor>=48):
                            dayy='4' 
                        upload_content=load_history_data_day_attachment2(dayy)
                        if(len(upload_content)>100):
                            #print(upload_content)
                            f = codecs.open(path_file_ftp, "wb",encoding='utf8')      #f = codecs.open(self.file, "r",encoding='utf8')
                            f.write(upload_content)
                            f.close()
                            print("Write file:"+path_file_ftp)
                        #Truyen file qua FTP2, truyen duoc thi xoa file    
                        creat_directory_ftp12("*.csv")
        #-----------------------------------------------------------------------
        # Time | Channel | Value | Status | Input | Output
        # Trang thai cac IO
        inputstatus=GPIO.input(INP1)+2*GPIO.input(INP2)+4*GPIO.input(INP3)+8*GPIO.input(INP4)+16*GPIO.input(INP5)+32*GPIO.input(INP6)
        outputstatus=GPIO.input(OUT1)+2*GPIO.input(OUT2)+4*GPIO.input(OUT3)+8*GPIO.input(OUT4)+16*GPIO.input(OUT5)+32*GPIO.input(OUT6)
        modeoutputstatus=IOsetting.modeoutput[0]+2*IOsetting.modeoutput[1]+4*IOsetting.modeoutput[2]+8*IOsetting.modeoutput[3]+16*IOsetting.modeoutput[4]+\
                          32*IOsetting.modeoutput[5]+64*IOsetting.modeoutput[6]+128*IOsetting.modeoutput[7]

        #print("Gain:"+str(Calibration.gain[indexmodbus]))
        # Phan doc du lieu modbus
        try:
            #for i in range(Set.maxchannel):
            usbrtu.readmodbus(indexmodbus,Set.addchannel[indexmodbus],Set.functionchannel[indexmodbus],Set.startreg[indexmodbus],Set.numberreg[indexmodbus],Set.typereg[indexmodbus])
            if(usbrtu.readdata[indexmodbus]!='inf'):
                Calibration.realvalue[indexmodbus]=round((usbrtu.readdata[indexmodbus]*Calibration.gain[indexmodbus]+Calibration.offset[indexmodbus]),2)    #Calibration.gain[indexmodbus] Calibration.offset[indexmodbus]
            if(usbrtu.status[indexmodbus]>0):
                connect485=connect485+1
                
        except Exception as e:
            webiopi.debug("Error Modbus: "+str(Set.addchannel[indexmodbus])+":"+str(indexmodbus)+":"+str(e)+str(sys.exc_info()[0]))
       
            
        indexmodbus=indexmodbus+1
        if(indexmodbus>=Set.maxchannel):    # Quet het cac dia chi
            indexmodbus=0
            Set.connect=connect485
            connect485=0
            # Su kien canh bao nhiet do,do am
            indextask=4                     # Hay bao loi o vi tri nay
            if(IOsetting.alarm):
                alarmth.Eventtemphumi()
        #------------------------------------------------
        indextask=4.3
        GPIO.output(LEDCONNECT,not GPIO.input(LEDCONNECT))
        looprunning=1
        indextask=5
    #--------------------update 17/12/16------------------------
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        Netsetting.reportserver="Error:"+str(e)+". Line:"+str(exc_tb.tb_lineno)
        print(Netsetting.reportserver)
#---------------------------------------
class AlarmEvents(object):
    def __init__(self):
        self.FlagEventTH=[]
        self.Tdelay=[]
        #self.Tsiren=0
        for i in range(MAXCHANNEL):
            self.FlagEventTH.append(0)     #0 Normal, 1 Alarm
            self.Tdelay.append(1)           #1 tinh bang phut
        GPIO.setup(OUT3, GPIO.OUT)    # Siren
        
    def init(self):                         # Setup output
        GPIO.output(OUT3,False)                 # Siren off
    def finish(self):
        GPIO.output(OUT3,False)
        
    def Eventtemphumi(self):
        global Beep,datetimealarms,indextask
        for i in range(Set.maxchannel):
            #print(i,"> gia tri kenh:",Set.highset,Set.lowset,self.FlagEventTH)
            if(Calibration.realvalue[i]>float(Set.highset[i]) and self.FlagEventTH[i]!=1):
                self.Tdelay[i]=self.Tdelay[i]+1
                if(self.Tdelay[i]>2):
                    q.put(str(Set.meshigh)+"\n"+str(Set.namechannel[i])+": "+str(Calibration.realvalue[i])+">"+str(Set.highset[i])+" "+str(Set.unitreg[i]))
                    datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                    self.FlagEventTH[i]=1
                    usbrtu.status[i]=3
                    IOsetting.tsiren3buff=IOsetting.tsiren3
                    self.Tdelay[i]=0
                    indextask=4.0
            elif(Calibration.realvalue[i]<float(Set.lowset[i]) and self.FlagEventTH[i]!=2):
                self.Tdelay[i]=self.Tdelay[i]+1
                if(self.Tdelay[i]>2):
                    q.put(str(Set.meslow)+"\n"+str(Set.namechannel[i])+": "+str(Calibration.realvalue[i])+"<"+str(Set.lowset[i])+" "+str(Set.unitreg[i]))
                    datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                    self.FlagEventTH[i]=2
                    usbrtu.status[i]=2
                    IOsetting.tsiren3buff=IOsetting.tsiren3
                    self.Tdelay[i]=0
                    indextask=4.1
            elif(Calibration.realvalue[i]>=float(Set.lowset[i]) and Calibration.realvalue[i]<=float(Set.highset[i]) and self.FlagEventTH[i]>0):
                self.Tdelay[i]=self.Tdelay[i]+1
                if(self.Tdelay[i]>2):
                    q.put(str(Set.namechannel[i])+": "+str(Calibration.realvalue[i])+" "+str(Set.unitreg[i]))
                    datetimealarms=strftime("%H:%M:%S, %d/%m/%y",localtime())
                    self.FlagEventTH[i]=0
                    usbrtu.status[i]=1
                    IOsetting.tsiren3buff=0
                    self.Tdelay[i]=0
                    indextask=4.2
            
# Khai bao
alarmth=AlarmEvents()
#---------------------------------------
# Calibration.realvalue[0] nhiet do dieu khien dieu hoa Out12
# Calibration.realvalue[1] do am de dieu khien hut am Out4
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
        #Temp > Set High, Bat toan bo
        if(Calibration.realvalue[0]>IOsetting.temphighon12 and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
            GPIO.output(OUT1,True)
            GPIO.output(OUT2,True)
            self.CHANGEOUT1=1
            self.CHANGEOUT2=1
            # Out4 che do luan phien
            if(IOsetting.modeoutput[3]==1):
                GPIO.output(OUT4,True)
            # Tro ve luan phien khi nhiet do binh thuong
            self.CountMin=IOsetting.tloopout12
            
        #Tem < Set Low, Tat toan bo
        elif((Calibration.realvalue[0]>0 and Calibration.realvalue[0]<IOsetting.templowoff12 or self.Flagoff12==1) and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
            GPIO.output(OUT1,False)
            GPIO.output(OUT2,False)
            self.CHANGEOUT1=1
            self.CHANGEOUT2=1
            # Out4 che do luan phien
            if(IOsetting.modeoutput[3]==1):
                GPIO.output(OUT4,False)
            # Tro ve luan phien khi nhiet do binh thuong
            self.CountMin=IOsetting.tloopout12
            
        #Setlow < Tem < Sethigh
        elif(self.CountMin>IOsetting.tloopout12 and IOsetting.modeoutput[0]==0 and IOsetting.modeoutput[1]==0):
            self.CountMin=0
            self.CountSequence=self.CountSequence+1
            # Luan phien 1 va 2
            if(self.CountSequence==2 and IOsetting.modeoutput[3]==0):
                self.CountSequence=0
            # Luan phien 1,2,4
            elif(self.CountSequence==3 and IOsetting.modeoutput[3]==1):
                self.CountSequence=0
            if(self.CountSequence==0):
                GPIO.output(OUT1,True)
                GPIO.output(OUT2,False)
                self.CHANGEOUT1=1
                self.CHANGEOUT2=1
                # Out4 che do luan phien
                if(IOsetting.modeoutput[3]==1):
                    GPIO.output(OUT4,True)
                
            elif(self.CountSequence==1):
                GPIO.output(OUT1,False)
                GPIO.output(OUT2,True)
                self.CHANGEOUT1=1
                self.CHANGEOUT2=1
                # Out4 che do luan phien
                if(IOsetting.modeoutput[3]==1):
                    GPIO.output(OUT4,True)
                    
            elif(self.CountSequence==2):
                GPIO.output(OUT1,True)
                GPIO.output(OUT2,True)
                self.CHANGEOUT1=1
                self.CHANGEOUT2=1
                # Out4 che do luan phien
                if(IOsetting.modeoutput[3]==1):
                    GPIO.output(OUT4,False)
                
        #Out4 dieu khien theo gia tri kenh 2
        if(Calibration.realvalue[1]>IOsetting.channel2highon4 and IOsetting.modeoutput[3]==0):
            GPIO.output(OUT4,True)
        elif(IOsetting.modeoutput[3]==0):
            GPIO.output(OUT4,False)

        #Out5 dieu khien theo gia tri kenh 3
        if(Calibration.realvalue[2]>IOsetting.channel3highon5 and IOsetting.modeoutput[4]==0):
            GPIO.output(OUT5,True)
        elif(IOsetting.modeoutput[3]==0):
            GPIO.output(OUT5,False)
            
# Setup Output
air=Aircontrol()
#---------------------------------------     
class ModbusRTU(object):
    def __init__(self):
        self.reportmodbus="Start Modbus"
        self.readdata=[]
        self.counterror=[]
        self.status=[]
        self.writefc6=[]
        self.writedatafc6=[]
        self.strdatatable=""
        for i in range(MAXCHANNEL):
            self.readdata.append(0)
            self.status.append(0)       #0 loi, 1 ok connected
            self.counterror.append(0)
            self.writefc6.append(0)     #0 khong ghi, 1 cho phep ghi
            self.writedatafc6.append('')
        #print("Cai dat dulieu =0",self.readdata)    
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
        self.data=0
        try:
            
            # Cài dat gia tri voi FC=06 xuat ra led string fc=16
            if((functionchannel==6 or functionchannel==16) and self.writefc6[indexaddress]==1 and len(self.writedatafc6[indexaddress])):     
                if(typereg==1):
                    print("write_register")
                    self.instrument.write_register(startreg,int(self.writedatafc6[indexaddress]),numberreg,functionchannel,True)
                    self.writefc6[indexaddress]=0 
                    
                elif(typereg==2):
                    print("write_longInt")
                    self.instrument.write_long(startreg,int(self.writedatafc6[indexaddress]),True)
                    self.writefc6[indexaddress]=0 
                elif(typereg==3):
                    print("write_float")
                    self.instrument.write_float(startreg,float(self.writedatafc6[indexaddress]),numberreg)
                    self.writefc6[indexaddress]=0 
                elif(typereg==4):
                    print("write_string")
                    self.writefc6[indexaddress]=0 
                    self.instrument.write_string(startreg,str(self.writedatafc6[indexaddress]),len(self.writedatafc6[indexaddress]))
                    
                elif(typereg==6):
                    print("write_longUint")
                    self.instrument.write_long(startreg,int(self.writedatafc6[indexaddress]),False)
                    self.writefc6[indexaddress]=0
                    
                if(self.status[indexaddress]==0):    
                    self.status[indexaddress]=1
                self.reportmodbus="ModbusW:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.writedatafc6[indexaddress])
                print(self.reportmodbus)
                return 1
            elif(functionchannel==6 and self.writefc6[indexaddress]==0):
                return 0
            
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
                """print("OK read 5 Out2:",self.data)
                if((self.data ==0 and GPIO.input(OUT2)==0) or (self.data>0 and GPIO.input(OUT2)==1)):
                    air.CHANGEOUT2=0"""
                return 1
            
            
            #:const:`False` Unsigned INT16     Unsigned short   0 to 65535
            #:const:`True`  INT16              Short            -32768 to 32767
            elif(Set.typereg[indexaddress]==1):                          
                self.data = self.instrument.read_register(startreg, numberreg,functionchannel,True)
                
            #read_long(registeraddress, functioncode=3, signed=False)
            elif(Set.typereg[indexaddress]==2):                         
                self.data = self.instrument.read_long(startreg,functionchannel, False)
                
            #read_float(registeraddress, functioncode=3, numberOfRegisters=2)
            elif(Set.typereg[indexaddress]==3):                
                self.data = round(self.instrument.read_float(startreg,functionchannel,numberreg),2)
                
            #read_string(registeraddress, numberOfRegisters=16, functioncode=3)
            elif(Set.typereg[indexaddress]==4):                
                self.data = self.instrument.read_string(startreg,numberreg,functionchannel)

            #read_registers(self, registeraddress, numberOfRegisters, functioncode=3):
            elif(Set.typereg[indexaddress]==5):
                print("read_registers")
                self.data = self.instrument.read_registers(startreg,numberreg,functionchannel)

            elif(Set.typereg[indexaddress]==6):
                print("read_Uint16")
                self.data = self.instrument.read_register(startreg, numberreg,functionchannel,False)     
                
            #GPIO.output(LEDERROR,False)
            self.readdata[indexaddress]=self.data
            self.counterror[indexaddress]=0
            # update 06/02/17
            if(IOsetting.alarm==0 and self.status[indexaddress]>1):
                self.status[indexaddress]=1
            if(self.status[indexaddress]==0):
                self.status[indexaddress]=1
                
            self.reportmodbus="ModbusR:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)
            print(self.reportmodbus)
            self.instrument.serial.timeout  = Set.timeout   # seconds
            return self.data
        except Exception as e:
            #GPIO.output(LEDERROR,True)
            #self.open()
            self.reportmodbus="Error Modbus:"+str(address)+"+"+str(startreg)+"+"+str(functionchannel)+"="+str(self.data)+"Co:"+str(self.counterror[indexaddress])+str(e)
            webiopi.debug(self.reportmodbus)
            self.counterror[indexaddress]=self.counterror[indexaddress]+1
            if(self.counterror[indexaddress]>20):
                self.counterror[indexaddress]=0
                if(self.status[indexaddress]>0):   #Co ket noi roi mat ket noi
                    self.status[indexaddress]=0
                print("Error read 10:",address,startreg,self.counterror[indexaddress])
                return 0
            else:
                #Strerror="Error read:"+str(address)+str(self.counterror[indexaddress])+str(e)
                #webiopi.debug(Strerror)
                print("Error read:",address,startreg,indexaddress,self.counterror[indexaddress],e)
                if(self.status[indexaddress]==0):   #Mat ket noi                    
                    self.readdata[indexaddress]=0
                return 0
# Setup USB RS485
usbrtu=ModbusRTU()

#---------Calibration setting--------------
class calisetting(object):
    def __init__(self):
        self.file = "/home/pi/bts/Calisetting.txt"
        self.gain=[]
        self.offset=[]
        self.realvalue=[]
        for i in range(MAXCHANNEL):   
            self.gain.append(1.0)
            self.offset.append(0.0)
            self.realvalue.append(0.0)
            
    def Load_calisetting(self):
        f = codecs.open(self.file, "r",encoding='utf8')
        data=f.read()
        # Close opend file
        f.close()
        strdata=str(data)
        setting=strdata.split('\n')
        if(len(setting)>=MAXCHANNEL*2):
            data=""
            i=0
            for i in range(MAXCHANNEL):  
                self.gain[i]=float(setting[i*2])
                self.offset[i]=float(setting[i*2+1])                              
                data=data+str(self.gain[i])+"\n"
                data=data+str(self.offset[i])+"\n"
                data=data+str(Set.namechannel[i])+"\n"
                data=data+str(usbrtu.readdata[i])+"\n"
                data=data+str(self.realvalue[i])+"\n"
                data=data+str(Set.unitreg[i])+"\n"
            #print("Load Calibration:",data)
        else:
            datawrite=""
            data=""    
            for i in range(MAXCHANNEL):  
                self.gain[i]=1.0
                self.offset[i]=0.0
                datawrite=datawrite+str(self.gain[i])+"\n"
                datawrite=datawrite+str(self.offset[i])+"\n"
            self.Save_calisetting(datawrite)
            print("Default Calibration Setting")
            for i in range(MAXCHANNEL):  
                data=data+str(self.gain[i])+"\n"
                data=data+str(self.offset[i])+"\n"
                data=data+str(Set.namechannel[i])+"\n"
                data=data+str(usbrtu.readdata[i])+"\n"
                data=data+str(self.realvalue[i])+"\n"
                data=data+str(Set.unitreg[i])+"\n"
                            
        return (data)
    
    def Save_calisetting(self,data):
        f = codecs.open(self.file, "w",encoding='utf8')
        f.write(data)
        # Close opend file
        f.close()
        setting=data.split('\n')
        #print (setting)
        data=""
        if(len(setting)>=MAXCHANNEL*2):
            for i in range(MAXCHANNEL):  
                self.gain[i]=float(setting[i*2])
                self.offset[i]=float(setting[i*2+1])
                data=data+str(self.gain[i])+"\n"
                data=data+str(self.offset[i])+"\n"
                data=data+str(Set.namechannel[i])+"\n"
                data=data+str(usbrtu.readdata[i])+"\n"
                data=data+str(self.realvalue[i])+"\n"
                data=data+str(Set.unitreg[i])+"\n"
        print("Saved Calibration Setting")
        return (data)
        
        
#----- Cai dat -----
Calibration=calisetting()
Calibration.Load_calisetting()
# phan truy xuat qua web
@webiopi.macro
def load_calibrationsetting():
    data=Calibration.Load_calisetting()
    return (data)

@webiopi.macro
def save_calibrationsetting(data):
    read=urllib.parse.unquote(data)
    read=read.replace(";", "\n")
    return(Calibration.Save_calisetting(read))

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
        data=data+strftime("%H:%M:%S, %d/%m/%y",localtime())+"\n"+str(get_ip_address('eth0'))+":8880\nhttp://ecapro.com.vn/"
        print(data)
        serial.writeString(data)       # write a string
        
    elif(read.find("Test?")!=-1):
        data="GSM:"+Gsm.network+",CSQ:"+str(Gsm.csq)+"\n"
        data=data+"SMS:"+str(Gsm.reportsms)+"\n"
        data=data+str(Netsetting.reportserver)+"\n"+str(Netsetting.ip)+":8880\nModbus conneted:"+str(Set.connect)+"/"+str(Set.maxchannel)+"\n"+str(version)
        print(data)
        serial.writeString(data)       # write a string
        
    elif(read.find("Setting?")!=-1):
        data="My IP:"+str(get_ip_address('eth0'))+"\n"
        data=data+"Gate:"+str(Netsetting.gateway)+"\n"
        data=data+"Host:"+str(socket.gethostname())+"\n"
        data=data+"Server:"+str(Netsetting.ipserver)+":"+str(Netsetting.portserver)+"\n"        
        print(data)
        serial.writeString(data)       # write a string

    elif(read.find("Temper?")!=-1):
        data=""
        for i in range(Set.maxchannel):
            data=data+str(Set.namechannel[i])+":"+str(Calibration.realvalue[i])+" "+str(Set.unitreg[i])+"\n"
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
        print("Error command HMI420",read)
        serial.writeString("Error command HMI420")       # write a string
#------------------------------------------
# blinking and store history data
from urllib.request import urlretrieve
def blink():
    global Alarmspk,Beep,looprunning,indextask
    lastminute=0
    count=0
    while True:
        now = datetime.datetime.now()
        if(looprunning==1 and now.minute==0): #60 phut kiem tra 1 lan
            looprunning=0
        elif(looprunning==0 and now.minute>10):
            looprunning=1
            webiopi.debug("Error SysNet: "+str(indextask))
            textsms=Netsetting.hostname+'\nError SysNet: '+str(indextask) + '\n'
            textsms=textsms+strftime("%H:%M:%S,%d/%m/%y",localtime())+"\n"+str(Netsetting.ip)+":8880"
            Netsetting.reportserver="Error SysNet: "+str(indextask) + ', '+ Netsetting.reportserver
            try:
                MAIL(textsms,"Email Error from ECA-GPIs6.6CE device: "+Netsetting.hostname)
                #Netsetting.reportserver="Sent Mail"   #Khac phuc loi khi nhan tin het tien.
            except:
                Netsetting.reportserver=Netsetting.reportserver+"Error Mail"   #Khac phuc loi khi nhan tin het tien.
            '''if(sms.connected==True):
                try:
                    sms.SendSMS(Netsetting.tel[0],textsms[:159])
                    #Gsm.reportsms="Sent SMS"
                    print("Sent SMS")
                except Exception as e:
                    Gsm.reportsms="Error SMS"+str(e)
                    print("Error SMS:",e)'''
                           
        # Bat bao dong ra loa
        if(IOsetting.tsiren3buff>0):
            GPIO.output(OUT3,True)
            
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
        # Ket noi HMI420, loi nay hay bi treo
        if (serial.available()):
            try:
                data = serial.readString()        # read available data as string
                IOsetting.reporthmi=data
                HNI420command(data)
            except Exception as e:
                #IOsetting.reporthmi="Error UART!"+str(e)
                #print(IOsetting.reporthmi)
                pass

#---Thu nghiem voi chuc nang MAIL----
def MAIL(mailtext,subject):   
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
    msg['Subject'] = subject
    # Send the message via an SMTP server
    s = smtplib.SMTP(Netsetting.mailserver,int(Netsetting.mailport))
    '''s.ehlo()
    s.starttls()
    s.ehlo'''
    s.login(Netsetting.mailfrom,Netsetting.mailpass)
    s.sendmail(Netsetting.mailfrom, recips, msg.as_string())
    s.quit()
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