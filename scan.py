from scapy.all import ARP, Ether, srp
import time
import json
from datetime import datetime
import os

DICT_LOG = "dict.log"
NEW_LOG = "new_devices.log"
LOG_LOG = "log.log"

def log_print(message):
    """Print to console and append to log.log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open(LOG_LOG, "a") as log_file:
        log_file.write(formatted + "\n")

def load_known_devices():
    """Load known devices from dict.log as a dict keyed by IP."""
    if os.path.exists(DICT_LOG):
        try:
            with open(DICT_LOG, "r") as f:
                entries = json.load(f)
                return {entry["ip"]: entry for entry in entries}
        except Exception:
            return {}
    return {}

def save_known_devices(known_dict):
    """Save known devices to dict.log in a sorted list format with timestamps."""
    device_list = sorted(known_dict.values(), key=lambda x: x["ip"])
    with open(DICT_LOG, "w") as f:
        json.dump(device_list, f, indent=4)

def log_new_device(device):
    """Log a new device to new_devices.log with timestamp."""
    with open(NEW_LOG, "a") as log:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"[{timestamp}] New device: IP={device['ip']}, MAC={device['mac']}\n")

def scan_network():
    """Perform ARP scan on network and return list of devices."""
    target = "10.0.0.1/20"  # Change based on your network
    arp = ARP(pdst=target)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp
    result = srp(packet, timeout=3, verbose=0)[0]
    return [{'ip': r.psrc, 'mac': r.hwsrc} for s, r in result]

log_print("Started scanning...")
known_devices = load_known_devices()

while True:
    current_devices = scan_network()
    for device in current_devices:
        ip = device['ip']
        mac = device['mac']
        if ip not in known_devices:
            device["first_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_print(f"New device: {device}")
            log_new_device(device)
            known_devices[ip] = device
            save_known_devices(known_devices)
    log_print("Scanned.")
    time.sleep(60)

