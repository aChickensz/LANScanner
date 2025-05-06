#!/usr/bin/env python3
"""
Utility script for managing the network device database.
Usage: python db_utils.py [command]

Commands:
  init        - Initialize the database
  stats       - Show statistics about the database
  export      - Export devices to JSON format
  devices     - List all devices
  purge-old   - Remove devices not seen recently (older than 30 days)
  add-device  - Add a new device manually
"""

import argparse
import json
import sqlite3
import sys
import os
from datetime import datetime, timedelta

# Configuration
DATABASE_PATH = "network_devices.db"
DEFAULT_SUBNET = "10.0.0.1/20"

def get_db_connection():
    """Get a database connection with row factory enabled"""
    if not os.path.exists(DATABASE_PATH):
        print(f"Error: Database file {DATABASE_PATH} does not exist.")
        print("Run 'python db_utils.py init' to create it.")
        sys.exit(1)
        
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    if os.path.exists(DATABASE_PATH):
        confirm = input(f"Database {DATABASE_PATH} already exists. Reinitialize? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create devices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT UNIQUE NOT NULL,
        mac TEXT NOT NULL,
        name TEXT DEFAULT '',
        subnet TEXT NOT NULL,
        first_seen TIMESTAMP NOT NULL,
        last_seen TIMESTAMP NOT NULL
    )
    ''')
    
    # Create scan_logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP NOT NULL,
        subnet TEXT NOT NULL,
        devices_found INTEGER NOT NULL,
        new_devices INTEGER NOT NULL
    )
    ''')
    
    # Create device_logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP NOT NULL,
        ip TEXT NOT NULL,
        mac TEXT NOT NULL,
        event_type TEXT NOT NULL
    )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_subnet ON devices(subnet)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_logs_timestamp ON scan_logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_logs_timestamp ON device_logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_logs_ip ON device_logs(ip)')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {os.path.abspath(DATABASE_PATH)}")

def show_stats():
    """Show database statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get counts
    cursor.execute("SELECT COUNT(*) FROM devices")
    device_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM scan_logs")
    scan_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM device_logs")
    log_count = cursor.fetchone()[0]
    
    # Get latest scan
    cursor.execute("SELECT * FROM scan_logs ORDER BY timestamp DESC LIMIT 1")
    latest_scan = cursor.fetchone()
    
    # Get subnet stats
    cursor.execute("""
    SELECT subnet, COUNT(*) as count 
    FROM devices 
    GROUP BY subnet 
    ORDER BY count DESC
    """)
    subnet_stats = cursor.fetchall()
    
    # Display results
    print("\n===== Database Statistics =====")
    print(f"Total devices: {device_count}")
    print(f"Total scans: {scan_count}")
    print(f"Total logs: {log_count}")
    
    if latest_scan:
        print(f"\nLatest scan: {latest_scan['timestamp']}")
        print(f"  Subnet: {latest_scan['subnet']}")
        print(f"  Devices found: {latest_scan['devices_found']}")
        print(f"  New devices: {latest_scan['new_devices']}")
    
    if subnet_stats:
        print("\nDevices by subnet:")
        for subnet in subnet_stats:
            print(f"  {subnet['subnet']}: {subnet['count']} devices")
    
    conn.close()

def export_devices():
    """Export devices to JSON format"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM devices ORDER BY ip")
    devices = [dict(row) for row in cursor.fetchall()]
    
    export_file = "devices_export.json"
    with open(export_file, "w") as f:
        json.dump(devices, f, indent=2)
    
    print(f"Exported {len(devices)} devices to {export_file}")
    conn.close()

def list_devices():
    """List all devices in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM devices ORDER BY ip")
    devices = cursor.fetchall()
    
    if not devices:
        print("No devices found in database.")
        return
    
    print("\n{:<15} {:<17} {:<20} {:<15} {:<20} {:<20}".format(
        "IP", "MAC", "Name", "Subnet", "First Seen", "Last Seen"))
    print("-" * 110)
    
    for device in devices:
        print("{:<15} {:<17} {:<20} {:<15} {:<20} {:<20}".format(
            device['ip'], 
            device['mac'], 
            device['name'] or '(unnamed)', 
            device['subnet'],
            device['first_seen'],
            device['last_seen']
        ))
    
    print(f"\nTotal: {len(devices)} devices")
    conn.close()

def purge_old_devices():
    """Remove devices not seen recently"""
    days = int(input("Remove devices not seen in how many days? [30]: ") or "30")
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find devices to remove
    cursor.execute("""
    SELECT COUNT(*) FROM devices
    WHERE last_seen < ?
    """, (cutoff_date,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"No devices found older than {days} days.")
        conn.close()
        return
    
    confirm = input(f"Found {count} devices not seen in {days} days. Delete them? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        conn.close()
        return
    
    # Get IPs for logging
    cursor.execute("""
    SELECT ip, mac FROM devices
    WHERE last_seen < ?
    """, (cutoff_date,))
    old_devices = cursor.fetchall()
    
    # Delete the devices
    cursor.execute("""
    DELETE FROM devices
    WHERE last_seen < ?
    """, (cutoff_date,))
    
    # Log the deletions
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for device in old_devices:
        cursor.execute("""
        INSERT INTO device_logs (timestamp, ip, mac, event_type)
        VALUES (?, ?, ?, ?)
        """, (now, device['ip'], device['mac'], 'PURGED'))
    
    conn.commit()
    conn.close()
    print(f"Removed {count} devices not seen since {cutoff_date}.")

def add_device():
    """Add a new device manually"""
    ip = input("IP address: ")
    if not ip:
        print("IP address is required. Aborted.")
        return
        
    mac = input("MAC address: ")
    if not mac:
        print("MAC address is required. Aborted.")
        return
    
    name = input("Device name (optional): ")
    subnet = input(f"Subnet [{DEFAULT_SUBNET}]: ") or DEFAULT_SUBNET
    
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Check if device exists
        cursor.execute("SELECT id FROM devices WHERE ip = ?", (ip,))
        existing = cursor.fetchone()
        
        if existing:
            confirm = input("Device with this IP already exists. Update? (y/N): ")
            if confirm.lower() != 'y':
                print("Aborted.")
                conn.close()
                return
                
            cursor.execute("""
            UPDATE devices 
            SET mac = ?, name = ?, subnet = ?, last_seen = ?
            WHERE ip = ?
            """, (mac, name, subnet, now, ip))
            
            print(f"Updated device with IP {ip}")
        else:
            cursor.execute("""
            INSERT INTO devices (ip, mac, name, subnet, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (ip, mac, name, subnet, now, now))
            
            # Log new device
            cursor.execute("""
            INSERT INTO device_logs (timestamp, ip, mac, event_type)
            VALUES (?, ?, ?, ?)
            """, (now, ip, mac, 'MANUAL_ADD'))
            
            print(f"Added new device with IP {ip}")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Network Device Database Utility")
    parser.add_argument('command', choices=['init', 'stats', 'export', 'devices', 'purge-old', 'add-device'],
                        help='Command to execute')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
    elif args.command == 'stats':
        show_stats()
    elif args.command == 'export':
        export_devices()
    elif args.command == 'devices':
        list_devices()
    elif args.command == 'purge-old':
        purge_old_devices()
    elif args.command == 'add-device':
        add_device()

if __name__ == '__main__':
    main()
