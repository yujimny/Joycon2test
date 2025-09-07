# Joycon2 BLE Client

A Python script that communicates with Joycon2 devices via BLE (Bluetooth Low Energy) and analyzes sensor data in real-time.

## Features

- **Automatic Joycon2 Device Detection**: Automatically finds Joycon2 devices using Manufacturer ID (0x0553)
- **BLE Connection and Data Communication**: Establishes stable BLE connections and handles data transmission
- **Real-time Sensor Data Analysis**: Parses and displays sensor data as it's received
- **Comprehensive Data Display**: Shows stick positions, button states, accelerometer, gyroscope, battery information, and more
- **Cross-platform Support**: Works on macOS, Linux, and Windows with BLE support
- **Device Side Detection**: Automatically detects whether the device is Left (L), Right (R), or GCCon controller

## What joycon2_ble_client.py Does

This script performs the following operations:

1. **Device Discovery**: Scans for Joycon2 devices using BLE advertisement data
2. **Connection Management**: Establishes and maintains BLE connections with Joycon2 devices
3. **Data Parsing**: Interprets raw binary data packets from the Joycon2 into readable sensor values
4. **Real-time Monitoring**: Continuously receives and displays sensor data including:
   - Button states (A, B, X, Y, D-pad, triggers, etc.)
   - Analog stick positions (left and right)
   - Mouse/trackpad data with movement deltas
   - Accelerometer readings (X, Y, Z axes)
   - Gyroscope readings (X, Y, Z axes)
   - Battery voltage and current
   - Temperature readings
   - Trigger button analog values
5. **Error Handling**: Manages connection errors and data parsing issues gracefully

## Requirements

- Python 3.7 or higher
- macOS/Linux/Windows with BLE support
- Joycon2 device in pairing/advertising mode

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Method 1: Automatic Device Discovery
1. Put your Joycon2 device in pairing mode
2. Run the script:
```bash
python joycon2_ble_client.py
```

### Method 2: Direct Connection
Connect directly to a specific device by MAC address:
```bash
python joycon2_ble_client.py --address AA:BB:CC:DD:EE:FF
```

## Displayed Data

- **PacketID**: Packet identifier for data tracking
- **Buttons**: Button states in hexadecimal format with human-readable button names
- **LeftStick/RightStick**: X/Y coordinates of left and right analog sticks
- **Mouse**: Mouse/trackpad coordinates with movement deltas
- **Accel**: Accelerometer sensor readings (X/Y/Z axes)
- **Gyro**: Gyroscope sensor readings (X/Y/Z axes)
- **Battery**: Battery voltage (V) and current (mA)
- **Temperature**: Temperature reading in Celsius
- **Triggers**: Analog trigger button values (L/R)
- **Mag**: Magnetometer readings (X/Y/Z axes)

## Exit Method

Press Ctrl+C to exit the program.

## Notes

- Joycon2 device must be in BLE advertising mode
- Initial connection may require pairing on some systems
- If data reception errors occur, check the device status
- The script automatically detects device type (L/R/GCCon) from manufacturer data

