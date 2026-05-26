import time
import random
import threading
import logging
import os
import requests

logger = logging.getLogger(__name__)

API_BASE = os.getenv("IOT_API_BASE", "http://localhost:5000/api/iot")

DEVICE_TEMPLATES = [
    {"device_id": "SCANNER-WH001", "device_type": "barcode_scanner", "location": "Warehouse-A"},
    {"device_id": "SCANNER-WH002", "device_type": "barcode_scanner", "location": "Warehouse-B"},
    {"device_id": "SCANNER-RT001", "device_type": "barcode_scanner", "location": "Retail-Floor"},
    {"device_id": "RFID-DOCK1", "device_type": "rfid_reader", "location": "Loading-Dock"},
    {"device_id": "RFID-DOCK2", "device_type": "rfid_reader", "location": "Shipping-Dock"},
    {"device_id": "RFID-GATE-EXIT", "device_type": "rfid_reader", "location": "Exit-Gate"},
    {"device_id": "TEMP-SENSOR-C001", "device_type": "temperature_sensor", "location": "Cold-Storage"},
    {"device_id": "SCALE-RCV01", "device_type": "weight_scale", "location": "Receiving"},
]

SAMPLE_BARCODES = [
    "5901234567897", "4012345678901", "9780201379624",
    "8712345678900", "2001234567890",
    "1234567890123", "9876543210987",
]

SAMPLE_RFID_EPCS = [
    "E280116060000205A8B1E030", "E280116060000205A8B1E031",
    "E280116060000205A8B1E032", "E280116060000205A8B1E033",
    "E280116060000205A8B1E034", "E280116060000205A8B1E035",
]


def generate_scan_event(device):
    return {
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "event_type": "scan",
        "barcode_data": random.choice(SAMPLE_BARCODES),
        "location": device["location"],
        "battery_level": round(random.uniform(55, 100), 1),
        "firmware_version": "v2.3.1",
        "raw_payload": {"scanner_model": "Zebra DS2208", "decode_time_ms": random.randint(10, 150)},
    }


def generate_rfid_event(device):
    return {
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "event_type": "tag_read",
        "rfid_epc": random.choice(SAMPLE_RFID_EPCS),
        "rfid_antenna": random.randint(1, 4),
        "rssi": round(random.uniform(-80, -40), 1),
        "location": device["location"],
        "battery_level": round(random.uniform(50, 100), 1),
        "firmware_version": "v4.1.2",
        "raw_payload": {"reader_model": "Impinj R420", "protocol": "EPC Gen2v2"},
    }


def generate_heartbeat(device):
    return {
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "event_type": "heartbeat",
        "location": device["location"],
        "battery_level": round(random.uniform(40, 100), 1),
        "firmware_version": "v2.3.1",
        "raw_payload": {"uptime_seconds": random.randint(3600, 86400)},
    }


def generate_error(device):
    return {
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "event_type": "error",
        "location": device["location"],
        "battery_level": round(random.uniform(10, 30), 1),
        "firmware_version": "v2.3.1",
        "error_message": random.choice([
            "Read timeout",
            "Antenna fault on port 2",
            "Low battery warning",
            "Communication loss with host",
        ]),
        "raw_payload": {"error_code": random.randint(100, 999)},
    }


def run_simulation(stop_event, interval_range=(1, 5), error_rate=0.05):
    session = requests.Session()
    while not stop_event.is_set():
        device = random.choice(DEVICE_TEMPLATES)
        roll = random.random()
        if roll < error_rate:
            payload = generate_error(device)
        elif device["device_type"] == "rfid_reader":
            payload = generate_rfid_event(device) if roll < 0.7 else generate_heartbeat(device)
        elif device["device_type"] in ("temperature_sensor", "weight_scale"):
            payload = generate_heartbeat(device)
        else:
            payload = generate_scan_event(device) if roll < 0.8 else generate_heartbeat(device)

        try:
            resp = session.post(f"{API_BASE}/events", json=payload, timeout=2)
            if resp.status_code not in (200, 201):
                logger.warning("IoT simulator: %s returned %d", API_BASE, resp.status_code)
        except requests.RequestException as e:
            logger.error("IoT simulator connection error: %s", e)
        time.sleep(random.uniform(*interval_range))


class IoTSimulator:
    def __init__(self, interval_range=(1, 5), error_rate=0.05):
        self.interval_range = interval_range
        self.error_rate = error_rate
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=run_simulation,
            args=(self._stop, self.interval_range, self.error_rate),
            daemon=True,
        )
        self._thread.start()
        return {"status": "started", "interval_range": self.interval_range}

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        return {"status": "stopped"}

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()
