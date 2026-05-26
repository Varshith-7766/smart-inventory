import os
import random
import requests
from datetime import datetime


API_BASE = os.getenv("IOT_API_BASE", "http://localhost:5000/api/iot")


class RFIDHandler:
    simulated_tags = [
        {"epc": "E280116060000205A8B1E030", "product_sku": "SKU001", "rssi_range": (-75, -45)},
        {"epc": "E280116060000205A8B1E031", "product_sku": "SKU002", "rssi_range": (-80, -50)},
        {"epc": "E280116060000205A8B1E032", "product_sku": "SKU003", "rssi_range": (-70, -40)},
        {"epc": "E280116060000205A8B1E033", "product_sku": "SKU004", "rssi_range": (-78, -48)},
        {"epc": "E280116060000205A8B1E034", "product_sku": "SKU005", "rssi_range": (-72, -42)},
    ]

    def __init__(self, device_id="RFID-GATE-DOCK1", reader_device="COM5", location="Loading-Dock", api_base=API_BASE):
        self.device_id = device_id
        self.reader_device = reader_device
        self.location = location
        self.api_base = api_base
        self.connected = False
        self.antenna_count = 4
        self.session = requests.Session()

    def connect(self):
        self.connected = True
        self.send_event("connect")
        return {"status": "connected", "device_id": self.device_id, "device": self.reader_device}

    def disconnect(self):
        self.connected = False
        self.send_event("disconnect")

    def read_tag(self):
        if not self.connected:
            return None
        tag = random.choice(self.simulated_tags)
        rssi = round(random.uniform(*tag["rssi_range"]), 1)
        return {
            "epc": tag["epc"],
            "product_sku": tag["product_sku"],
            "antenna": random.randint(1, self.antenna_count),
            "rssi": rssi,
            "read_rate_hz": round(random.uniform(10, 50), 1),
        }

    def read_multiple(self, count=5):
        if not self.connected:
            return []
        seen = set()
        tags = []
        for _ in range(count):
            tag = self.read_tag()
            if tag and tag["epc"] not in seen:
                seen.add(tag["epc"])
                tags.append(tag)
        return tags

    def send_event(self, event_type="tag_read", tag_data=None):
        payload = {
            "device_id": self.device_id,
            "device_type": "rfid_reader",
            "event_type": event_type,
            "location": self.location,
            "battery_level": round(random.uniform(50, 100), 1),
            "firmware_version": "v4.1.2",
            "raw_payload": {
                "reader_model": "Impinj R420",
                "antenna_count": self.antenna_count,
                "protocol": "EPC Gen2v2",
            },
        }
        if tag_data:
            payload["rfid_epc"] = tag_data["epc"]
            payload["rfid_antenna"] = tag_data["antenna"]
            payload["rssi"] = tag_data["rssi"]
        resp = self.session.post(f"{self.api_base}/events", json=payload)
        return resp.json() if resp.status_code == 201 else resp.json()
