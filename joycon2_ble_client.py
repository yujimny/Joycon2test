import asyncio
import struct
import sys
import warnings
import argparse
from bleak import BleakScanner, BleakClient
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice

# Suppress FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

# Joycon2 Manufacturer ID
JOYCON2_MANUFACTURER_ID = 0x0553

# Service and Characteristic UUIDs
WRITE_CHARACTERISTIC_UUID = "649d4ac9-8eb7-4e6c-af44-1ea54fe5f005"
SUBSCRIBE_CHARACTERISTIC_UUID = "ab7de9be-89fe-49ad-828f-118f09df7fd2"

def to_int16(b, offset):
    return struct.unpack_from("<h", b, offset)[0]

def to_uint16(b, offset):
    return struct.unpack_from("<H", b, offset)[0]

def parse_stick(data, offset):
    # Joy-Con stick is 12bit packed
    d = data[offset:offset+3]
    val = int.from_bytes(d, "little")
    x = val & 0xFFF
    y = (val >> 12) & 0xFFF
    return x, y

def parse_joycon2_data(data):
    """Parse Joycon2 data"""
    parsed = {
        "PacketID": int.from_bytes(data[0x00:0x03], "little"),
        "Buttons": int.from_bytes(data[0x03:0x07], "little"),

        "LeftStick": parse_stick(data, 0x0A),
        "RightStick": parse_stick(data, 0x0D),

        "MouseX": to_int16(data, 0x10),
        "MouseY": to_int16(data, 0x12),
        "MouseUnk": to_int16(data, 0x14),
        "MouseDistance": to_int16(data, 0x16),

        "MagX": to_int16(data, 0x18),
        "MagY": to_int16(data, 0x1A),
        "MagZ": to_int16(data, 0x1C),

        "BatteryVoltageRaw": to_uint16(data, 0x1F),  # 1000 = 1V
        "BatteryCurrentRaw": to_int16(data, 0x28),   # 100 = 1mA

        "TemperatureRaw": to_int16(data, 0x2E),
        "AccelX": to_int16(data, 0x30),
        "AccelY": to_int16(data, 0x32),
        "AccelZ": to_int16(data, 0x34),

        "GyroX": to_int16(data, 0x36),
        "GyroY": to_int16(data, 0x38),
        "GyroZ": to_int16(data, 0x3A),

        "TriggerL": data[0x3C],
        "TriggerR": data[0x3D],
    }

    # Add converted values
    parsed["BatteryVoltage(V)"] = parsed["BatteryVoltageRaw"] / 1000.0
    parsed["BatteryCurrent(mA)"] = parsed["BatteryCurrentRaw"] / 100.0
    parsed["Temperature(°C)"] = 25 + parsed["TemperatureRaw"] / 127.0

    return parsed

# Global variables to store previous mouse position
last_mouse_x = 0
last_mouse_y = 0

def parse_buttons(buttons):
    """Parse button states"""
    button_names = []
    
    # Button bitmask definitions
    button_masks = {
        0x80000000: "ZL",
        0x40000000: "L",
        0x00010000: "SELECT",
        0x00080000: "LS",
        0x01000000: "↓",
        0x02000000: "↑",
        0x04000000: "→",
        0x08000000: "←",
        0x00200000: "CAMERA",
        0x10000000: "SR(L)",
        0x20000000: "SL(L)",
        0x00100000: "HOME",
        0x00400000: "CHAT",
        0x00020000: "START",
        0x00001000: "SR(R)",
        0x00002000: "SL(R)",
        0x00004000: "R",
        0x00008000: "ZR",
        0x00040000: "RS",
        0x00000100: "Y",
        0x00000200: "X",
        0x00000400: "B",
        0x00000800: "A"
    }
    
    for mask, name in button_masks.items():
        if buttons & mask:
            button_names.append(name)
    
    return button_names

