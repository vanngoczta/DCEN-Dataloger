import sqlite3
import sys
import os
from time import localtime, strftime
namepicture=""

dbname='/home/pi/bts/database.db'
# database_script
# Tao bang ghi du lieu canh bao
def creat_alarm_tablet():
    with sqlite3.connect(dbname,isolation_level=None) as conn:
        curs=conn.cursor()
        print ("Opened database successfully")
        conn.execute('''CREATE TABLE if not exists alarmdisplay
        (ID INTEGER PRIMARY KEY AUTOINCREMENT,
        tdate DATE,
        ttime TIME,
        event TEXT);''')
        print ("Table alarm created successfully")

# store the event in the database
def insert_alarm_tablet(alarms):
    global namepicture
    with sqlite3.connect(dbname,isolation_level=None) as conn:
        curs=conn.cursor()
        # I used triple quotes so that I could break this string into
        date=strftime("%Y-%m-%d",localtime())
        time=strftime("%H:%M:%S",localtime())
        curs.execute("INSERT INTO alarmdisplay values(null,(?),(?),(?))", (date,time,alarms))
        # commit the changes
        #conn.commit()
        namepicture=date[2:4]+date[5:7]+date[8:10]+time[0:2]+time[3:5]+time[6:8]
#-------------------------------
# Tao bang ghi du lieu history
# status=0 not connnect
# status=1 ok
# status=2 low
# status=3 high
def creat_history_data():
    with sqlite3.connect(dbname,isolation_level=None) as conn:
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
    
# store data in the database ok, number
def insert_history_data(channel,value,status):
    with sqlite3.connect(dbname,isolation_level=None) as conn:
        curs=conn.cursor()
        curs.execute("INSERT INTO historydata values(null,date('now','localtime'),time('now','localtime'),(?),(?),(?))",\
                     (channel,value,status))
        # commit the changes
        #conn.commit()
        
# delete data in the database ok, number
def delete_history_data(days):
    with sqlite3.connect(dbname,isolation_level=None) as conn:
        curs=conn.cursor()
        curs.execute("DELETE FROM historydata WHERE tdate<date('now','localtime','-%s day')" % (days))
