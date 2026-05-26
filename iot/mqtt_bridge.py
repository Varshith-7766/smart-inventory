"""
MQTT Bridge — Design for future hardware integration
====================================================

This module is a DESIGN DOCUMENT + STUB for connecting physical IoT
devices to the Smart Inventory API via MQTT (Message Queuing Telemetry
Transport).

Current approach:
  The IoT simulator and handler classes POST JSON events directly to
  the REST API at /api/iot/events.  This works fine for simulation and
  controlled environments.

Production upgrade path:
  1. Install an MQTT broker (Mosquitto, EMQX, HiveMQ)
  2. Replace POST calls with MQTT publish/subscribe
  3. Run this bridge as a background service that:
       - Subscribes to device topics (e.g., iot/+/scan, iot/rfid/+/tag)
       - Parses the MQTT message
       - Forwards to /api/iot/events via POST
       - Publishes processed acknowledgements back to iot/+/ack

MQTT Topic Design:
  iot/{device_id}/scan           ← Barcode scan events
  iot/{device_id}/rfid           ← RFID tag read events
  iot/{device_id}/heartbeat      ← Device keep-alive
  iot/{device_id}/error          ← Device error reports
  iot/{device_id}/ack            ← Server acknowledgement

Example message payload (same JSON schema as REST API):
  {
    "event_type": "scan",
    "barcode_data": "5901234567897",
    "device_id": "SCANNER-WH001",
    "location": "Warehouse-A"
  }

Dependencies (install when deploying):
  pip install paho-mqtt
"""


class MQTTBridge:
    def __init__(self, broker_host="localhost", broker_port=1883, api_base="http://localhost:5000/api/iot"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.api_base = api_base
        self.client = None

    def connect(self):
        """Connect to MQTT broker and subscribe to topics."""
        print(f"[MQTT Bridge] Placeholder: connect to {self.broker_host}:{self.broker_port}")
        print("[MQTT Bridge] Topic: iot/+/scan, iot/+/rfid, iot/+/heartbeat, iot/+/error")

    def start(self):
        """Start the MQTT event loop."""
        print("[MQTT Bridge] Placeholder: start listening for device messages")

    def stop(self):
        """Gracefully disconnect from broker."""
        print("[MQTT Bridge] Placeholder: disconnect")