def print_parsed_data(parsed):
    """Display parsed data"""
    global last_mouse_x, last_mouse_y
    
    # Calculate mouse movement delta
    mouse_delta_x = parsed['MouseX'] - last_mouse_x
    mouse_delta_y = parsed['MouseY'] - last_mouse_y
    
    # Save current values
    last_mouse_x = parsed['MouseX']
    last_mouse_y = parsed['MouseY']
    
    # Parse button states
    button_names = parse_buttons(parsed['Buttons'])
    
    print("\n" + "="*50)
    print("Joycon2 Data:")
    print("="*50)
    
    # Display important data with priority
    print(f"PacketID: {parsed['PacketID']}")
    print(f"Buttons: {parsed['Buttons']:08X}")
    if button_names:
        print(f"Pressed: {', '.join(button_names)}")
    else:
        print("Pressed: None")
    print(f"LeftStick: X={parsed['LeftStick'][0]}, Y={parsed['LeftStick'][1]}")
    print(f"RightStick: X={parsed['RightStick'][0]}, Y={parsed['RightStick'][1]}")
    print(f"Mouse: X={parsed['MouseX']}, Y={parsed['MouseY']}, DeltaX={mouse_delta_x}, DeltaY={mouse_delta_y}, Unk={parsed['MouseUnk']}, Distance={parsed['MouseDistance']}")
    print(f"Mag: X={parsed['MagX']}, Y={parsed['MagY']}, Z={parsed['MagZ']}")
    print(f"Accel: X={parsed['AccelX']}, Y={parsed['AccelY']}, Z={parsed['AccelZ']}")
    print(f"Gyro: X={parsed['GyroX']}, Y={parsed['GyroY']}, Z={parsed['GyroZ']}")
    print(f"Battery: {parsed['BatteryVoltage(V)']:.2f}V, {parsed['BatteryCurrent(mA)']:.1f}mA")
    print(f"Temperature: {parsed['Temperature(°C)']:.1f}°C")
    print(f"Triggers: L={parsed['TriggerL']}, R={parsed['TriggerR']}")

def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    """Device detection callback (OS independent)"""
    if advertisement_data.manufacturer_data:
        for company_id, data in advertisement_data.manufacturer_data.items():
            if company_id == JOYCON2_MANUFACTURER_ID:
                print(f"Joycon2 found: {device.name} ({device.address})")
                return device
    return None

