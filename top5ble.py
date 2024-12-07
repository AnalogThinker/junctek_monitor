import asyncio
from bleak import BleakScanner

async def scan_ble_devices():
    devices = await BleakScanner.discover(timeout=5)
    return sorted(devices, key=lambda d: d.rssi, reverse=True)[:50]

def print_device_info(device):
    print(f"Name: {device.name or 'Unknown'}")
    print(f"Address: {device.address}")
    print(f"RSSI: {device.rssi} dBm")
    print("---")

async def main():
    print("Scanning for nearby BLE devices...")
    closest_devices = await scan_ble_devices()
    
    print("\nTop 5 closest BLE devices:")
    for device in closest_devices:
        print_device_info(device)

if __name__ == "__main__":
    asyncio.run(main())
