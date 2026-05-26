import sys, os, json, time, threading, requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["FLASK_DEBUG"] = "false"
os.environ["FLASK_PORT"] = "5399"

from app import create_app
from database import db
from models.iot_device import IoTDeviceLog

app = create_app(test_config={"WTF_CSRF_ENABLED": False, "TESTING": True})
with app.app_context():
    db.session.query(IoTDeviceLog).delete()
    db.session.commit()
t = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5399, debug=False), daemon=True)
t.start()
time.sleep(3)

BASE = "http://localhost:5399"
failures = []

# Authenticated session for protected endpoints
s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"}, timeout=5)
if r.status_code != 200:
    print(f"Login failed: {r.status_code} {r.text}")
    sys.exit(1)

def test(label, method, path, expect_status=None, checks=None, **kwargs):
    url = f"{BASE}{path}"
    fn = getattr(s, method.lower())
    try:
        timeout = kwargs.pop("req_timeout", 3)
        resp = fn(url, timeout=timeout, **kwargs)
        ok = resp.status_code in (200, 201)
        if expect_status:
            ok = resp.status_code == expect_status
        if ok:
            data = resp.json() if resp.status_code in (200, 201) else None
            if checks and data:
                for key, expected in checks.items():
                    val = data
                    for k in key.split("."):
                        val = val.get(k) if isinstance(val, dict) else None
                    if val != expected:
                        print(f"  FAIL check {key}: expected {expected}, got {val}")
                        failures.append(label)
            print(f"  PASS [{resp.status_code}] {label}")
        else:
            print(f"  FAIL [{resp.status_code}] {label}")
            failures.append(label)
        return resp.json() if resp.status_code in (200, 201) else None
    except Exception as e:
        print(f"  FAIL [{e}] {label}")
        failures.append(label)
        return None

print("=== IoT API Tests ===\n")

test("Stats empty", "GET", "/api/iot/stats",
     checks={"total_events": 0, "registered_devices": 0})
test("Events list empty", "GET", "/api/iot/events",
     checks={"total": 0})
test("Devices list empty", "GET", "/api/iot/devices")

bc = test("POST barcode scan", "POST", "/api/iot/events", json={
    "device_id": "TEST-SCANNER-01", "device_type": "barcode_scanner",
    "event_type": "scan", "barcode_data": "5901234567897",
    "location": "Test-Lab", "battery_level": 92.5, "firmware_version": "v2.3.1",
})
assert bc and bc.get("event"), "POST should return event"

rfid = test("POST RFID tag_read", "POST", "/api/iot/events", json={
    "device_id": "TEST-RFID-01", "device_type": "rfid_reader",
    "event_type": "tag_read", "rfid_epc": "E280116060000205A8B1E030",
    "rfid_antenna": 2, "rssi": -62.5, "location": "Loading-Dock",
    "battery_level": 78.0, "firmware_version": "v4.1.2",
})
assert rfid and rfid.get("event")

test("POST heartbeat", "POST", "/api/iot/events", json={
    "device_id": "TEST-SCANNER-01", "device_type": "barcode_scanner",
    "event_type": "heartbeat", "location": "Test-Lab", "battery_level": 91.0,
})

test("POST error event", "POST", "/api/iot/events", json={
    "device_id": "TEST-RFID-01", "device_type": "rfid_reader",
    "event_type": "error", "error_message": "Antenna fault",
    "location": "Loading-Dock", "battery_level": 45.0,
})

test("POST missing device_id (400)", "POST", "/api/iot/events",
     expect_status=400, json={"device_type": "barcode_scanner"})

evts = test("Events list (4 events)", "GET", "/api/iot/events?per_page=10",
            checks={"total": 4})

evts2 = test("Filter by device_id", "GET", "/api/iot/events?device_id=TEST-RFID-01",
             checks={"total": 2})

test("Filter unprocessed", "GET", "/api/iot/events?unprocessed=1",
     checks={"total": 4})

devs = test("Devices list (2 devices)", "GET", "/api/iot/devices")
if devs:
    if len(devs) != 2:
        print(f"  FAIL expected 2 devices, got {len(devs)}")
        failures.append("device count")

if bc and bc.get("event"):
    test("Process event", "PATCH", f"/api/iot/events/{bc['event']['id']}/process",
         json={"quantity": 5}, checks={"event.is_processed": True})

stats = test("Stats after events", "GET", "/api/iot/stats",
             checks={"total_events": 4, "registered_devices": 2})
if stats and stats.get("unprocessed_events") != 3:
    print(f"  WARN expected 3 unprocessed, got {stats.get('unprocessed_events')}")

test("Simulator status (not running)", "GET", "/api/iot/simulator/status",
     checks={"running": False})
test("Simulator start", "POST", "/api/iot/simulator/start",
     checks={"status": "started"})
test("Simulator status (running)", "GET", "/api/iot/simulator/status",
     checks={"running": True})
test("Simulator stop", "POST", "/api/iot/simulator/stop",
     checks={"status": "stopped"}, req_timeout=10)
test("Simulator status (stopped)", "GET", "/api/iot/simulator/status",
     checks={"running": False})

print()
if failures:
    print(f"*** {len(failures)} TESTS FAILED ***")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("=== All IoT API tests passed ===")
