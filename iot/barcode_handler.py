import os
import re
import random
import requests
from datetime import datetime


API_BASE = os.getenv("IOT_API_BASE", "http://localhost:5000/api/iot")
BARCODE_FORMATS = {
    "EAN-13": r"^\d{13}$",
    "EAN-8": r"^\d{8}$",
    "UPC-A": r"^\d{12}$",
    "CODE128": r"^[A-Za-z0-9\-]+$",
}


class BarcodeHandler:
    scannable_barcodes = [
        "5901234567897",
        "4012345678901",
        "9780201379624",
        "8712345678900",
        "2001234567890",
    ]

    def __init__(self, device_id="SCANNER-WH001", location="Warehouse-A", api_base=API_BASE):
        self.device_id = device_id
        self.location = location
        self.api_base = api_base
        self.last_scan = None
        self.session = requests.Session()

    def parse_barcode(self, raw_data):
        raw = raw_data.strip()
        for fmt_name, pattern in BARCODE_FORMATS.items():
            if re.match(pattern, raw):
                self.last_scan = raw
                return {"barcode": raw, "format": fmt_name}
        return None

    def simulate_scan(self, barcode=None):
        if barcode is None:
            barcode = random.choice(self.scannable_barcodes)
        parsed = self.parse_barcode(barcode)
        if not parsed:
            return {"error": f"Invalid barcode: {barcode}"}
        return parsed

    def send_event(self, barcode=None):
        result = self.simulate_scan(barcode)
        if "error" in result:
            return result
        payload = {
            "device_id": self.device_id,
            "device_type": "barcode_scanner",
            "event_type": "scan",
            "barcode_data": result["barcode"],
            "location": self.location,
            "battery_level": round(random.uniform(60, 100), 1),
            "firmware_version": "v2.3.1",
            "raw_payload": {"scanner_model": "Zebra DS2208", "decode_time_ms": random.randint(15, 120)},
        }
        resp = self.session.post(f"{self.api_base}/events", json=payload)
        if resp.status_code == 201:
            self.last_scan = result["barcode"]
        return resp.json()
