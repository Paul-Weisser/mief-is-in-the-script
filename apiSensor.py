import requests
import json
import os
import time
import board
import busio
import adafruit_sgp30
import Adafruit_DHT
from datetime import datetime

fileDir = os.path.dirname(os.path.abspath(__file__))
if not os.path.isfile(fileDir + '/apiConf.json'):
	defaultConf = {
			"PiSecret" : "-1",
			"PiID" : "-1",
			"Dht11Pin" : 4,
			"TempOffset" : 0,
			"HumidityOffset" : 0,
			"ApiUrl" : "https://mief-is-in-the-air.tk",
			"PrintValues" : False}
	with open(fileDir + '/apiConf.json', 'w') as conf_out:
	    json.dump(defaultConf, conf_out)

with open(fileDir + '/apiConf.json') as conf_file:
	conf = json.load(conf_file)
	piId = conf['PiID']
	piSecret = conf['PiSecret']
	dht11Pin = conf['Dht11Pin']
	tempOffset = conf['TempOffset']
	humidityOffset = conf['HumidityOffset']
	apiUrl = conf['ApiUrl']
	printOut = conf['PrintValues']

header = {
	'PiSecret':piSecret,
	'PiID':piId,
	'Content-Type':'application/json'
}
try:
	i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
	sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
	if printOut:
		print("SGP30 serial #", [hex(i) for i in sgp30.serial])
	sgp30.iaq_init()
	sgp30.set_iaq_baseline(0x8973, 0x8aae)
except Exception as ex:
	print('SGP30 init error')

elapsed_sec = 0
while True:
	eCO2, TVOC = sgp30.iaq_measure()
	if printOut:
		print("eCO2 = %d ppm \t TVOC = %d ppb" % (eCO2, TVOC))
	time.sleep(1)
	elapsed_sec += 1
	if elapsed_sec % 10 == 0:
		eCO2Base, TVOCBase = sgp30.get_iaq_baseline()
		#sgp30.set_iaq_baseline(eCO2Base,TVOCBase)
		#eCO2Base = sgp30.baseline_eCO2
		#TVOCBase = sgp30.baseline_TVOC
		if printOut:
			print("**** Base: eCO2 = 0x%x, TVOC = 0x%x"%(eCO2Base, TVOCBase))
	if elapsed_sec % 60 == 0:
            try:
                    dht11 = Adafruit_DHT.DHT11
                    humidity, temperature = Adafruit_DHT.read_retry(dht11, dht11Pin)
                    humidity = humidity + humidityOffset
                    temperature = temperature + tempOffset
                    if printOut:
                            print('Temperature: %d Humidity: %d'%(temperature, humidity))
            except Exception as ex:
                    print('DHT11 reading error')

            payload = {
                    "eCO2" : eCO2,
                    "humidity" : humidity,
                    "temperature" : temperature,
                    "dateTimeUTC" : datetime.utcnow().isoformat()
            }

            try:
                    resp = requests.post(apiUrl + '/api/airQuality', headers=header, json=payload, verify=False)
                    if resp.status_code != requests.codes.ok:
                            print('Request not successful (%d): %s'%(resp.status_code, resp.json()))
                    if printOut and resp.status_code == requests.codes.ok:
                            print('Request successful')
            except Exception as ex:
                    print('Connection error:',ex)


