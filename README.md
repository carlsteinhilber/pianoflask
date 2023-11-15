# pianoflask
A lightweight, flask-based UI for pianobar

# The whys
I have a Raspberry Pi - connected to a Xantech multizone amplifier - that I use to pipe my Pandora stations throughout the house. Long ago I had installed PianoBar - the wonderful console pandora.com music player (https://6xq.net/pianobar/) - to stream my Pandora stations, and had followed several online guides to also install PatioBar web-based UI to control PianoBar from my phone (https://github.com/kylejohnson/Patiobar). But I was never really happy with the solution. PatioBar, with it's NodeJS/React dependencies, seemed overly "heavy" for a Raspberry Pi (beared out by the fact that it would continually crash my Pi) and the UI looked like an early '90's webpage.

So I tinkered to try to build a similar, but much more managible solution using the much lighter Flask framework.

# The hows
PianoFlask utilizes the same eventcmd solution as PatioBar (in fact, it was lifted directly from that project), and a very similar FiFO CTL pipe to control and receive event notification from PianoBar. This all drives Flask's SocketIO library, and presents a clean, modern webpage based on the lightweight Pico CSS framework.

# Installation
There are several online tutorials to install PianoBar/PatioBar, but the basic steps are these:
- Flash a fresh MicroSD card with a new version of Raspberry Pi OS using the Raspberry Pi Imager - I used "Raspbery Pi OS (Legacy) Lite" for my Pi 3B, no need to install the full version with a desktop
  - Before flashing, bring up the advanced options using **Ctrl + Shift + X** and under *Service*, Enable SSH
  - Name the Pi on the first tab of the settings (I just named mine pianoflask)
- Connect your Pi to the network (hardwired is recommended, but WiFi is an option... just configure it in the advanced options in the Imager) and power it on
- SSH into the Pi using PuTTY or other utility
- Expand the Pi's filesystem (this may not be necessary anymore, but it's become habit for me every time I start with a fresh Pi):
```
pi@raspberrypi:~ sudo raspi-config
```
  - Go to Advanced, then Expand File System
- You will likely be prompted to reboot, select 'Yes'
- Once the Pi has restarted and is back online, connect again, then update
```
pi@raspberrypi:~ sudo apt-get update
pi@raspberrypi:~ sudo apt-get upgrade
```
- Reboot again
- Now check the Python version already installed on the Pi
```
pi@raspberrypi:~ python -V
```
  - The system should display a version equal to or higher than 3.9
  - If not, Google how to install a more recent Python version
- You will likely need to install Python 3 Pip
```
pi@raspberrypi:~ sudo apt-get install python3-pip
```
- From here, PianoBar is available via the standard apt repositories, so installation is easy
```
pi@raspberrypi:~ sudo apt install pianobar
```
- We also want to install Screen so pianobar can run without a screen attached
```
pi@raspberrypi:~ sudo apt install screen
```
- Now try running PianoBar to ensure it installed correctly
```
pi@raspberrypi:~ pianobar
```
  - PianoBar will ask for your username/email address and password to your Pandora account
  - Next, it should list all of your current Pandora stations, and prompt you to select one to start playing
