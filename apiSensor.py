#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import sys
from datetime import datetime


def main():
    # Working Dir
    working_dir = os.path.dirname(os.path.abspath(__file__))

    # Logger config setzen
    global logger
    logging.basicConfig(filename=working_dir + '/mief.log')
    logger = logging.getLogger("MiefLogger")
    logger.setLevel(logging.DEBUG)

    # Consolen Ausgabe anhängen
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    # Verzeichnis für die Config setzen und Config laden
    config = Config(working_dir + '/apiConf.json')

    # Falls wir commandline Parameter an der Stelle haben übernehmen wir das in die Config
    if len(sys.argv) == 3:
        pi_id = sys.argv[1]
        pi_secret = sys.argv[2]
        logger.info("PiId and PiSecret are set from commandline:\n\tPiID = %s\n\tPiSecret = %s" % (pi_id, pi_secret))
        config.set_id_and_secret(pi_id, pi_secret)
        logger.info("exit script")
        sys.exit(0)

    # Log-Level setzten
    if not config.debugMode:
        logger.setLevel(logging.WARNING)

    # PoolManager für die https requests erstellen
    http = urllib3.PoolManager()

    # Init Sensoren
    sgp30 = init_sgp30(config.eCO2Base, config.tVOCBase)
    dht11 = Adafruit_DHT.DHT11

    # Listen für den Median erstellen
    co2_list = []
    temp_list = []
    humidity_list = []
    elapsed_sec = 0

    while True:
        # Alle 6 Sekunden machen wir eine Messung
        if elapsed_sec % 6 == 0:
            try:
                # Temperatur und Feuchtigkeit auslesen
                humidity, temperature = Adafruit_DHT.read_retry(dht11, config.dht11Pin)

                # Offsets verrechnen
                humidity = humidity + config.humidityOffset
                temperature = temperature + config.tempOffset

                # Absolute Feuchtigkeit setzen zur Kompensierung
                a_humidity = convert_rh_to_ah(humidity, temperature)
                sgp30.set_iaq_humidity(a_humidity)

                # CO2 auslesen
                eco2, tvoc = sgp30.iaq_measure()

                # Alle Werte den Listen hinzufügen
                co2_list.append(eco2)
                temp_list.append(temperature)
                humidity_list.append(humidity)

                # Werte loggen
                logger.info(
                    "Values:\n\teCO2 = %d ppm\n\tTVOC = %d ppb\n\tTemperature = %d °C\n\tHumidity = %d %%\n\tAbsolute humidity = %f g/m³" % (
                        eco2, tvoc, temperature, humidity, a_humidity))
            except Exception:
                logger.error("Sensor reading error:", exc_info=True)

        # Einmal die Minute die Daten an den Server pushen
        if elapsed_sec % 60 == 0:
            # Read Baseline
            eco2_base, tvoc_base = sgp30.get_iaq_baseline()

            # Save Baseline
            try:
                config.set_base_line(eco2_base, tvoc_base)

                # Baseline loggen
                logger.debug("Baseline:\n\teCO2 = 0x%x\n\tTVOC = 0x%x" % (eco2_base, tvoc_base))
            except Exception:
                logger.warning("Could not save Baseline")

            # Median der Werte berechnen
            m_co2 = statistics.median(co2_list)
            m_humidity = statistics.median(humidity_list)
            m_temp = statistics.median(temp_list)
            logger.info("Push to Server:\n\teCO2 = %.2f ppm\n\tTemperature = %.2f °C\n\tHumidity %.2f %%" % (
                m_co2, m_temp, m_humidity))
            post_to_server(config.piSecret, config.piId, m_co2, m_humidity, m_temp, config.apiUrl, http)

            # Alle Listen wieder zurücksetzen
            co2_list.clear()
            temp_list.clear()
            humidity_list.clear()

        # Eine Sekunde warten
        time.sleep(1)
        elapsed_sec += 1


def init_sgp30(eco2_base, tvoc_base):
    try:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
        sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
        logger.debug("SGP30 serial: #" + "".join([hex(i) for i in sgp30.serial]))
        sgp30.iaq_init()
        logger.debug("Set Baseline:\n\teCO2 = 0x%x\n\tTVOC = 0x%x" % (eco2_base, tvoc_base))
        sgp30.set_iaq_baseline(eco2_base, tvoc_base)
        return sgp30
    except Exception:
        logger.error("SGP30 init error:", exc_info=True)


