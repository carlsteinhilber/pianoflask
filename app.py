import atexit
import eventlet
# eventlet.monkey_patch()

from flask import *
from flask_socketio import *

import io
import json
import os
from os.path import dirname, abspath, join
import psutil
import re
import sys
import threading
import time


async_mode = None

# Init the server
app = Flask(__name__,
        static_url_path='', 
        static_folder='static',
        template_folder='templates')

app.config['SECRET_KEY'] = 'some super secret key!'
# socketio = SocketIO(app, logger=True)
socketio = SocketIO(app, async_mode=async_mode)

ACTIVE_DEBUG=False

filenameNowplaying = "trackinfo.json"
filenameStationlist = "stations.json"

# nowplayingPath = '/home/pi/.config/pianobar/'+nowplayingFileName
# stationlistPath = '/home/pi/.config/pianobar/'+stationlistFileName


## HELPER FUNCTIONS
# left() - pythonized string left
def left(s, amount):
    return s[:amount]

## mid() - pythonized string mid
def mid(s, offset, amount):
    return s[offset:offset+amount]

## debug_log() - print to console (turn off for production)
def debug_log(msg):
    if(ACTIVE_DEBUG):
        print(msg)
    return True

def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def secondsToTimeString(inSeconds):
    hours = str((inSeconds / (60 * 60)) % 24).split(".")[0].zfill(2)
    minutes = str((inSeconds / (60) % 60)).split(".")[0].zfill(2)
    seconds = str((inSeconds) % 60).split(".")[0].zfill(2)
    return ( hours + ":" + minutes + ":" + seconds )


##############################################
# Pianobar Class
# a class to interface with Pianobar
##############################################

class Pianobar:
    def __init__(self):

        debug_log('initializing class')

        self._processname = 'pianobar'

        self.paths = {}
        self.paths["config"] = "/home/pi/.config/" + self._processname
        self.paths["fifo"] = self.paths["config"] + "/ctl"
        self.paths["nowplaying"] = (self.paths["config"] + "/"+filenameNowplaying)
        self.paths["stationlist"] = (self.paths["config"] + "/"+filenameStationlist)

        self.paused = False

        self.running = False

        self.stationlist = []

        self.track = {}
        self.track["pausedtime"] = 0
        self.track["pausedstart"] = None
        self.track["duration"] = 0
        self.track["info"] = {}
        self.track["elapsedtime"] = 0
        self.track["starttime"] = None


    def isRunning(self):
        # Iterate over the all the running process
        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if self._processname.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def start(self):
        debug_log('checking for pianobar process')
        # Check that Pianobar is already running
        self.running = self.isRunning()
        debug_log(f'process found: {self.running}')

        # get most recent track
        self.setTrackInfo(self.readNowPlaying())
        # debug_log(self.track["info"])

        # get most recent list of stations
        self.stationlist = self.readStationList()
        # debug_log(self.stations)


        startWithPausedSong = False

        if startWithPausedSong:
            self.writeFifo(command = 'S')
            self.paused = True
        else:
            self.writeFifo(command = 'P')
            self.paused = False

        self.track["pausedtime"] = 0
        self.track["pausedstart"] = None
        self.track["starttime"] = self.track["info"]["started"]
        self.track["duration"] = self.track["info"]["songDuration"]
        self.track["elapsedtime"] = time.time() - self.track["info"]["started"]

        return self.running
        
    def getEmptyTrackInfo(self):
        return {
                "artist": "Unknown",
                "title": "Unknown",
                "album": "Unknown",
                "coverArt": '/images/unknown-track.jpg',
                "stationName": "",
                "songStationName": "",
                "pRet": 1,
                "pRetStr": "",
                "wRet": 0,
                "wRetStr": "r",
                "songDuration": 0,
                "songPlayed": 0,
                "rating": 0,
                "detailUrl": "",
                "started": 0 }

    def getProgress(self):
        elapsedTime = self.getTrackElapsedTime()
        duration = self.track["duration"]
        if elapsedTime > duration:
            elapsedTime = duration
        progress = {            
            "elapsed" : secondsToTimeString(elapsedTime),
            "elapsedSec" : int(elapsedTime),
            "duration" : secondsToTimeString(duration),
            "durationSec" : int(duration),
            "percent" : "%.0f%%" % ((elapsedTime/duration) * 100)
        }
        return progress

    def getStationList(self):
        return self.stationlist

    def getTrackDuration(self):
        return self.track["duration"]

    def getTrackElapsedTime(self):
        if self.running and not self.paused:
            self.track["elapsedtime"] = (time.time() - self.track["starttime"]) - self.track["pausedtime"]
        return self.track["elapsedtime"]
    
    def getTrackInfo(self):
        return self.track["info"]

    def isPaused(self):
        return self.paused

    def pause(self):
        if self.running and not self.paused:
            if self.writeFifo(command = 'S'):
                self.track["pausedstart"] = time.time()
                self.paused = True
                return True
        return False

    def resume(self):
        if self.running and self.paused:
            if self.writeFifo(command = 'P'):
                if self.track["pausedstart"] is None:
                    self.track["pausedstart"] = time.time()
                # keep adding the amount of paused time
                self.track["pausedtime"] += time.time() - self.track["pausedstart"]
                self.paused = False
                return True
        return False
    
    def readNowPlaying(self):
        trackInfo = self.getEmptyTrackInfo()
        try:
            f = open(self.paths["nowplaying"],'r')
            nowplayingFile = json.load(f)
            f.close()
            if(len(nowplayingFile)>0):
                trackInfo = nowplayingFile
        except Exception as error:
            print("Could not read nowplaying data")
            print(error)

        return trackInfo

    def readStationList(self):
        stationsInfo = []
        try:
            f = open(self.paths["stationlist"],'r')
            stationlistFile = json.load(f)
            f.close()
            if( len(stationlistFile) > 0 ):
                stationsInfo = stationlistFile["stations"]
        except Exception as error:
            print("Could not read stationlist data")
            print(error)

        return stationsInfo        
    
    def setTrackInfo(self,trackinfo):

        self.track["info"] = trackinfo
        # self.track["info"]["coverArt"] = '/images/unknown-track.jpg'
        if len(trackinfo["coverArt"].strip()) < 1:
            self.track["info"]["coverArt"] = '/images/unknown-track.jpg'

        self.track["pausedtime"] = 0
        self.track["pausedstart"] = None
        self.track["starttime"] = trackinfo["started"]
        self.track["duration"] = trackinfo["songDuration"]
        self.track["elapsedtime"] = 0


        
        return trackinfo
    
    def songban(self):
        if self.running:
            if self.writeFifo(command = '-'):
                return True
        return False

    def songlove(self):
        if self.running:
            if self.writeFifo(command = '+'):
                return True
        return False

    def songnext(self):
        if self.running:
            if self.writeFifo(command = 'n'):
                return True
        return False

    def songtired(self):
        if self.running:
            if self.writeFifo(command = 't'):
                return True
        return False

    def stationchange(self, id):
        if self.running:
            command = "s" + str(int(id)) + "\n"
            if self.writeFifo(command = command):
                return True
        return False

    def writeFifo(self, command):
        #Write a command to the pianobar FIFO
        fifoSuccess = False
        
        if self.running:
            debug_log("sending FIFO command: " + command)
            try:
                fifo_w = open(self.paths["fifo"], 'w')
                fifo_w.write(command)
                fifo_w.close()
                fifoSuccess = True
            except:
                print("could not send command to ctl fifo")
        
        return fifoSuccess


