#!/usr/bin/env python

import asyncio
import json
import argparse
import traceback
import logging
import signal
import time
import yaml

from bleak import BleakScanner, BleakClient, BleakError
import paho.mqtt.publish as publish
import config

#blesniffer
check = {}



class JTData:
    def __init__(self) -> None:
        pass


class JTInfo:

    ADDR = config.JUNTEC_ADDR
    RX_CHARACTERISTIC = "0000fff1-0000-1000-8000-00805f9b34fb"


    def __init__(self) -> None:
        self.data = JTData()
        self.bt_device = None
        self.name = None
        self.addr = self.ADDR
        self.discovery_info_sent = False

    def _add_signal_handlers(self):
        loop = asyncio.get_event_loop()

        async def shutdown(sig):
            """
            Cancel all running async tasks (other than this one) when called.
            By catching asyncio.CancelledError, any running task can perform
            any necessary cleanup when it's cancelled.
            """
            tasks = []
            for task in asyncio.all_tasks(loop):
                if task is not asyncio.current_task(loop):
                    task.cancel()
                    tasks.append(task)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            loop.stop()

        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(sig)))

    def locate_device(self):
        asyncio.run(self._locate_device())

    async def _locate_device(self):
        self.bt_device = await BleakScanner.find_device_by_address(self.addr)
        if self.bt_device is None:
            raise Exception(
                "Couldn't find BLE device - is it in range? is another client connected? "
                + " Check 'hcitool con' and force disconnect if necessary"
            )
        self.name = self.bt_device.name
        self.addr = self.bt_device.address
        logger.info(
            "Located JUNTEK device - name=%s addr=%s",
            self.bt_device.name,
            self.bt_device.address,
        )


    def start_loop(self, interval):
        try:
            asyncio.run(self._query_loop(interval))
        except asyncio.CancelledError:
            logger.info("Caught signal and shutdown.")


    async def _query_loop(self, interval):
        self._add_signal_handlers()

        async with BleakClient(self.bt_device, timeout=20) as client:
            await client.start_notify(self.RX_CHARACTERISTIC, callback=self._callback)
            while True:
                try:
                    if not client.is_connected:
                        logger.warning("No connection...Attempting to reconnect")
                        await client.connect()
                        await client.start_notify(
                            self.RX_CHARACTERISTIC, callback=self._callback
                        )

#                    await client.write_gatt_char(
#                        self.TX_CHARACTERISTIC, self.REQUEST_DATA, False
#                    )

                except EOFError:
                    logger.warning("DBus EOFError")
                except asyncio.exceptions.TimeoutError:
                    logger.warning("asyncio TimeOutError communicating with device")
                except BleakError as err:
                    logger.warning("BleakError - %s", err)
                except Exception as err:
                    logger.warning(
                        f"Error querying Juntek: {err}, {type(err)}"
                        + traceback.format_exc()
                    )

                if not interval:  # one-shot run, don't loop
                    break

                await asyncio.sleep(interval)

    def _callback(self, sender, data):
        logger.debug("DEBUG: DATA=%s", data.hex())






        # BLE_SNIFF PLUG
        #hex_value = "".join(format(x, "02x") for x in value)
        #global result
    #    global check
        bs = str(data.hex()).upper()
        params = {
            "voltage": "C0", # V
            "current": "C1", # A
            "dir_of_current": "D1", # binary
            "ah_remaining": "D2", # Ah
            "discharge": "D3",      # KWh
            "charge": "D4",         # KWh
            "mins_remaining": "D6", #  Min
            "impedance": "D7",           # mΩ
            "power": "D8", # W
            "temp": "D9", # C/F
            "battery_capacity": "B1" # A
        }
        battery_capacity_ah = config.BATT_CAP

        params_keys = list(params.keys())
        params_values = list(params.values())

        # split bs into a list of all values and hex keys
        bs_list = [bs[i:i+2] for i in range(0, len(bs), 2)]

        # reverse the list so that values come after hex params
        bs_list_rev = list(reversed(bs_list))

        values = {}

        # iterate through the list and if a param is found,
        # add it as a key to the dict. The value for that key is a
        # concatenation of all following elements in the list
        # until a non-numeric element appears. This would either
        # be the next param or the beginning hex value.
        for i in range(len(bs_list_rev)-1):
            if bs_list_rev[i] in params_values:
                value_str = ''
                j = i + 1
                while j < len(bs_list_rev) and bs_list_rev[j].isdigit():
                    value_str = bs_list_rev[j] + value_str
                    j += 1

                position = params_values.index(bs_list_rev[i])

                key = params_keys[position]
                values[key] = value_str
        # check if dir_of_current exist if not asign if charging or dischargin exist
        if "dir_of_current" not in values and "charging" not in check:
            if "discharge" in values and "charge" not in values:
                values["dir_of_current"] = "00"
            elif "charge" in values and "discharge" not in values:
                values["dir_of_current"] = "01"

        # now format to the correct decimal place, or perform other formatting
        for key,value in list(values.items()):
            if not value.isdigit():
                del values[key]

            val_int = int(value)
            if key == "dir_of_current":
                if value == "01":
                    check["charging"] = True
                else:
                    check["charging"] = False
            elif key == "voltage":
                self.data.jt_batt_v = values[key] = val_int / 100
            elif key == "current":
                values[key] = val_int / 100
            elif key == "discharge":
                values[key] = val_int / 100000
            elif key == "charge":
                values[key] = val_int / 100000
            elif key == "ah_remaining":
                self.data.jt_ah_remaining = values[key] = val_int / 1000
            elif key == "mins_remaining":
                self.data.jt_min_remaining = values[key] = val_int
            elif key == "impedance":
                values[key] = val_int / 100
            elif key == "power":
                values[key] = val_int / 100
            elif key == "temp":
                self.data.jt_temp = values[key] = val_int - 100
            elif key == "battery_capacity":
                values[key] = val_int / 10

        # Calculate percentage
        if isinstance(battery_capacity_ah, int) and "ah_remaining" in values:
            self.data.jt_soc = soc = values["ah_remaining"] / battery_capacity_ah * 100
            if "soc" not in values or soc != values["soc"]:
                self.data.jt_soc = values["soc"] = soc
        # Update old results with new values
        #result.update(values)


        # Display current as negative numbers if discharging
        if "charging" in check:
            if check["charging"] == False:
                if "current" in values:
                    values["current"] *= -1
                    self.data.jt_current = values["current"]
                if "power" in values:
                    values["power"] *= -1
                    self.data.jt_watts = values["power"]


        logger.debug(values)

#End of BLESNIFF Plug





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
                    entry["expire_after"] = 180
                if not "state_topic" in entry:
                    entry["state_topic"] = f"Juntek-Monitor/{entry['unique_id']}"
                if not "device" in entry:
                    entry["device"] = {"name": "Juntek Monitor", "identifiers": jt.name}

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
        for k, v in jt.data.__dict__.items():
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
jt = JTInfo()
while jt.bt_device is None:
    try:
        jt.locate_device()
    except Exception as err:
        logger.warning(f"Error searching for Juntek: {err}, {type(err)}")
    time.sleep(5)

jt.start_loop(args.interval)
