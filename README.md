"# Serial Port GUI Application

A simple Python GUI application that allows you to:
- Connect to a serial port with configurable baud rate
- Display and edit multiline text
- Select individual lines
- Send lines individually to the serial port

## Features

- **Serial Connection**: Connect to any available serial port with selectable baud rates (9600, 19200, 38400, 57600, 115200)
- **Port Auto-Detection**: Automatically lists available serial ports with a refresh button
- **Text Widget**: Multiline text area for composing or displaying content
- **Line Selection**: Select any line(s) and send them individually
- **Batch Send**: Send all lines in the text area to the serial port
- **Status Indicator**: Real-time connection status display
- **Built with tkinter**: Uses Python's standard GUI library

## Requirements

- Python 3.6+
- pyserial (listed in requirements.txt)

## Installation

1. Clone or download this repository
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python serial_gui_app.py
```

2. **Connect to Serial Port**:
   - Select the desired serial port from the dropdown
   - Choose the baud rate (default is 9600)
   - Click "Connect" button

3. **Send Data**:
   - Type or paste text lines in the text area
   - **Send Selected Line**: Select one or more lines and click "Send Selected Line" to send them
   - **Send All Lines**: Click "Send All Lines" to send all non-empty lines in sequence

4. **Manage Text**:
   - Use "Clear Text" button to clear the text area
   - Use "Refresh Ports" to update the list of available serial ports

5. **Disconnect**:
   - Click "Disconnect" button to close the serial connection

## Notes

- Each line is sent with a newline character (`\n`)
- Empty lines are skipped when sending
- The application supports both selecting individual lines and multiple consecutive lines
- Status indicator shows current connection state and port information
- Ensure proper serial port permissions on Linux/Mac (may require `sudo` or group membership)

## License

MIT" 
