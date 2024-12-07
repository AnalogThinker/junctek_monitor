import asyncio
# import bluetooth
from bleak import BleakClient

JUNTEK_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
#JUNTEK_UUID = "ae656aea-86c2-d654-f73b-d3f9cc15a9d6"

async def read_juntek_data(address):
    async with BleakClient(address) as client:
        while True:
            try:
                data = await client.read_gatt_char(JUNTEK_UUID)
                decoded_data = data.decode('utf-8')
                voltage, current, power = parse_juntek_data(decoded_data)
                print(f"Voltage: {voltage}V, Current: {current}A, Power: {power}W")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error: {e}")
                break

def parse_juntek_data(data):
    # Parse the data string based on Juntek's protocol
    # This is a simplified example and may need adjustment
    parts = data.split(',')
    voltage = float(parts[0])
    current = float(parts[1])
    power = float(parts[2])
    return voltage, current, power

def main():
    #juntek_address = "XX:XX:XX:XX:XX:XX"  # Replace with your Juntek device's Bluetooth address
    juntek_address = "84:C2:E4:44:59:59"  # Replace with your Juntek device's Bluetooth address

    asyncio.run(read_juntek_data(juntek_address))

if __name__ == "__main__":
    main()