async def find_joycon2():
    """Find Joycon2 device (OS independent)"""
    print("Searching for Joycon2...")
    
    found_device = None
    found_manufacturer_data = None
    
    def enhanced_detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
        """Joycon2 detection callback (proceed immediately, OS independent)"""
        nonlocal found_device, found_manufacturer_data
        
        # For Windows: use advertisement_data.manufacturer_data directly
        if advertisement_data.manufacturer_data:
            for company_id, data in advertisement_data.manufacturer_data.items():
                if company_id == JOYCON2_MANUFACTURER_ID:
                    print(f"*** JOYCON2 DETECTED DURING SCAN: {device.name} ({device.address}) ***")
                    print(f"    Company ID: 0x{company_id:04X}")
                    print(f"    Manufacturer Data: {data.hex()}")
                    found_device = device
                    found_manufacturer_data = data
                    return
        
        # For Linux/macOS: also check device.metadata
        if hasattr(device, 'metadata') and device.metadata.get("manufacturer_data"):
            for company_id, data in device.metadata["manufacturer_data"].items():
                if company_id == JOYCON2_MANUFACTURER_ID:
                    print(f"*** JOYCON2 DETECTED DURING SCAN (metadata): {device.name} ({device.address}) ***")
                    print(f"    Company ID: 0x{company_id:04X}")
                    print(f"    Manufacturer Data: {data.hex()}")
                    found_device = device
                    found_manufacturer_data = data
                    return
    
    # Callback-based scanning (OS independent)
    scanner = BleakScanner(enhanced_detection_callback)
    await scanner.start()
    
    try:
        # Scan for 10 seconds, or until Joycon2 is found
        for i in range(100):  # 100回 × 0.1秒 = 10秒
            if found_device is not None:
                print("Joycon2 found! Interrupting scan.")
                break
            await asyncio.sleep(0.1)
    finally:
        await scanner.stop()
    
    # If Joycon2 is found, process immediately
    if found_device is not None:
        device_info = await process_joycon2_device(found_device, found_manufacturer_data)
        return device_info
    
    # If not found, rescan using traditional method
    print("Not found in callback, rescanning using traditional method...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    for device in devices:
        # For Linux/macOS: use device.metadata
        if hasattr(device, 'metadata') and device.metadata.get("manufacturer_data"):
            for company_id in device.metadata["manufacturer_data"].keys():
                if company_id == JOYCON2_MANUFACTURER_ID:
                    manufacturer_bytes = device.metadata["manufacturer_data"][company_id]
                    device_info = await process_joycon2_device(device, manufacturer_bytes)
                    return device_info
        
        # For Windows: cannot access individual device manufacturer_data,
        # already processed in callback-based scanning
        # no additional processing here
    
    print("Joycon2 not found")
    return None

async def process_joycon2_device(device, manufacturer_bytes):
    """Process Joycon2 device information (OS independent)"""
    print(f"Joycon2 found:")
    print(f"  Device Info:")
    print(f"    Name: {device.name}")
    print(f"    Address: {device.address}")
    # Safe RSSI retrieval (Windows compatible)
    if hasattr(device, 'rssi'):
        print(f"    RSSI: {device.rssi}")    
    print(f"    Manufacturer Data: {manufacturer_bytes.hex()}")
    print(f"    Manufacturer Data Length: {len(manufacturer_bytes)} bytes")
    
    # Determine L/R from 6th byte (index 5)
    device_side = "Unknown"
    if len(manufacturer_bytes) >= 7:
        byte6 = manufacturer_bytes[5]  # 6th byte (index 5)
        if byte6 == 0x67:
            device_side = "L"
            print(f"    Detected as: L (byte6=0x67)")
        elif byte6 == 0x66:
            device_side = "R"
            print(f"    Detected as: R (byte6=0x66)")
        elif byte6 == 0x73:
            device_side = "GCCon"
            print(f"    Detected as: GCCon (byte6=0x73)")
        else:
            print(f"    Detected as: Unknown (byte6=0x{byte6:02x})")
    
    print(f"  " + "="*50)
    
    # Return device information and side information as dictionary
    return {
        'device': device,
        'side': device_side,
        'manufacturer_data': manufacturer_bytes
    }

async def connect_and_communicate(device_info):
    """Connect to device and communicate (OS independent)"""
    if not device_info:
        print("Device information not specified")
        return
    
    try:
        device = device_info['device']
        device_side = device_info['side']
        
        print(f"Connecting: {device.name} ({device.address}) - {device_side}")
        await connect_to_address(device.address, device.name, device_side)
                
    except Exception as e:
        print(f"Connection error: {e}")

async def connect_to_address(address, device_name="Joycon2", device_side="Unknown"):
    """Connect directly to specified address"""
    try:
        print(f"Connecting: {device_name} ({address}) - {device_side}")
        async with BleakClient(address) as client:
            print(f"Connection successful! Device: {device_name} ({device_side})")
            
            # Sleep for 1 second immediately after connection
            print("Waiting for stabilization after connection...")
            await asyncio.sleep(0.5)
            
            # Send write commands
            write_commands = [
                bytes.fromhex("0c91010200040000FF000000"),
                bytes.fromhex("0c91010400040000FF000000")
            ]
            
            for i, command in enumerate(write_commands, 1):
                print(f"Sending write command {i}...")
                await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, command)
                await asyncio.sleep(0.5)
            
            print("Write completed")
            
            # Start data subscription
            print("Starting data subscription...")
            
            def notification_handler(sender, data):
                """Handler when notification data is received"""
                try:
                    parsed = parse_joycon2_data(data)
                    print_parsed_data(parsed)
                except Exception as e:
                    print(f"Data parsing error: {e}")
                    print(f"Raw data: {data.hex()}")
            
            await client.start_notify(SUBSCRIBE_CHARACTERISTIC_UUID, notification_handler)
            
            print(f"Data reception started. Device: {device_name} ({device_side})")
            print("Press Ctrl+C to exit.")
            
            # Continue receiving data in infinite loop
            while True:
                await asyncio.sleep(0.1)
                
    except Exception as e:
        print(f"Connection error: {e}")

async def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Joycon2 BLE Client")
    parser.add_argument("--address", "-a", help="MAC address of device to connect to (e.g., AA:BB:CC:DD:EE:FF)")
    args = parser.parse_args()
    
    print("Joycon2 BLE Client")
    print("="*30)
    
    if args.address:
        # Connect directly to specified address
        print(f"Connecting directly to specified address: {args.address}")
        try:
            await connect_to_address(args.address)
        except KeyboardInterrupt:
            print("\nExiting program")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        # Search for Joycon2
        device_info = await find_joycon2()
        
        if device_info:
            try:
                await connect_and_communicate(device_info)
            except KeyboardInterrupt:
                print("\nExiting program")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            print("Joycon2 device not found")

if __name__ == "__main__":
    asyncio.run(main())

