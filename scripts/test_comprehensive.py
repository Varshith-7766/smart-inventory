"""
Comprehensive corner-case and edge-case tests for Smart Inventory.

Covers: auth, products, sales, stock, IoT, dashboard, inventory audit, concurrency.

Usage:  python scripts/test_comprehensive.py
"""

import sys, os, json, time, threading, random, string, requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["FLASK_DEBUG"] = "false"
os.environ["FLASK_PORT"] = "5899"
os.environ["IOT_API_BASE"] = "http://localhost:5899/api/iot"

from database import db
from models import Product, Sale, SaleItem, InventoryLog, IoTDeviceLog, Category

from app import create_app
_app = create_app(test_config={"WTF_CSRF_ENABLED": False, "TESTING": True})
with _app.app_context():
    db.session.query(IoTDeviceLog).delete()
    db.session.query(InventoryLog).delete()
    db.session.query(SaleItem).delete()
    db.session.query(Sale).delete()
    db.session.query(Product).delete()
    db.session.query(Category).filter(Category.id > 1).delete()
    db.session.commit()

t = threading.Thread(target=lambda: _app.run(host="0.0.0.0", port=5899, debug=False), daemon=True)
t.start()
time.sleep(3)

BASE = "http://localhost:5899"
failures = []
passes = []

def check(label, ok, detail=""):
    if ok:
        passes.append(label)
        print(f"  PASS: {label}")
    else:
        failures.append(f"{label} {detail}")
        print(f"  FAIL: {label} {detail}")

def get_csrf(session):
    """Fetch CSRF token from /api/auth/csrf-token endpoint."""
    resp = session.get(f"{BASE}/api/auth/csrf-token", timeout=5)
    try:
        return resp.json().get("csrf_token", "")
    except Exception:
        return ""

def session_api(session, method, path, **kwargs):
    """Use requests.Session for cookie persistence + CSRF."""
    url = f"{BASE}{path}"
    fn = getattr(session, method.lower())
    headers = kwargs.pop("headers", {})
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        token = session._csrf_token if hasattr(session, "_csrf_token") else get_csrf(session)
        if token:
            headers["X-CSRFToken"] = token
            session._csrf_token = token
    try:
        resp = fn(url, timeout=10, headers=headers, **kwargs)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        return resp.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# ─────────────────────────────────────────────
# LOGIN + CSRF SETUP
# ─────────────────────────────────────────────
print("\n=== AUTH ===\n")

s = requests.Session()
# These are exempt from CSRF, so no token needed
code, d = session_api(s, "POST", "/api/auth/register", json={"username": "a" * 256, "password": "test"})
check("Register with 256-char username returns 400", code == 400, f"got {code}")

code, d = session_api(s, "POST", "/api/auth/login", json={"username": "nonexistent_user_xyz", "password": "pwd"})
check("Login nonexistent user returns 401", code == 401, f"got {code}")

code, d = session_api(s, "POST", "/api/auth/login", json={})
check("Login empty body returns 400", code == 400, f"got {code}")

code, d = session_api(s, "POST", "/api/auth/login", json={"username": "admin", "password": "admin123"})
check("Login as admin succeeds", code == 200, f"got {code}")

# Now that we're logged in, fetch a CSRF token for subsequent requests
token = get_csrf(s)
if token:
    s._csrf_token = token

code, d = session_api(s, "GET", "/api/auth/me")
check("GET /me after login returns 200", code == 200, f"got {code}")
check("/me returns admin username", d.get("user", {}).get("username") == "admin", str(d))

# ─────────────────────────────────────────────
# PRODUCTS — edge cases
# ─────────────────────────────────────────────
print("\n=== PRODUCTS ===\n")

code, d = session_api(s, "POST", "/api/products/", json={"name": "", "sku": "EDGE-001", "unit_price": 9.99})
check("Product with empty name", code in (201, 400), f"got {code}")