- I have a HiFi DAC hat on my Pi which PianoBar did not immediately recognize, so I did not hear any sound. I had to do some configuration based on some documentation specific to my particular hat (for me, it was a HiFiBerry DAC Pro+, so I followed the instructions here: https://www.hifiberry.com/docs/software/configuring-linux-3-18-x/)
- Once configured correctly, I was able to hear the track playing, and control PianoBar from the commandline using the hotkeys described here: https://linux.die.net/man/1/pianobar

Alright, now that PianoBar is installed and functioning properly, time to hook up PianoFlask
- Install Flask
```
pi@raspberrypi:~ pip install flask
```
Add the local bin directory to the system's PATH, as described during the installation
```
pi@raspberrypi:~ export PATH="$HOME/.local/bin:$PATH"
```
- Now install Flask Sockets and the eventlet library
```
pi@raspberrypi:~ pip install flask-socketio
pi@raspberrypi:~ pip install eventlet
```
- Now copy the PianoFlask project to the Pi (either via the git client, or by downloading the zip archive from this repository)
- The project should be copied to a new subdirectory in the Pi's home directory (/home/pi/pianoflask/)
- Create a new config directory for PianoBar
```
pi@raspberrypi:~ mkdir -p ~/.config/pianobar
```
- Edit the sample PianoBar config file that is included in the pianoflask directory
```
pi@raspberrypi:~ sudo nano ~/pianoflask/config.sample
```
  - Edit the *user* and *password* lines to match your Pandora.com login credentials
  - Update the *autostart_station* line to include the ID of the station you want PianoBar to always start on when the system reboots (you can determine the station ID by visiting https://pandora.com, clicking on one of your stations - or create a new one - and then copying everything after the last backslash '\'. ex: if the page for your chosen station is https://www.pandora.com/station/play/**86840530020870280**, then the station ID is '86840530020870280')
  - Save the config file (if you're using nano, **CTRL-O** to save, then **CTRL-X** to exit)
- Copy the config file to the PianoBar config directory, as, simply, 'config'
```
pi@raspberrypi:~ sudo cp ~/pianoflask/config.sample ~/.config/pianobar/config
```

Awesome! PianoFlask should now be installed and read, just a few more housekeeping things to get PianoFlask talking to PianoBar properly.
- First, make the eventcmd.sh file in the pianoflask directory executable
```
pi@raspberrypi:~ sudo chmod 755 ~/pianoflask/eventcmd.sh
```
- Create a FiFo pipe to control PianoBar
```
pi@raspberrypi:~ sudo mkfifo "/home/pi/.config/pianobar/ctl"
```
- Copy the two .service files to the system directory so that PianoBar and PianoFlask both start when the Pi is booting
```
pi@raspberrypi:~ sudo cp pianobar.service /lib/systemd/system/
pi@raspberrypi:~ sudo cp pianoflask.service /lib/systemd/system/
```
- Now hook both of the services up
```
pi@raspberrypi:~ sudo systemctl daemon-reload
pi@raspberrypi:~ sudo systemctl enable pianobar
pi@raspberrypi:~ sudo systemctl enable pianoflask
pi@raspberrypi:~ sudo systemctl start pianobar
pi@raspberrypi:~ sudo systemctl start pianoflask
```
- Give the system one last good reboot
```
pi@raspberrypi:~ sudo reboot
```
- Now, once the Pi is restarted and back online, you should be able to point a web browser on a device/computer on the same network to the Pi's network address, and a nice UI should appear that allows you to control playback of your Pandora tracks.
```
http://<name of your pi>.local:5000 (so, if you named your Pi "pianoflask" like I did above, you would go to http://pianoflask.local:5000
```
  - if that doesn't work, you may need to use the IP address of the Pi (something like http://192.168.1.100:5000) depending on how your network router is set up. If that's the case, you'll want to set up a reserved IP address for your Pi, which, unfortunately, given how many different ways there is to do this on different routers, is beyond the scope of this guide. You'll want to check the documentation for your specific router.
- Once you have the UI up in a web browser
  - Check that all your stations appear in the station dropdown
  - Check that you can pause and play the track
  - The three buttons at the bottom are, from left to right:
    - I dislike this track (broken heart icon - you won't ever hear this track again, unless you reactivate it on pandora.com)
    - I'm tired of this track (calendar icon - will not play this track again for at least a month)
    - I love this track (heart icon - keep playing this track and try to find more like it)

Please note: PianoFlask does not include volume control. This is by design (mine) since my PianoFlask Pi is connected to an amplifier that I can control through a separate web UI. If you would like to have volume control added to *your* PianoFlask installation, contact me and I should be able to provide a brief guide of how to do so. Should be relatively easy.


