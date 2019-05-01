import urllib3
import json
import os
import time
import board
import busio
import adafruit_sgp30
import Adafruit_DHT
import statistics
import math
from datetime import datetime

printOut=False

def main():
	global printOut
	fileDir = os.path.dirname(os.path.abspath(__file__)) + '/apiConf.json'
	http = urllib3.PoolManager()
	config=Config(fileDir)
	printOut = config.printOut
	sgp30 = InitSgp30()
	dht11 = Adafruit_DHT.DHT11

	cO2List = []
	tempList = []
	humidityList = []
	elapsed_sec = 0
	while True:
		#Alle 6 Sekunden machen wir eine Messung		
		if elapsed_sec % 6 == 0:
			try:
				humidity, temperature = Adafruit_DHT.read_retry(dht11, config.dht11Pin)
				humidity = humidity + config.humidityOffset
				temperature = temperature + config.tempOffset
				sgp30.set_iaq_humidity(ConvertRhToAh(humidity,temperature))
				eCO2, TVOC = sgp30.iaq_measure()
				cO2List.append(eCO2)
				tempList.append(temperature)
				humidityList.append(humidity)
				if printOut:
					print("eCO2 = %d ppm \t TVOC = %d ppb" % (eCO2, TVOC))
					print('Temperature = %d Humidity = %d'%(temperature, humidity))
			except Exception as ex:
				print('Sensor reading error: ' + ex)

		if elapsed_sec % 60 == 0:	

			if printOut:
				eCO2Base, TVOCBase = sgp30.get_iaq_baseline()
				print("**** Base: eCO2 = 0x%x, TVOC = 0x%x"%(eCO2Base, TVOCBase))

			mCo2=statistics.median(cO2List)
			mHumidity= statistics.median(humidityList)
			mTemp = statistics.median(tempList)
			PostToServer(config.piSecret,config.piId,mCo2,mHumidity,mTemp, config.apiUrl, http)
			cO2List.clear()
			tempList.clear()
			humidityList.clear()
		
		time.sleep(1)
		elapsed_sec += 1


def InitSgp30():
	try:
		i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
		sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
		if printOut:
			print("SGP30 serial #", [hex(i) for i in sgp30.serial])
		sgp30.iaq_init()
		sgp30.set_iaq_baseline(0x8973, 0x8aae)
		return sgp30
	except Exception as ex:
		print('SGP30 init error: ' + ex)

def PostToServer(secret,id,eCO2,humidity,temperature, apiUrl,http):
	header = {
		'PiSecret':secret,
		'PiID':id,
		'Content-Type':'application/json'}

	payload = json.dumps({
				"eCO2" : eCO2,
				"humidity" : humidity,
				"temperature" : temperature,
				"dateTimeUTC" : datetime.utcnow().isoformat()})

	try:
		resp = http.request('POST', apiUrl + '/api/airQuality', headers=header, body=payload, timeout = 4.0, retries = 3)
		#resp = requests.post(apiUrl + '/api/airQuality', headers=header, json=payload, verify=False)
		if resp.status != 200:
			print('Request not successful (%d): %s'%(resp.status, json.loads(resp.data.decide('utf-8'))))
		if printOut and resp.status == 200:
			print('Request successful')
	except Exception as ex:
		print('Connection error:',ex)	

def ConvertRhToAh(humidity, temp):
	ah = 216.7 * (((humidity / 100.0) * 6.112 * math.exp((17.62 * temp) / (243.12 + temp))) / (273.15 + temp))
	return ah

class Config:
	def __init__(self, path):
		try:			
			self.CheckCreateConfig(path)
			self.ReadConfig(path)
		except Exception as ex:
			#Die Config ist auf jeden Fall da, da wir sie sonst erzeugt hätten
			#Wenn wir hier landen, muss die Config also defekt sein
			#-> Löschen und neu erzeugen
			os.remove(path)
			self.CheckCreateConfig(path)
			self.ReadConfig(path)

	def ReadConfig(self, path):
		with open(path) as conf_file:
				conf = json.load(conf_file)
				self.piId = conf['PiID']
				self.piSecret = conf['PiSecret']
				self.dht11Pin = conf['Dht11Pin']
				self.tempOffset = conf['TempOffset']
				self.humidityOffset = conf['HumidityOffset']
				self.apiUrl = conf['ApiUrl']
				self.printOut = conf['PrintValues']

	def CheckCreateConfig(self, configPath):
		if not os.path.isfile(configPath):
			defaultConf = {
					"PiSecret" : "-1",
					"PiID" : "-1",
					"Dht11Pin" : 4,
					"TempOffset" : 0,
					"HumidityOffset" : 0,
					"ApiUrl" : "https://mief-is-in-the-air.tk",
					"PrintValues" : False}
			with open(configPath, 'w') as conf_out:
				json.dump(defaultConf, conf_out)

if __name__ == "__main__":
	main()
