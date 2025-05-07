from flask import Flask, render_template, jsonify, request
import threading
import time
import os
import sqlite3
from datetime import datetime
from scapy.all import ARP, Ether, srp

app = Flask(__name__)

#Database config
DATABASE_PATH = "network_devices.db"
LOG_LOG = "log.log"
DEFAULT_SUBNET = "10.0.0.1/20"

#==================== DATABASE FUNCTIONS ====================

def init_db():
    #Initialize the SQLite db with necessary tables
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    #Create devices table
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

    #Create scan_logs table for tracking scan history
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP NOT NULL,
        subnet TEXT NOT NULL,
        devices_found INTEGER NOT NULL,
        new_devices INTEGER NOT NULL
    )
    ''')

    #Create device_logs table to track new device discoveries
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP NOT NULL,
        ip TEXT NOT NULL,
        mac TEXT NOT NULL,
        event_type TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

def get_db_connection():
    #Get a database connection with row factory enabled
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_known_devices():
    #Get all known devices from the db
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices ORDER BY ip")
    devices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return devices

def get_device_by_ip(ip):
    #Get device information by IP address
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE ip = ?", (ip,))
    device = cursor.fetchone()
    conn.close()
    return dict(device) if device else None

def add_or_update_device(device):
    #Add a new device or update an existing one in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if device exists
    cursor.execute("SELECT id FROM devices WHERE ip = ?", (device['ip'],))
    existing = cursor.fetchone()

    if existing:
        # Update existing device
        cursor.execute("""
        UPDATE devices 
        SET mac = ?, last_seen = ?
        WHERE ip = ?
        """, (device['mac'], now, device['ip']))
        is_new = False
    else:
        # Add new device
        cursor.execute("""
        INSERT INTO devices (ip, mac, name, subnet, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (device['ip'], device['mac'], device.get('name', ''), 
              device.get('subnet', DEFAULT_SUBNET), now, now))

        # Log new device discovery
        cursor.execute("""
        INSERT INTO device_logs (timestamp, ip, mac, event_type)
        VALUES (?, ?, ?, ?)
        """, (now, device['ip'], device['mac'], 'NEW_DEVICE'))

        is_new = True

    conn.commit()
    conn.close()
    return is_new

def update_device_info(ip, name=None, subnet=None):
    #Update device name or subnet
    conn = get_db_connection()
    cursor = conn.cursor()

    if name is not None and subnet is not None:
        cursor.execute("""
        UPDATE devices 
        SET name = ?, subnet = ?
        WHERE ip = ?
        """, (name, subnet, ip))
    elif name is not None:
        cursor.execute("""
        UPDATE devices 
        SET name = ?
        WHERE ip = ?
        """, (name, ip))
    elif subnet is not None:
        cursor.execute("""
        UPDATE devices 
        SET subnet = ?
        WHERE ip = ?
        """, (subnet, ip))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def log_scan(subnet, devices_found, new_devices):
    """Log a network scan to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO scan_logs (timestamp, subnet, devices_found, new_devices)
    VALUES (?, ?, ?, ?)
    """, (now, subnet, devices_found, new_devices))

    conn.commit()
    conn.close()

#==================== UTILITIES ====================

def log_print(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open(LOG_LOG, "a") as f:
        f.write(formatted + "\n")

def scan_network(subnet=DEFAULT_SUBNET):
    arp = ARP(pdst=subnet)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp
    result = srp(packet, timeout=3, verbose=0)[0]
    return [{'ip': r.psrc, 'mac': r.hwsrc} for s, r in result]

# ==================== BACKGROUND SCANNER ====================

scanner_running = True
subnet_lock = threading.Lock()
custom_subnet = DEFAULT_SUBNET

def background_scanner():
    global custom_subnet
    while scanner_running:
        with subnet_lock:
            subnet = custom_subnet

        log_print(f"Scanning {subnet}")
        current_devices = scan_network(subnet=subnet)
        new_devices_count = 0

        for device in current_devices:
            device["subnet"] = subnet
            if add_or_update_device(device):
                new_devices_count += 1

        # Log scan statistics
        log_scan(subnet, len(current_devices), new_devices_count)

        time.sleep(60)
#==================== FLASK ROUTES ====================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/devices", methods=["GET"])
def get_devices():
    devices = get_known_devices()
    return jsonify(devices)

@app.route("/devices/update", methods=["POST"])
def update_device():
    data = request.json
    ip = data.get("ip")
    name = data.get("name")
    subnet = data.get("subnet")

    if update_device_info(ip, name, subnet):
        return jsonify({"status": "ok", "message": "Device updated."})
    else:
        return jsonify({"status": "error", "message": "Device not found."}), 404

@app.route("/scan", methods=["POST"])
def trigger_scan():
    data = request.json
    subnet = data.get("subnet")
    if subnet:
        with subnet_lock:
            global custom_subnet
            custom_subnet = subnet
    return jsonify({"status": "ok", "message": "Scan triggered."})

@app.route("/stats", methods=["GET"])
def get_stats():
    """Get network scanning statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    #Get device count
    cursor.execute("SELECT COUNT(*) as count FROM devices")
    device_count = cursor.fetchone()['count']
    #Get scan count
    cursor.execute("SELECT COUNT(*) as count FROM scan_logs")
    scan_count = cursor.fetchone()['count']

    #Get recently found devices
    cursor.execute("""
    SELECT * FROM devices 
    ORDER BY first_seen DESC 
    LIMIT 5
    """)
    recent_devices = [dict(row) for row in cursor.fetchall()]

    # Get subnet statistics
    cursor.execute("""
    SELECT subnet, COUNT(*) as device_count 
    FROM devices 
    GROUP BY subnet 
    ORDER BY device_count DESC
    """)
    subnet_stats = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        "device_count": device_count,
        "scan_count": scan_count,
        "recent_devices": recent_devices,
        "subnet_stats": subnet_stats
    })

@app.route("/logs", methods=["GET"])
def get_logs():
    """Get device discovery logs"""
    limit = request.args.get('limit', 50, type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM device_logs
    ORDER BY timestamp DESC
    LIMIT ?
    """, (limit,))

    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(logs)

# ==================== MAIN ====================

if __name__ == "__main__":
    #Init db before starting
    init_db()

    #Start background scanner thread
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()

    app.run(debug=True, host="0.0.0.0", port=1817)
