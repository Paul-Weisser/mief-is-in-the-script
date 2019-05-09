#!/bin/bash

sudo date -s "$(curl -s "http://worldtimeapi.org/api/timezone/Europe/Berlin.txt" | grep "^datetime" | sed "s/.* \(.*\)/\1/")"

sudo raspi-config noint do_i2c 0

mkdir /home/pi/mief
cd /home/pi/mief

sudo apt-get install build-essential python-dev python-openssl git
git clone https://github.com/adafruit/Adafruit_Python_DHT.git && cd Adafruit_Python_DHT
sudo python setup.py install

cd ..

read -p "Enter PiId provided by the homepage(can be changed in the config): "  id
read -p "Enter ApiSecret provided by the homepage(can be changed in the config): "  secret

wget -O apiSensor.py https://raw.githubusercontent.com/Paul-Weisser/mief-is-in-the-script/master/apiSensor.py
wget -O runMiefSensor.sh https://raw.githubusercontent.com/Paul-Weisser/mief-is-in-the-script/master/runMiefSensor.sh 

chmod +x runMiefSensor.sh

python3 apiSensor.py $id $secret

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

