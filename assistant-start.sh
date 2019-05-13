#!/bin/sh

sleep 6
amixer -c 1 sset 'Speaker' 114
python3 /home/pi/action-rgb-led.py &
python3 /home/pi/mensaDeamon.py &
