#!/bin/sh

procs_running=$(ps -ef| grep -c apiSensor)


if [ "$procs_running" -lt 2 ];
then
   date  
   echo 'started'  
   python3 /home/pi/mief/apiSensor.py 
  
fi
