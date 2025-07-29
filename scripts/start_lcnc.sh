#! /bin/bash
# script to start linuxcnc with the correct configuration

gio launch /home/micross/Desktop/xytable.desktop
#sleep 2

#set the niceness (priority) of the linuxcnc processes to -20 to prevent watchdog timeouts
ps axo pid,comm | grep linuxcnc | grep -o "[0-9]*" | while read -r line ; do
	sudo renice -n -20 -p $line
done
