#!/bin/bash

mkdir /home/pi/mief
cd /home/pi/mief

git clone https://github.com/adafruit/Adafruit_Python_DHT.git && cd Adafruit_Python_DHT
sudo python3 setup.py install

cd ..

wget -O apiSensor.py https://raw.githubusercontent.com/Paul-Weisser/mief-is-in-the-script/master/apiSensor.py
wget -O runMiefSensor.sh https://raw.githubusercontent.com/Paul-Weisser/mief-is-in-the-script/master/runMiefSensor.sh 

chmod +x runMiefSensor.sh

currentcron=$(crontab -l | grep mief)

if [[ $currentcron == *"runMiefSensor"* ]]; then
	echo "Job used to run Mief-Sensor has already been installed, skipping!"
else
	crontab -l > currentcrontab
	echo "* * * * * /home/pi/mief/runMiefSensor.sh >> /home/pi/mief/joblog.txt" >> currentcrontab
        crontab currentcrontab
	rm currentcrontab	
	echo "created job"
fi

