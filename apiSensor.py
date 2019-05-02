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
import logging
from datetime import datetime


def main():
	#Logger config setzen
	global logger
	logging.basicConfig(filename='mief.log')
	logger = logging.getLogger("MiefLogger")
	logger.setLevel(logging.DEBUG)
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	logger.addHandler(ch)

	#Verzeichnis für die Config setzen und Config laden
	fileDir = os.path.dirname(os.path.abspath(__file__)) + '/apiConf.json'
	config=Config(fileDir)
	#Log-Level setzten
	if not config.debugMode:
		logger.setLevel(logging.WARNING)
	#PoolManager für die https requestes erstellen
	http = urllib3.PoolManager()
	#Init Sensoren
	sgp30 = InitSgp30()
	dht11 = Adafruit_DHT.DHT11
	#Listen für den Median erstellen
	cO2List = []
	tempList = []
	humidityList = []
	elapsed_sec = 0
	while True:
		#Alle 6 Sekunden machen wir eine Messung		
		if elapsed_sec % 6 == 0:
			try:
				#Temperatur und Feuchtigkeit auslesen
				humidity, temperature = Adafruit_DHT.read_retry(dht11, config.dht11Pin)
				#Offsets verechnen
				humidity = humidity + config.humidityOffset
				temperature = temperature + config.tempOffset
				#Absolute Feuchtigkeit setzen zur kompensierung 
				aHumidity = ConvertRhToAh(humidity,temperature)
				sgp30.set_iaq_humidity(aHumidity)
				#CO2 auslesen
				eCO2, TVOC = sgp30.iaq_measure()
				#Alle Werte den Listen adden
				cO2List.append(eCO2)
				tempList.append(temperature)
				humidityList.append(humidity)
				#Werte loggen
				logger.info("Values:\n\teCO2 = %d ppm\n\tTVOC = %d ppb\n\tTemperature = %d °C\n\tHumidity = %d %%\n\tAbsolute humidity = %f g/m³"%(eCO2, TVOC,temperature, humidity,aHumidity))
			except Exception as ex:
				logger.error("Sensor reading error:", str(ex))

		#Einmal die Minute die Daten an den Server pushen
		if elapsed_sec % 60 == 0:
			#Baseline loggen
			if config.debugMode:
				eCO2Base, TVOCBase = sgp30.get_iaq_baseline()
				logger.debug("Baseline:\n\teCO2 = 0x%x\n\tTVOC = 0x%x"%(eCO2Base, TVOCBase))
			#Median der Werte berechnen
			mCo2=statistics.median(cO2List)
			mHumidity= statistics.median(humidityList)
			mTemp = statistics.median(tempList)
			logger.info("Push to Server:\n\teCO2 = %d ppm\n\tTemperature = %d °C\n\tHumidity %d %%"%(mCo2, mTemp, mHumidity))
			PostToServer(config.piSecret,config.piId,mCo2,mHumidity,mTemp, config.apiUrl, http)
			#Alle Listen wieder zurücksetzen
			cO2List.clear()
			tempList.clear()
			humidityList.clear()
		#Eine Sekunde warten
		time.sleep(1)
		elapsed_sec += 1

def InitSgp30():
	try:
		i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
		sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
		logger.debug("SGP30 serial: #" + "".join([hex(i) for i in sgp30.serial]))
		sgp30.iaq_init()
		sgp30.set_iaq_baseline(0x8973, 0x8aae)
		return sgp30
	except Exception as ex:
		logger.error("SGP30 init error:", str(ex))

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
		if resp.status != 200:
			logger.warning("Request not successful (%d): %s"%(resp.status, json.loads(resp.data.decode('utf-8'))))
		if resp.status == 200:
			logger.info("Request successful")
	except Exception as ex:
		logger.error("Connection error:", str(ex))	

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
			logger.error("Create config error:", str(ex))
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
				self.debugMode = conf['DebugMode']

	def CheckCreateConfig(self, configPath):
		if not os.path.isfile(configPath):
			defaultConf = {
					"PiSecret" : "-1",
					"PiID" : "-1",
					"Dht11Pin" : 4,
					"TempOffset" : 0,
					"HumidityOffset" : 0,
					"ApiUrl" : "https://mief-is-in-the-air.tk",
					"DebugMode" : False}
			with open(configPath, 'w') as conf_out:
				json.dump(defaultConf, conf_out)

if __name__ == "__main__":
	main()
