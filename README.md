# This is a Python project that allows to read the Data from Juntek / Junctek / Koolertron Battery Monitor (KG KF series).
Acquisition can be done:
- Through Bluetooth (Not recommended, highly unreliable, random updates as the devices streams)
- Through RS485 (using a shield, or a RS485 to USB)

The data is then published on MQTT.

Please note this is a quick'n'dirty code made at 11PM and first time on Python, so it could use some improvements I'm sure, but it works.

## INSTALL :
Download/Clone the code and create a Python virtual environment in the src directory
'''
$ python -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
'''

Edit the config.py file. Add your MQTT information, and the MAC address for your module. You can use one of the various BLE scanner apps available on your phone to find the address.

Test the script to see if it is working. If everything is good, it will publish MQTT autodiscovery info to Home Assistant, and you should see a new device under the MQTT integration.

There are 2 Python scripts, one for BT, the other one for RS485
   ```
   $ ./BTjuntek.py --debug
   $ ./juntek485.py --debug
   ```

If everything works, you can run the script as a systemd service, for continous updates.

Edit the paths of 'WorkingDirectory' and 'ExecStart' in the ha-jt.service file to match your installation
Copy the ha-jt.service file to /etc/systemd/system/
Enable the service to start on boot

   ```
   $ sudo systemctl daemon-reload
   $ sudo systemctl enable ha-jt.service
   ```

Start the service
   ```
   $ sudo systemctl start ha-jt.service
   ```


## License

GPLv3



## Credits :
I heavily used ard00d's code for the Renogy : https://github.com/ard00d/renogy-bt2-ha-ble
The bottom of this post was key to understand the format : https://community.home-assistant.io/t/home-assistant-tasmota-wemos-mini-r1-battery-meter-kg140f/473969/17
The Manual from the Manufacturer also helped a lot : http://68.168.132.244/KG-F_EN_manual.pdf
