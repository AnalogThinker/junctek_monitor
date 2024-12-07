import asyncio
from bleak import BleakClient, BleakScanner

JUNTEK_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

async def connect_juntek(address):
    device = await BleakScanner.find_device_by_address(address)
    if not device:
        print(f"Device with address {address} not found")
        return

    async with BleakClient(device) as client:
        print(f"Connected to {device.name}")
        
        while True:
            try:
                data = await client.read_gatt_char(JUNTEK_UUID)
                decoded_data = data.decode('utf-8')
                parsed_data = parse_juntek_data(decoded_data)
                print_data(parsed_data)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error: {e}")
                break

def parse_juntek_data(data):
    parts = data.split(',')
    return {
        'voltage': float(parts[2]) / 100,
        'current': float(parts[3]) / 100,
        'remaining_capacity': float(parts[4]) / 100,
        'cumulative_capacity': float(parts[5]) / 100,
        'watt_hours': float(parts[6]) / 10000,
        'temperature': float(parts[8]) - 100,
        'output_status': int(parts[10]),
        'current_direction': "Charging" if int(parts[11]) == 0 else "Discharging",
        'battery_life': int(parts[12])
    }

def print_data(data):
    print(f"Voltage: {data['voltage']}V")
    print(f"Current: {data['current']}A")
    print(f"Remaining Capacity: {data['remaining_capacity']}Ah")
    print(f"Cumulative Capacity: {data['cumulative_capacity']}Ah")
    print(f"Watt Hours: {data['watt_hours']}kWh")
    print(f"Temperature: {data['temperature']}°C")
    print(f"Output Status: {data['output_status']}")
    print(f"Current Direction: {data['current_direction']}")
    print(f"Battery Life: {data['battery_life']} minutes")
    print("---")


async def list_gatt_services(address):
    async with BleakClient(address) as client:
        print(f"Connected to {client.address}")
        services = await client.get_services()

        print("\nGATT Services:")
        for service in services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}")
                print(f"    Properties: {', '.join(char.properties)}")
                for descriptor in char.descriptors:
                    print(f"    Descriptor: {descriptor.uuid}")

async def main():
    juntek_address = "XX:XX:XX:XX:XX:XX"  # Replace with your Juntek KL140F's Bluetooth address
    juntek_address = "84:C2:E4:44:59:59"
    await connect_juntek(juntek_address)
    await list_gatt_services(juntek_address)

if __name__ == "__main__":
    asyncio.run(main())

