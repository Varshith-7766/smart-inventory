import threading
import time
import random


class SerialReader:
    def __init__(self, port="COM3", baud_rate=9600):
        self.port = port
        self.baud_rate = baud_rate
        self.running = False
        self.callback = None
        self._thread = None

    def start(self, callback=None):
        self.callback = callback
        self.running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        while self.running:
            data = self._simulated_read()
            if data and self.callback:
                self.callback(data)
            time.sleep(random.uniform(0.5, 3))

    def _simulated_read(self):
        devices = {
            "barcode": {
                "raw": "5901234567897",
                "device": "SCANNER-WH001",
                "type": "scan",
            },
            "rfid": {
                "raw": "E280116060000205A8B1E030",
                "device": "RFID-DOCK1",
                "type": "tag_read",
            },
        }
        return random.choice(list(devices.values()))

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