def post_to_server(secret, id, eco2, humidity, temperature, api_url, http):
    header = {
        'PiSecret': secret,
        'PiID': id,
        'Content-Type': 'application/json'}

    payload = json.dumps({
        "eCO2": eco2,
        "humidity": humidity,
        "temperature": temperature,
        "dateTimeUTC": datetime.utcnow().isoformat()})

    try:
        resp = http.request('POST', api_url + '/api/airQuality', headers=header, body=payload, timeout=4.0, retries=3)
        if resp.status != 200:
            logger.warning("Request not successful (%d): %s" % (resp.status, json.loads(resp.data.decode('utf-8'))))
        if resp.status == 200:
            logger.info("Request successful")
    except Exception:
        logger.error("Connection error", exc_info=True)


def convert_rh_to_ah(humidity, temp):
    return 216.7 * (((humidity / 100.0) * 6.112 * math.exp((17.62 * temp) / (243.12 + temp))) / (273.15 + temp))


class Config(object):
    __eco2_base_default = 0x8973
    __tvoc_base_default = 0x8aae

    __slots__ = ['piId', 'piSecret', 'dht11Pin', 'tempOffset', 'humidityOffset', 'apiUrl', 'debugMode', 'eCO2Base',
                 'tVOCBase','configPath']

    def __init__(self, config_path):
        self.piId = None
        self.piSecret = None
        self.dht11Pin = None
        self.tempOffset = None
        self.humidityOffset = None
        self.apiUrl = None
        self.debugMode = None
        self.eCO2Base = None
        self.tVOCBase = None
        self.configPath = None

        try:
            self.configPath = config_path
            if not os.path.isfile(config_path):
                self.write_config(config_path, "-1", "-1", 4, 0, 0, "https://mief-is-in-the-air.tk", False, Config.__eco2_base_default, Config.__tvoc_base_default)
            self.read_config(config_path)
        except Exception:
            # Die Config ist auf jeden Fall da, da wir sie sonst erzeugt hätten
            # Wenn wir hier landen, muss die Config also defekt sein
            # -> Neu erzeugen
            logger.error("Create config error:", exc_info=True)
            logger.info("Override old broken config!")
            self.write_config(config_path, "-1", "-1", 4, 0, 0, "https://mief-is-in-the-air.tk", False, Config.__eco2_base_default, Config.__tvoc_base_default)
            self.read_config(config_path)

    def read_config(self, path):
        with open(path) as conf_file:
            conf = json.load(conf_file)
            self.piId = conf['PiID']
            self.piSecret = conf['PiSecret']
            self.dht11Pin = conf['Dht11Pin']
            self.tempOffset = conf['TempOffset']
            self.humidityOffset = conf['HumidityOffset']
            self.apiUrl = conf['ApiUrl']
            self.debugMode = conf['DebugMode']
            self.eCO2Base = conf['ECO2Base']
            self.tVOCBase = conf['TVOCBase']

    @staticmethod
    def write_config(config_path, pi_secret, pi_id, dht11pin, temp_off, humidity_off, api_url, debug_mode, eco2_base, tvoc_base):
        default_conf = {
            "PiSecret": pi_secret,
            "PiID": pi_id,
            "Dht11Pin": dht11pin,
            "TempOffset": temp_off,
            "HumidityOffset": humidity_off,
            "ApiUrl": api_url,
            "DebugMode": debug_mode,
            "ECO2Base": eco2_base,
            "TVOCBase": tvoc_base
        }

        with open(config_path, 'w') as conf_out:
            json.dump(default_conf, conf_out)

    def set_base_line(self, eco2_base, tvoc_base):
        self.write_config(self.configPath, self.piSecret, self.piId, self.dht11Pin, self.tempOffset,
                          self.humidityOffset, self.apiUrl, self.debugMode, eco2_base, tvoc_base)

    def set_id_and_secret(self, pi_id, pi_secret):
        try:
            self.write_config(self.configPath, pi_secret, pi_id, self.dht11Pin, self.tempOffset, self.humidityOffset,
                              self.apiUrl, self.debugMode, self.eCO2Base, self.tVOCBase)
            self.read_config(self.configPath)
        except Exception:
            logger.error("Setting PiId or PiSecret failed:", exc_info=True)


if __name__ == "__main__":
    main()
