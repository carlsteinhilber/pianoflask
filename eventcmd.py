#!/usr/bin/env python

# a python-based pianobar event handler
import json
import os
from os.path import expanduser, join, isfile
from pathlib import Path
import requests
import socketio
import sys
import time


socket = socketio.Client()

trackinfoFileName = "trackinfo.json"
stationsFileName = "stations.json"

socketActive = False
try:
    socket.connect('http://0.0.0.0:5000')
    socketActive = True
except:
    print("server not connected")
    socketActive = False

path = os.environ.get('XDG_CONFIG_HOME')
if not path:
    path = expanduser("~/.config")
else:
    path = expanduser(path)

trackinfoPath = join(path, 'pianobar', trackinfoFileName)
stationsPath = join(path, 'pianobar', stationsFileName)

trackFileExists = False
if os.path.isfile(trackinfoPath):
    trackFileExists = True

stationsFileExists = False
if os.path.isfile(stationsPath):
    stationsFileExists = True


info = sys.stdin.readlines()
cmd = sys.argv[1]

# if socketActive:
#     sio.emit('eventcmd', cmd)

regPath = join(path, 'pianobar', cmd+".json")

if cmd == 'songstart':
    trackinfo = {
        "artist":"",
        "title":"",
        "album":"",
        "coverArt":"",
        "stationName":"",
        "songStationName":"",
        "pRet":0,
        "pRetStr":"",
        "wRet":0,
        "wRetStr":"",
        "songDuration":0,
        "songPlayed":0,
        "rating":0,
        "detailUrl":"",
        "started": int(time.time())
    }
    
    stationinfo = {
        "stationCount":0,
        "stations":[]
    }    
    receivedData = False
    for line in info:

        # reads each line and trims of extra the spaces 
        # and gives only the valid words
        command, description = line.strip().split('=', 1)

        if(command == "stationCount"):
            receivedData = True
            if(description.isnumeric()):
                stationinfo[command] = int(description.strip())
            else:
                stationinfo[command] = description.strip()
        elif(command == "stationName"):
            receivedData = True
            trackinfo[command] = description.strip()
        elif(command[:7] == "station"):
            receivedData = True
            stationNumber = command[7:].strip()
            if(stationNumber.isnumeric()):
                stationinfo["stations"].append({"id":int(stationNumber),"name":description.strip()})
            else:
                trackinfo[command] = description.strip()
        else:
            receivedData = True
            if(command in ['pRet','wRet','songDuration','songPlayed','rating'] and description.isnumeric()):
                trackinfo[command] = int(description.strip())
            else:
                trackinfo[command] = description.strip()

    if(receivedData):

        songData = {}
        if trackFileExists:
            trackinfoRead = open(trackinfoPath, 'r')
            try:
                songData = json.load(trackinfoRead)
            except:
                print("could not load existing song data")
            trackinfoRead.close()

        if songData != trackinfo:
            dataSuccess = False
            if socketActive:
                try:
                    socket.emit('trackchanged', {'trackinfo' : trackinfo } )
                    dataSuccess = True
                except Exception as error:
                    print("Could not send socket data to server")
                    # print(error)

                if not dataSuccess:
                    try:
                        url = 'http://127.0.0.1:5000/updatetrack'
                        x = requests.post(url, json=trackinfo)
                        dataSuccess = True
                    except Exception as error:
                        print("Could not send send post data")
                        # print(error)

            trackinfoWrite = open(trackinfoPath, 'w')
            try:
                json.dump(trackinfo, trackinfoWrite, indent = 4, sort_keys = False)
            except Exception as error:
                print("Could not write to track file")
                # print(error)
            trackinfoWrite.close()

        stationData = {}
        if stationsFileExists:
            stationsRead = open(stationsPath,'r')
            try:
                stationData = json.load(stationsRead)
            except:
                print("could not load existing station data")

            stationsRead.close()

        if stationData != stationinfo:
            dataSuccess = False
            if socketActive:
                try:
                    socket.emit('changestations', {'stationinfo': stationinfo } )
                    dataSuccess = True
                except Exception as error:
                    print("Could send socket data to server")
                    # print(error)

                if not dataSuccess:
                    try:
                        url = 'http://127.0.0.1:5000/updatestations'
                        x = requests.post(url, json=stationinfo)
                        dataSuccess = True
                    except Exception as error:
                        print("Could send send post data")
                        # print(error)

            stationsWrite = open(stationsPath, 'w')
            try:
                json.dump(stationinfo, stationsWrite, indent = 4, sort_keys = False)
            except Exception as error:
                print("Could not write to stations file")
                # print(error)
            stationsWrite.close()
else:
    regPath
    regFile = open(regPath, 'w')
    json.dump({"command": cmd, "data": info}, regFile, indent = 4, sort_keys = False)
    regFile.close()

if socketActive:
    time.sleep(1)
    socket.disconnect()
    socketActive = False
    
