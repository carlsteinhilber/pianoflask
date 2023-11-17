import atexit
import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, disconnect
import io
import json
import os
from os.path import dirname, abspath, join
import psutil
import re
import sys
import time

async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

connected_clients={}

ACTIVE_DEBUG=False

appnamespace = "/pianoflask"

pianobarOnFlag = 0

currentSong = {'filepath':'/home/pi/.config/pianobar/nowplaying','lastmodified':0}
stationList = {'filepath':'/home/pi/.config/pianobar/stations','lastmodified':0}

crappyGlobalCSTimestamp = 0


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

##############################################
# Pianobar Class
##############################################

class Pianobar:
    def __init__(self):
        #FIFO location
        self.processname = 'pianobar'
        self.configpath = "/home/pi/.config/pianobar"
        self.fifo = self.configpath + "/ctl"
        self.nowplaying = {'filepath':(self.configpath + "/nowplaying"),'lastmodified':0}
        self.stations = {'filepath':(self.configpath + "/stations"),'lastmodified':0}
        self.running = False
        # TODO: need a better solution, here... if piano flask is started while pianobar is
        # puased, this will be out of sync
        self.paused = False 

    def isRunning(self):
        # Iterate over the all the running process
        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if self.processname.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
        
    def start(self):
        debug_log('Checking for pianobar')
        # Check that Pianobar is already running
        self.running = self.isRunning()
        return self.running

    def stop(self):
        debug_log('Stopping pianobar')
        # Send q command to kill pianobar
        self.writeFifo(command = 'q')

    def checkForUpdates(self):
        fileStatus = {'nowplaying':False, 'stations':False }
        # fileStatus = dict([('currentSong', False), ('stationList', False)])

        nowPlayingTS = os.path.getmtime(self.nowplaying["filepath"])
        stationsTS = os.path.getmtime(self.stations["filepath"])

        if nowPlayingTS != self.nowplaying["lastmodified"]:
            fileStatus["nowplaying"] = True
            self.nowplaying["lastmodified"] = nowPlayingTS
        if stationsTS != self.stations["lastmodified"]:
            fileStatus["stations"] = True
            self.stations["lastmodified"] = stationsTS
        return fileStatus

    def getPaused(self):
        return self.paused

    def setPaused(self,paused):
        self.paused = paused

    def getStations(self):
        stationsProcessed = []
        file1 = open(self.stations["filepath"], "r+")
        fileContents = file1.readlines()
        file1.close()
        for station in fileContents:
            stationSpecs = station.split(':')
            stationsId = stationSpecs[0].strip()
            stationsName = rreplace(stationSpecs[1].replace('\n', ''),'Radio','',1).strip()
            stationsProcessed.append({'id':stationsId, 'name':stationsName })
        return stationsProcessed        

    def getNowPlaying(self):
        nowPlaying = {'artist':"",'track':"", 'album':"", 'image':"", 'rating':"", 'station':""}
        file1 = open(self.nowplaying["filepath"], "r+")
        fileContents = file1.readlines()
        file1.close()
        # print("*****FILESPECS*****")
        # print(fileContents)
        trackSpecs = fileContents[0].split(',,,')
        if len(trackSpecs) > 5:
            nowPlaying = {
                'artist':trackSpecs[0].strip(),
                'track':trackSpecs[1].strip(),
                'album':trackSpecs[2].strip(),
                'image':trackSpecs[3].strip(),
                'rating':trackSpecs[4].strip(),
                'station': rreplace(trackSpecs[5].replace('\n', ''),'Radio','',1).strip()
            }
        return nowPlaying

    def writeFifo(self, command):
        #Write a command to the pianobar FIFO
        fifo_w = open(self.fifo, 'w')
        fifo_w.write(command)
        fifo_w.close()
        return True


pianobar = Pianobar()
pianobar.start()

# goodbye() - register an exit event
@atexit.register
def goodbye():
    debug_log("CALL goodbye")

# pianoflask_get_now_playing() - get the now playing info (current song/track)
@socketio.on('get_now_playing', namespace=appnamespace)
def pianoflask_get_now_playing():
    debug_log("CALL pianoflask_get_now_playing")
    nowPlaying = pianobar.getNowPlaying()
    emit('set_now_playing', nowPlaying, broadcast=True)


# pianoflask_check_for_updates() - check if either the now playing or station info has been updated
@socketio.on('check_for_updates', namespace=appnamespace)
def pianoflask_check_for_updates(message):
    debug_log("CALL pianoflask_check_for_updates")
    fileUpdates = pianobar.checkForUpdates()
    if fileUpdates["nowplaying"] or fileUpdates["stations"]:
        # I think it will be bad for this next emit to be "broadcast" to all clients
        emit('file_event', fileUpdates)
        

# pianoflask_send_fifo() - send the specified command out through the FiFo pipe
# if there is an ID (typically specifying the station in a change station command) then include a newline feed
@socketio.on('send_fifo', namespace=appnamespace)
def pianoflask_send_fifo(message):
    debug_log("CALL pianoflask_send_fifo")
    command = message["command"]
    if "id" in message:
        command = message["command"] + str(int(message["id"])) + "\n"
    debug_log(command)
    if pianobar.writeFifo(command):
        if command == "S":
            pianobar.setPaused(True)
        if command == "P":
            pianobar.setPaused(False)
        emit('fifo_successfull', {"command":command}, broadcast=True)



# pianoflask_connect() - client has connected to socket
@socketio.on('connect', namespace=appnamespace)
def pianoflask_connect():
    print("CALL pianoflask_connect")

# pianoflask_disconnect() - client has disconnected from socket
@socketio.on('disconnect', namespace=appnamespace)
def pianoflask_disconnect():
    print("CALL pianoflask_disconnect")

# pianoflask_disconnect_request() - client has requested to disconnect
# had to create this stub to solve some issues calling disconnect directly (TODO: research direct disconnect issues)
@socketio.on('disconnect_request', namespace=appnamespace)
def pianoflask_disconnect_request(message):
    print("CALL pianoflask_disconnect_request")


@app.route('/')
def index():
    debug_log("/")
    time.sleep(1)
    
    isRunning = pianobar.isRunning()
    isPaused = pianobar.getPaused()

    if isRunning:
        nowPlaying = pianobar.getNowPlaying()
        stations = pianobar.getStations()

        return render_template('pianoflask.html',
                           pianobarrunning=isRunning,
                           pianobarpaused = isPaused,
                           nowplaying=nowPlaying,
                           stations=stations,
                           async_mode=socketio.async_mode)
    else:
        return render_template('failed.html',
                           pianobarrunning=isRunning,
                           async_mode=socketio.async_mode)

if __name__ == '__main__':
    socketio.run(app, debug=False,host='0.0.0.0')