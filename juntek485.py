#!/usr/bin/env python
import asyncio
import json
import argparse
import traceback
import logging
import signal
import time
import yaml
import serial
import math

import paho.mqtt.publish as publish
import config



class JTData:
    def __init__(self) -> None:
        pass


class JTInfo:
    def __init__(self) -> None:
        self.data = JTData()
        self.discovery_info_sent = False
        self.name = "Juntek Monitor"
        #Capture data from RS485
        with serial.Serial(config.RS485, baudrate=115200, timeout=1) as serialHandle:
            get_values_str = b':R50=1,2,1,\n'
            serialHandle.write(get_values_str)
            byte_string = serialHandle.readline()
            print(byte_string)
        #split CSV
        string = byte_string.decode()
        string = string.strip()
        values = string.split(',')
        #Calculations
        calc_watts = int(values[2])*int(values[3])/10000

        #Formatting the data
        self.data.jt_batt_v = int(values[2])/100
        self.data.jt_current = int(values[3])/100
        self.data.jt_watts = math.ceil(calc_watts*100)/100
        self.data.jt_batt_charging = int(values[11])
        self.data.jt_soc = math.ceil(int(values[4]) / config.BATT_CAP) /10
        self.data.jt_ah_remaining = int(values[4])/1000
        self.data.jt_acc_cap = math.ceil(int(values[6])/1000)/100
        self.data.jt_min_remaining = math.ceil(int(values[7])/60)
        self.data.jt_temp = int(values[8])-100

        #Negative values if Discharging
        if self.data.jt_batt_charging == 0:
            self.data.jt_watts = self.data.jt_watts * -1
            self.data.jt_current = self.data.jt_current * -1

        #Output values on screen
        for k, v in self.data.__dict__.items():
            print(f"{k} = {v}")




#    def publish(self):

        # Publish Home Assistant discovery info to MQTT on first run
        if self.discovery_info_sent is False:
            msg = "Publishing Discovery information to Home Assistant"
            logger.info(msg)

            f = open("jt_mqtt.yaml", "r")
            y = yaml.safe_load(f)
            for entry in y:
                if not "unique_id" in entry:
                    entry["unique_id"] = entry["object_id"] # required for mapping to a device
                if not "platform" in entry:
                    entry["platform"] = "mqtt"
                if not "expire_after" in entry:
                    entry["expire_after"] = 90
                if not "state_topic" in entry:
                    entry["state_topic"] = f"Juntek-Monitor/{entry['unique_id']}"
                if not "device" in entry:
                    entry["device"] = {"name": "Juntek Monitor", "identifiers": "BTG065"}

                logger.debug(
                    f"DISCOVERY_PUB=homeassistant/sensor/{entry['object_id']}/config\n"
                    + "PL={json.dumps(entry)}\n"
                )
                publish.single(
                    topic=f"homeassistant/sensor/{entry['object_id']}/config",
                    payload=json.dumps(entry),
                    retain=True,
                    hostname=config.MQTT_HOST,
                    auth=auth,
                )

            self.discovery_info_sent = True

        # Combine sensor updates for MQTT
        mqtt_msgs = []
        for k, v in self.data.__dict__.items():
            mqtt_msgs.append({"topic": f"Juntek-Monitor/{k}", "payload": v})
            if not args.quiet:
                print(f"{k} = {v}")
        publish.multiple(mqtt_msgs, hostname=config.MQTT_HOST, auth=auth)
        logger.info("Published updated sensor stats to MQTT")





if hasattr(config, "JT_LOG_FILE"):
    logging.basicConfig(
        filename=config.JT_LOG_FILE,
        format="%(asctime)s %(levelname)s:%(message)s",
        encoding="utf-8",
        level=logging.WARNING,
    )
logger = logging.getLogger("Juntek KF Coulometer")
logger.setLevel(logging.INFO)

auth = {"username": config.MQTT_USER, "password": config.MQTT_PASS}

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
parser.add_argument(
    "-i",
    "--interval",
    type=int,
    help="Run nonstop and query the device every <interval> seconds",
)
parser.add_argument(
    "-q", "--quiet", action="store_true", help="Quiet mode. No output except for errors"
)
args = parser.parse_args()


if args.debug:
    logger.warning("Setting logging level to DEBUG")
    logger.setLevel(logging.DEBUG)

if not args.quiet:
    logger.addHandler(logging.StreamHandler())


logger.info("Starting up")

while True:
    try:
        jt = JTInfo()
    except Exception as e:
        print(f"Error occured: {e}")
    time.sleep(5)
