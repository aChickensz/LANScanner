# LAN Scanner

A lightweight, web-based network scanning tool that monitors devices on your local network. This application uses ARP scanning to discover devices on your LAN, tracks when they appear and disappear, and provides a responsive web dashboard for monitoring your network.

## Features

- **Automatic Network Scanning**: Periodically scans your network to discover connected devices
- **Device Tracking**: Logs first and last seen timestamps for all discovered devices
- **Web Dashboard**: Monitor and manage discovered devices through a responsive interface
- **Custom Scanning**: Specify subnets to scan on demand
- **Device Management**: Name your devices and organize them by subnet
- **Filtering & Sorting**: Easily find devices by filtering and sorting in the dashboard
- **Database Support**: All data is stored in SQLite for persistence and reliability
- **Command-line Utilities**: Manage the device database with helper scripts

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Database Utilities](#database-utilities)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Screenshots](#screenshots)
- [License](#license)

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)
- Scapy (for network scanning)
- Flask (for web interface)

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/aChickensz/LANScanner.git
   cd lan-scanner
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```bash
   python db_util.py init
   ```

## Usage

### Starting the Web Interface

Run the Flask application:

```bash
sudo python app.py
```

The web interface will be accessible at `http://localhost:1817`.

> **Note:** Root/sudo privileges are required for ARP scanning.

### Basic Scanning

The application will automatically scan your network every minute using the default subnet defined in the configuration (10.0.0.1/20 by default).

### Using the Web Interface

1. **Viewing Devices**: All discovered devices are displayed in the main table.
2. **Custom Scan**: Enter a subnet (e.g., 192.168.1.0/24) in the input field and click "Scan Now".
3. **Filtering**: Use the filter inputs to search for specific devices by name or subnet.
4. **Sorting**: Click on any column header to sort the table by that field.
5. **Naming Devices**: Click on the name field for any device to give it a custom name.

## Database Utilities

The `db_util.py` script provides several commands for managing the database:

```bash
python db_util.py [command]
```

Available commands:

- `init` - Initialize the database
- `stats` - Show statistics about the database
- `export` - Export devices to JSON format
- `devices` - List all devices
- `purge-old` - Remove devices not seen recently
- `add-device` - Add a new device manually

Examples:

```bash
# Show database statistics
python db_util.py stats

# List all devices in the database
python db_util.py devices

# Export devices to JSON
python db_util.py export

# Add a device manually
python db_util.py add-device
```

## Project Structure

- `app.py` - Main Flask application with web server and background scanner
- `db_util.py` - Database utility script
- `scan.py` - Standalone scanner script (alternative to app.py)
- `templates/index.html` - Main web interface template
- `static/styles.css` - CSS styles for the web interface
- `static/app.js` - JavaScript for the web interface
- `network_devices.db` - SQLite database file (created after initialization)

## Configuration

Key configuration variables are defined at the top of each script:

- **Default subnet**: Change `DEFAULT_SUBNET` in `app.py` or `db_util.py` to your preferred network range
- **Database path**: Modify `DATABASE_PATH` if you want to store the database elsewhere
- **Scan interval**: Adjust the `time.sleep()` value in the background scanner function

## Screenshots

![image](https://github.com/user-attachments/assets/d2410404-e5bb-405f-acad-49205c66d25d)

## License

[MIT License](LICENSE)