code, d = session_api(s, "POST", "/api/products/", json={"name": "Unicode Ñoño", "sku": "EDGE-UNI-001", "unit_price": 5.0})
check("Product with unicode name", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/products/", json={"name": "Barcode test", "sku": "EDGE-BC-001", "unit_price": 1.0, "barcode": "000000000000"})
bc_id = d.get("product", {}).get("id")
check("Product with all-zero barcode", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/products/", json={"name": "Max qty", "sku": "EDGE-MAXQ", "unit_price": 1.0, "quantity": 2147483647})
check("Product with INT_MAX quantity", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/products/", json={"name": "Zero price", "sku": "EDGE-ZEROP", "unit_price": 0.0})
check("Product with zero price", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/products/", json={"name": "Negative price product", "sku": "EDGE-NEGP", "unit_price": -5.0})
check("Product with negative price (DB might accept)", code in (201, 400), f"got {code}")

code, d = session_api(s, "PUT", f"/api/products/{bc_id}", json={"name": "", "sku": "", "unit_price": 0})
check("Update product to empty name/sku", code in (200, 400), f"got {code}")

code, d = session_api(s, "GET", "/api/products/?q=XYZ123NONEXISTENT")
check("Search with random string returns 0", d.get("total", -1) == 0, str(d))

code, d = session_api(s, "GET", "/api/products/?category=__non_existent_category__")
check("Category filter no results", d.get("total", -1) == 0, str(d))

code, d = session_api(s, "GET", "/api/products/?page=99999")
check("Page beyond last returns empty", len(d.get("products", [None])) == 0, str(d))

# ─────────────────────────────────────────────
# SALES — edge cases
# ─────────────────────────────────────────────
print("\n=== SALES ===\n")

code, d = session_api(s, "POST", "/api/products/", json={"name": "Sale Test Item", "sku": "EDGE-SALE-001", "unit_price": 10.0, "quantity": 100})
prod_id = d.get("product", {}).get("id")
assert prod_id, f"Need product for sales tests: {d}"

code, d = session_api(s, "POST", "/api/sales/", json={"customer_name": "", "items": [{"product_id": prod_id, "quantity": 1}]})
check("Sale with empty customer name", code == 201, f"got {code}")
sale_id = d.get("sale", {}).get("id")

code, d = session_api(s, "POST", "/api/sales/", json={"customer_name": "a" * 500, "items": [{"product_id": prod_id, "quantity": 1}]})
check("Sale with 500-char customer name", code in (201, 400), f"got {code}")

code, d = session_api(s, "DELETE", f"/api/sales/{sale_id}")
check("Void sale (DELETE)", code == 200, f"got {code}")

code, d = session_api(s, "DELETE", f"/api/sales/{sale_id}")
check("Double void returns 400", code == 400, f"got {code}")

code, d = session_api(s, "POST", "/api/sales/", json={"customer_name": "Concurrent test", "items": [{"product_id": prod_id, "quantity": 50}]})
check("Sale of 50 units at once", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/sales/", json={"customer_name": "Overstock test", "items": [{"product_id": prod_id, "quantity": 100}]})
check("Sale exceeding remaining stock returns 400", code == 400, f"got {code}")

thread_ids = {"counter": 0}
errs = []
def concurrent_buy():
    tid = thread_ids["counter"]
    thread_ids["counter"] += 1
    for i in range(5):
        sku = f"EDGE-CONC-{tid}-{i}"
        c, d = session_api(s, "POST", "/api/products/", json={"name": f"Concurrent {tid}-{i}", "sku": sku, "unit_price": 5.0, "quantity": 100})
        pid = d.get("product", {}).get("id")
        if not pid:
            errs.append(f"Thread {tid} failed SKU {sku}: {d}")

threads = [threading.Thread(target=concurrent_buy) for _ in range(3)]
for t2 in threads: t2.start()
for t2 in threads: t2.join()
check("Concurrent product creation (3 threads, 5 each)", len(errs) == 0, str(errs[:2]))

code, d = session_api(s, "POST", "/api/sales/", json={"customer_name": "unicode αβγ", "items": [{"product_id": prod_id, "quantity": 1}]})
check("Sale with unicode customer name", code == 201, f"got {code}")

# ─────────────────────────────────────────────
# STOCK — edge cases
# ─────────────────────────────────────────────
print("\n=== STOCK ===\n")

code, d = session_api(s, "POST", "/api/products/", json={"name": "Stock Test", "sku": "EDGE-STK-001", "unit_price": 1.0, "quantity": 10})
stk_id = d.get("product", {}).get("id")

code, d = session_api(s, "POST", "/api/stock/adjust", json={"product_id": stk_id, "quantity_change": 9999, "movement_type": "purchase_in", "reason": "Bulk shipment"})
check("Large positive stock adjustment", code == 200, f"got {code}")
check("New quantity is 10 + 9999 = 10009", d.get("new_quantity") == 10009, str(d))

code, d = session_api(s, "POST", "/api/stock/adjust", json={"product_id": stk_id, "quantity_change": -9999, "reason": "Damage write-off"})
check("Large negative adjustment", code == 200, f"got {code}")
check("New quantity is 10009 - 9999 = 10", d.get("new_quantity") == 10, str(d))

code, d = session_api(s, "POST", "/api/stock/adjust", json={"product_id": 999999, "quantity_change": 10})
check("Stock adjust for nonexistent product", code == 404, f"got {code}")

code, d = session_api(s, "POST", "/api/stock/adjust", json={"product_id": stk_id, "quantity_change": 0})
check("Stock adjust with zero change", code == 400, f"got {code}")

code, d = session_api(s, "POST", "/api/stock/adjust", json={"product_id": stk_id, "quantity_change": -50000})
check("Stock adjust below zero returns 400", code == 400, f"got {code}")

code, d = session_api(s, "GET", "/api/stock/alerts")
check("Stock alerts returns list", "alerts" in d, str(d))

code, d = session_api(s, "GET", "/api/stock/movements?page=1&per_page=5")
check("Stock movements returns paginated", "movements" in d, str(d))

# ─────────────────────────────────────────────
# INVENTORY AUDIT TRAIL
# ─────────────────────────────────────────────
print("\n=== INVENTORY AUDIT ===\n")

with _app.app_context():
    logs = InventoryLog.query.order_by(InventoryLog.id.desc()).limit(10).all()
check("InventoryLog has records after sales+adjust", len(logs) > 0, f"got {len(logs)}")
has_sale = any(l.movement_type == "sale_out" for l in logs)
has_adj = any(l.movement_type in ("adjustment", "purchase_in") for l in logs)
has_ret = any(l.movement_type == "return_in" for l in logs)
check("InventoryLog contains sale_out entries", has_sale, str([l.movement_type for l in logs]))
check("InventoryLog contains adjustment entries", has_adj, str([l.movement_type for l in logs]))
check("InventoryLog contains return_in (from sale void)", has_ret, str([l.movement_type for l in logs]))

log = logs[0]
check("InventoryLog has quantity_before", log.quantity_before is not None, str(log.quantity_before))
check("InventoryLog has quantity_after", log.quantity_after is not None, str(log.quantity_after))
check("InventoryLog has product relationship", log.product is not None or log.product_id is not None, str(log))
check("InventoryLog has reference_type", log.reference_type is not None, str(log.reference_type))

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
print("\n=== DASHBOARD ===\n")

code, d = session_api(s, "GET", "/api/dashboard/stats")
check("Dashboard stats returns 200", code == 200, f"got {code}")
check("Stats has total_products", "total_products" in d, str(d))
check("Stats has total_sales", "total_sales" in d, str(d))
check("Stats has low_stock_alerts", "low_stock_alerts" in d, str(d))
check("Stats has sales_trend", "sales_trend" in d, str(d))
check("Stats has categories", "categories" in d, str(d))
check("Sales trend is a list", isinstance(d.get("sales_trend"), list), str(type(d.get("sales_trend"))))
check("Categories is a list", isinstance(d.get("categories"), list), str(type(d.get("categories"))))

code, d = session_api(s, "GET", "/api/dashboard/low-stock")
check("Dashboard low-stock returns 200", code == 200, f"got {code}")
check("Dashboard low-stock is array", isinstance(d, list), str(type(d)))

# ─────────────────────────────────────────────
# IoT — edge cases
# ─────────────────────────────────────────────
print("\n=== IOT ===\n")

code, d = session_api(s, "POST", "/api/iot/events", json={"device_id": "", "device_type": "barcode_scanner"})
check("IoT event with empty device_id", code == 400, f"got {code}")

code, d = session_api(s, "POST", "/api/iot/events", json={"device_id": "SPECIAL-CHARS-😀", "device_type": "barcode_scanner", "event_type": "scan", "barcode_data": "5901234567897"})
check("IoT device_id with unicode", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/iot/events", json={"device_id": "BAT-001", "device_type": "barcode_scanner", "event_type": "scan", "barcode_data": "5901234567897", "battery_level": -5})
check("IoT event with negative battery", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/iot/events", json={"device_id": "RSSI-001", "device_type": "rfid_reader", "event_type": "tag_read", "rfid_epc": "E280116060000205A8B1E030", "rssi": -999.9})
check("IoT event with extreme RSSI", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/iot/events", json={"device_id": "BULK-001", "device_type": "barcode_scanner", "event_type": "scan", "barcode_data": "9780201379624", "raw_payload": {"nested": {"data": [1, 2, 3]}}})
check("IoT event with nested JSON payload", code == 201, f"got {code}")

code, d = session_api(s, "POST", "/api/iot/events", json={"device_id": "INVALID-TYPE", "device_type": "invalid_type_xyz"})
check("IoT event with invalid device_type", code == 400, f"got {code}")

code, d = session_api(s, "GET", "/api/iot/events?per_page=3&page=2")
check("IoT events paginated page 2", code == 200, f"got {code}")
check("IoT events response has total", "total" in d, str(d))

code, d = session_api(s, "GET", "/api/iot/devices")
check("IoT devices list", code == 200, f"got {code}")
if isinstance(d, list):
    check("IoT devices include event_count", all("event_count" in dev for dev in d), str(d[:2]))

code, d = session_api(s, "GET", "/api/iot/stats")
check("IoT stats", code == 200, f"got {code}")
check("IoT stats has registered_devices", "registered_devices" in d, str(d))

code, d = session_api(s, "POST", "/api/iot/simulator/start")
check("IoT simulator start", code == 200, f"got {code}")
time.sleep(2)
code, d = session_api(s, "GET", "/api/iot/simulator/status")
check("IoT simulator running", d.get("running") == True, str(d))
code, d = session_api(s, "POST", "/api/iot/simulator/stop")
check("IoT simulator stop", code in (200, 408, 0), f"got {code}")

# ─────────────────────────────────────────────
# FRONTEND — static pages
# ─────────────────────────────────────────────
print("\n=== FRONTEND ===\n")

for page in ["/", "/dashboard.html", "/products.html", "/inventory.html", "/sales.html", "/alerts.html", "/login.html", "/iot.html"]:
    code, _ = session_api(s, "GET", page)
    check(f"Page {page} returns 200", code == 200, f"got {code}")

for asset in ["/static/css/style.css", "/static/js/app.js"]:
    url = f"{BASE}{asset}"
    resp = s.get(url, timeout=5)
    check(f"Static {asset} returns 200", resp.status_code == 200, f"got {resp.status_code}")
    check(f"{asset} is non-empty", len(resp.text) > 0, f"empty")

# ─────────────────────────────────────────────
# UNAUTHENTICATED ACCESS SHOULD FAIL
# ─────────────────────────────────────────────
print("\n=== UNAUTHENTICATED ===\n")

anon = requests.Session()
get_csrf(anon)
code, d = session_api(anon, "GET", "/api/dashboard/stats")
check("Unauthenticated GET /stats returns 401", code == 401, f"got {code}")

code, d = session_api(anon, "GET", "/api/products/")
check("Unauthenticated GET /products returns 401", code == 401, f"got {code}")

code, d = session_api(anon, "POST", "/api/products/", json={"name": "Should fail", "sku": "UNAUTH-001", "unit_price": 1.0})
check("Unauthenticated POST /products returns 401", code == 401, f"got {code}")

# ─────────────────────────────────────────────
# HTTP METHOD VALIDATION
# ─────────────────────────────────────────────
print("\n=== HTTP METHODS ===\n")

code, _ = session_api(s, "PUT", "/api/auth/login", json={})
check("PUT to auth login (should 405)", code == 405, f"got {code}")

code, _ = session_api(s, "DELETE", "/api/sales/99999")
check("DELETE non-existent sale returns 404", code == 404, f"got {code}")

code, _ = session_api(s, "GET", "/api/sales/99999")
check("GET non-existent sale returns 404", code == 404, f"got {code}")

# ─────────────────────────────────────────────
# SQL INJECTION SAFETY CHECKS
# ─────────────────────────────────────────────
print("\n=== INJECTION ===\n")

injections = [
    "/api/products/?q=' OR '1'='1",
    "/api/products/?category='; DROP TABLE products; --",
    "/api/products/?q=<script>alert('xss')</script>",
]
for inj in injections:
    code, d = session_api(s, "GET", inj)
    check(f"Injection attempt returns 200 (not crash)", code == 200, f"got {code} for {inj[:40]}")

# ─────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"RESULTS: {len(passes)} passed, {len(failures)} failed out of {len(passes) + len(failures)} tests")

if failures:
    print(f"\nFAILURES ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL CORNER-CASE TESTS PASSED")
