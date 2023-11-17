# PianoFlask
A lightweight, flask-based UI for pianobar

# The whys
I have a Raspberry Pi - connected to a Xantech multizone amplifier - that I use to pipe my Pandora stations throughout the house. Long ago I had installed PianoBar - the wonderful console pandora.com music player (https://6xq.net/pianobar/) - to stream my Pandora stations, and had followed several online guides to also install PatioBar web-based UI to control PianoBar from my phone (https://github.com/kylejohnson/Patiobar). But I was never really happy with the solution. PatioBar, with it's NodeJS/React dependencies, seemed overly "heavy" for a Raspberry Pi (beared out by the fact that it would continually crash my Pi) and the UI looked like an early '90's webpage.

So I tinkered to try to build a similar, but much more managible solution using the much lighter Flask framework.

# The hows
PianoFlask utilizes the same eventcmd solution as PatioBar (in fact, it was lifted directly from that project), and a very similar FiFO CTL pipe to control and receive event notification from PianoBar. This all drives Flask's SocketIO library, and presents a clean, modern webpage based on the lightweight Pico CSS framework.

# Installation

## Preparing the SD card

- Flash a fresh MicroSD card with a new version of Raspberry Pi OS using the Raspberry Pi Imager
  - I used "Raspbery Pi OS (Legacy) Lite" for my Pi 3B, no need to install the full version with a desktop
  - Before flashing, bring up the advanced options using **Ctrl + Shift + X**:
    -  Under *General*
      - tick the checkbox next to "Set hostname" and give your Pi a name (this will be the easiest way to access the UI online, so name it something you'll remember, ex: "pianoflask")
      - tick the checkbox next to "Set username and password - leave Username set to "pi", but set a unique password you can remember
    -  Under *Service*
      - tick the checkbox next to "Enable SSH", and leave it set to "Use password authentication"

- Connect your Pi to the network (hardwired is recommended, but WiFi is an option... just configure on the *General* tab in the Imager, as above) and power it on
- SSH into the Pi using PuTTY or other utility

(all SSH instructions assume you are logged in as the "pi" user, and are in the "pi" user's home directory... type `cd ~` at any time if you're unsure, you should see a prompt like `pi@pianoflask:~` when you're logged in)

- Expand the Pi's filesystem (this may not be necessary anymore, but it's become habit for me every time I start with a fresh Pi):
```
sudo raspi-config
```
> Go to Advanced, then Expand File System

- You will likely be prompted to reboot, select 'Yes'
- Once the Pi has restarted and is back online, connect again, then update
```
sudo apt-get update && sudo apt-get upgrade
```
> this should take several minutes

- Reboot again

- Now check the Python version already installed on the Pi
```
python -V
```
> Python 3.9.2
- The system should display a version equal to or higher than 3.9
  - If not, Google how to install a more recent Python version

- You will likely need to install Python 3 Pip
```
sudo apt-get install python3-pip
```

## Installing PianoBar

There are several online tutorials to install PianoBar/PatioBar, but the basic steps are these:

- PianoBar is available via the standard Raspberry Pi apt repositories, so installation is easy
```
sudo apt install pianobar
```

That's it! At this point, if your Pi is not already hooked up to speakers or a headset, do that now.
Then try running PianoBar to ensure it installed correctly
```
pianobar
```
- PianoBar will ask for your username/email address and password to your Pandora account
- Next, it should list all of your current Pandora stations, and prompt you to select one by typing the station number from the list
- PianoBar will take a few seconds, tell you which track it has selected, and then begin playing
  - I have a HiFi DAC hat on my Pi which PianoBar did not immediately recognize, so I did not hear any sound. I had to do some configuration based on some documentation specific to my particular hat (for me, it was a HiFiBerry DAC Pro+, so I followed the instructions here: https://www.hifiberry.com/docs/software/configuring-linux-3-18-x/)
- check that you can
  - toggle the pausing of the track either by hitting the 'p' key or the spacebar
  - change stations by hitting the 's' key
  - quit pianobar either with the 'q' or '/' keys
  - additional commandline controls using the hotkeys described here: https://linux.die.net/man/1/pianobar

## Installing PianoFlask

Alright, now that PianoBar is installed and functioning properly, time to hook up PianoFlask

- Install Flask
```
pip install flask
```
- Add the local bin directory to the system's PATH, as described during the installation
```
export PATH="$HOME/.local/bin:$PATH"
```
- Now install Flask Sockets, the eventlet library, and psutils
```
pip install flask-socketio
pip install eventlet
pip install psutil
```
You'll need to grab PianoFlask from this repository somehow. You can do this in one of several ways:
- You can use git
```
sudo apt install git
git clone https://github.com/carlsteinhilber/pianoflask.git`
```
- You can pull the zip file down to your Pi, and then unzip the files into a new pianoflask directory
```
wget https://github.com/carlsteinhilber/pianoflask/archive/refs/heads/main.zip
mkdir pianoflask
unzip main.zip  && mv pianoflask-main/* pianoflask
```

## Hook PianoFlask up to PianoBar

Awesome! PianoFlask should now be installed and ready, just a few more housekeeping things to get PianoFlask talking to PianoBar properly.

- Create a new config directory for PianoBar
```
mkdir -p ~/.config/pianobar
```
- Copy the sample config file from the PianoFlask directory into the new config directory
```
sudo cp ~/pianoflask/config.sample ~/.config/pianobar/config
```
- Now edit the config file (I will be using Nano as my editor, you can use whatever you are most familiar with)
```
sudo nano ~/.config/pianobar/config
```
- Edit the *user* and *password* lines to match your Pandora.com login credentials
- Update the *autostart_station* line to include the ID of the station you want PianoBar to always start on when the system reboots
  - you can determine the station ID by visiting https://pandora.com, clicking on one of your stations - or create a new one - and then copying everything after the last backslash '\'.
  - ex: if the page for your chosen station is https://www.pandora.com/station/play/86840530020870280, then the station ID is '86840530020870280'

- Save the config file (if you're using nano, **CTRL-O** to save, then **CTRL-X** to exit)

- make the eventcmd.sh file in the pianoflask directory executable
```
sudo chmod 755 ~/pianoflask/eventcmd.sh
```
- Create a FiFo pipe to control PianoBar, and make it writable
```
sudo mkfifo "/home/pi/.config/pianobar/ctl"
sudo chmod 766 ~/.config/pianobar/ctl
```

- Copy the two .service files to the system directory so that PianoBar and PianoFlask both start when the Pi is booting
```
sudo cp ~/pianoflask/pianobar.service /lib/systemd/system/
sudo cp ~/pianoflask/pianoflask.service /lib/systemd/system/
```
- Now hook both of the services up
```
sudo systemctl daemon-reload
sudo systemctl enable pianobar
sudo systemctl enable pianoflask
sudo systemctl start pianobar
sudo systemctl start pianoflask
```
- Give the system one last good reboot
```
sudo reboot
```

## Using PianoFlask

Once the Pi has restarted and back online, if your speakers/headphones are still connected, you will hear PianoBar start up without any prompts, and begin playing a track from the station you specified in the ~/.config/pianobar/config file as the *autostart_station*
- If you do not hear a track start to play, you may want to double confirm this *autostart_station* setting in the config file

If everything has worked correctly, Piano*Flask* should have started automatically as well
- you should be able to point a web browser on a device/computer on the same network to the Pi's network address, and a nice UI should appear that allows you to control playback of your Pandora tracks.
```
http://pianoflask.local:5000
```
> (if you named your Pi something other than "pianoflask" while you were flashing the SD card, replace "pianoflask" in the link above with whatever name you gave your Pi)

- if that doesn't work, you may need to use the IP address of the Pi (something like http://192.168.1.100:5000) depending on how your network router is set up. If that's the case, you'll want to set up a reserved IP address for your Pi, which, unfortunately, given how many different ways there are to do this on different routers, is beyond the scope of this guide. You'll want to check the documentation for your specific router.

- Once you have the UI up in a web browser
  - Check that all your stations appear in the station dropdown
  - Check that you can pause and play the track
  - The three buttons at the bottom are, from left to right:
    - I dislike this track (broken heart icon - you won't ever hear this track again, unless you reactivate it on pandora.com)
    - I'm tired of this track (calendar icon - will not play this track again for at least a month)
    - I love this track (heart icon - keep playing this track and try to find more like it)

Please note: PianoFlask does not include volume control. This is by design (mine) since my PianoFlask Pi is connected to an amplifier that I can control through a separate web UI. If you would like to have volume control added to *your* PianoFlask installation, contact me and I should be able to provide a brief guide of how to do so. Should be relatively easy.