def updateProgressBar():
    socketio.emit('updateprogress', pianobar.getProgress())
#     threading.Timer(1, updateProgressBar).start()

pianobar = Pianobar()
pianobar.start()

@socketio.on('pause')   
def songpause_received(data):
    if pianobar.pause():   
        emit('commandsuccessfull', data, broadcast=True)
    
@socketio.on('resume')   
def songresume_received(data):
    if pianobar.resume():   
        emit('commandsuccessfull', data, broadcast=True)

@socketio.on('songban')   
def songban_received(data):
    if pianobar.songban():
        emit('commandsuccessfull', data, broadcast=True)

@socketio.on('songlove')   
def songban_received(data):
    if pianobar.songlove(): 
        emit('commandsuccessfull', data, broadcast=True)    

@socketio.on('songnext')   
def songnext_received(data):
    if pianobar.songnext():
        emit('commandsuccessfull', data, broadcast=True)
    
@socketio.on('songtired')   
def songban_received(data):
    if pianobar.songtired():   
        emit('commandsuccessfull', data, broadcast=True)

@socketio.on('stationchange')   
def stationchange_received(data):
    if pianobar.stationchange(data["id"]):   
        emit('commandsuccessfull', data, broadcast=True)

    

# threading.Timer(1, updateProgressBar).start()
@socketio.on('getprogress')   
def getprogress_received(data):
    socketio.emit('updateprogress', pianobar.getProgress())


# Receive a message from the front end HTML
@socketio.on('send_message')   
def message_received(data):
    print(data['text'])
    emit('message_from_server', {'text':data['text']}, broadcast=True)

@socketio.on('trackchanged')   
def updatesong_received(data):
    pianobar.setTrackInfo(data["trackinfo"])   
    emit('updatetrack', data, broadcast=True)

@app.route('/images/<path:path>')
def send_image(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    debug_log("/")
    time.sleep(1)
    
    isRunning = pianobar.isRunning()
    isPaused = pianobar.isPaused()

    if isRunning:
    
        # nowPlaying = pianobar.getNowPlaying()
        # stations = pianobar.getStations()

        # print(nowPlaying)


        return render_template('pianoflask.html',
            pianobarrunning = isRunning,
            pianobarpaused = isPaused,
            progress = pianobar.getProgress(),
            trackinfo = pianobar.getTrackInfo(),
            stationlist = pianobar.getStationList(),
            async_mode = socketio.async_mode)
    else:
        return render_template('failed.html',
            pianobarrunning = isRunning,
            async_mode = socketio.async_mode)


# Actually Start the App
if __name__ == '__main__':
    socketio.run(app, debug=False,host='0.0.0.0')