"""
Edge-Case Tests for Smart Inventory API
========================================
Tests all endpoints with error conditions, boundary values, and invalid inputs.
Run with:  python scripts/test_edge_cases.py
Requires MySQL database with tables already created (run schema.sql first).
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import create_app

app = create_app(test_config={"WTF_CSRF_ENABLED": False, "TESTING": True})
uid = str(int(time.time()))[-6:]  # unique suffix for test data
client = app.test_client()
pass_count = 0
fail_count = 0

# Authenticate via test client session
with client.session_transaction() as sess:
    sess["user_id"] = 1
    sess["username"] = "admin"


def test(name, condition):
    global pass_count, fail_count
    if condition:
        pass_count += 1
        print(f"  PASS: {name}")
    else:
        fail_count += 1
        print(f"  FAIL: {name}")


# ── Products ────────────────────────────────────────────────────────────

# 1. Missing required fields
r = client.post("/api/products/", json={"name": "No SKU"})
test("Missing SKU returns 400", r.status_code == 400)

# 2. Empty body
r = client.post("/api/products/", json={})
test("Empty product body returns 400", r.status_code == 400)

# 3. Duplicate SKU
sku_a = f"EDGE-SKU-A-{uid}"
r = client.post("/api/products/", json={"name": "P1", "sku": sku_a, "unit_price": 5.0})
assert r.status_code == 201
r = client.post("/api/products/", json={"name": "P2", "sku": sku_a, "unit_price": 5.0})
test("Duplicate SKU returns 409", r.status_code == 409)

# 4. Duplicate barcode
bar_a = f"EDGE-BAR-{uid}"
r = client.post("/api/products/", json={"name": "P3", "sku": f"EDGE-SKU-B-{uid}", "unit_price": 5.0, "barcode": bar_a})
assert r.status_code == 201
r = client.post("/api/products/", json={"name": "P4", "sku": f"EDGE-SKU-C-{uid}", "unit_price": 5.0, "barcode": bar_a})
test("Duplicate barcode returns 409", r.status_code == 409)

# 5. Invalid supplier_id
r = client.post("/api/products/", json={"name": "P5", "sku": f"EDGE-SKU-D-{uid}", "unit_price": 5.0, "supplier_id": 9999})
test("Invalid supplier returns 404", r.status_code == 404)

# 6. Zero price (should be allowed per schema)
r = client.post("/api/products/", json={"name": "Free Item", "sku": f"EDGE-SKU-E-{uid}", "unit_price": 0})
test("Zero price product accepted", r.status_code == 201)
pid_free = r.get_json()["product"]["id"]

# 7. Negative quantity
r = client.post("/api/products/", json={"name": "Neg Qty", "sku": f"EDGE-SKU-F-{uid}", "unit_price": 5.0, "quantity": -5})
test("Negative quantity accepted (no DB CHECK constraint)", r.status_code == 201)

# 8. Get nonexistent product
r = client.get("/api/products/999999")
test("Get nonexistent product returns 404", r.status_code == 404)

# 9. Update nonexistent product
r = client.put("/api/products/999999", json={"name": "Ghost"})
test("Update nonexistent product returns 404", r.status_code == 404)

# 10. Delete nonexistent product
r = client.delete("/api/products/999999")
test("Delete nonexistent product returns 404", r.status_code == 404)

# 11. Update with duplicate SKU
sku_src = f"EDGE-UPD-SRC-{uid}"
sku_tgt = f"EDGE-UPD-TGT-{uid}"
r = client.post("/api/products/", json={"name": "Update Source", "sku": sku_src, "unit_price": 1.0})
assert r.status_code == 201
r = client.post("/api/products/", json={"name": "Update Target", "sku": sku_tgt, "unit_price": 1.0})
assert r.status_code == 201
pid_target = r.get_json()["product"]["id"]
r = client.put(f"/api/products/{pid_target}", json={"sku": sku_src})
test("Update to duplicate SKU returns 409", r.status_code == 409)

# 12. Search with no results
r = client.get("/api/products/?q=ZZZZNONEXISTENT")
data = r.get_json()
test("Search no results returns empty list", len(data["products"]) == 0)

# 13. Category filter with no matches
r = client.get("/api/products/?category=NonExistentCategory")
data = r.get_json()
test("Category filter no matches returns empty list", len(data["products"]) == 0)

# 14. Navigation beyond last page
r = client.get("/api/products/?page=9999")
data = r.get_json()
test("Page beyond last returns empty list", len(data["products"]) == 0)

# ── Sales ───────────────────────────────────────────────────────────────

# 15. Sale with no items
r = client.post("/api/sales/", json={"customer_name": "No Items"})
test("Sale with no items returns 400", r.status_code == 400)

r = client.post("/api/sales/", json={"customer_name": "No Items", "items": []})
test("Sale with empty items returns 400", r.status_code == 400)

# 16. Sale with nonexistent product
r = client.post("/api/sales/", json={"items": [{"product_id": 999999, "quantity": 1}]})
test("Sale nonexistent product returns 404", r.status_code == 404)

# 17. Sale exceeding stock (use the free item which has qty 0)
if pid_free:
    r = client.post("/api/sales/", json={"items": [{"product_id": pid_free, "quantity": 999}]})
    test("Sale exceeding stock returns 400", r.status_code == 400)

# 18. Sale missing product_id
r = client.post("/api/sales/", json={"items": [{"quantity": 1}]})
test("Sale missing product_id returns 400", r.status_code == 400)

# 19. Sale missing quantity
r = client.post("/api/sales/", json={"items": [{"product_id": 1}]})
test("Sale missing quantity returns 400", r.status_code == 400)

# 20. Successful sale (use a known product)
r = client.get("/api/products/")
data = r.get_json()
if data["products"]:
    first_id = data["products"][0]["id"]
    first_qty = data["products"][0]["quantity"]
    purchase_qty = min(1, first_qty)
    if purchase_qty > 0:
        r = client.post("/api/sales/", json={
            "customer_name": "Edge Test",
            "items": [{"product_id": first_id, "quantity": purchase_qty}]
        })
        test(f"Successful sale returns 201", r.status_code == 201)

        # Verify stock was deducted
        r2 = client.get(f"/api/products/{first_id}")
        new_qty = r2.get_json()["product"]["quantity"]
        test(f"Stock deducted correctly", new_qty == first_qty - purchase_qty)

# 21. Get nonexistent sale
r = client.get("/api/sales/999999")
test("Get nonexistent sale returns 404", r.status_code == 404)

# ── Stock ───────────────────────────────────────────────────────────────

# 22. Stock adjust with no body
r = client.post("/api/stock/adjust", json={})
test("Stock adjust empty body returns 400", r.status_code == 400)

# 23. Stock adjust with zero change
r = client.post("/api/stock/adjust", json={"product_id": 1, "quantity_change": 0})
test("Stock adjust zero change returns 400", r.status_code == 400)

# 24. Stock adjust nonexistent product
r = client.post("/api/stock/adjust", json={"product_id": 999999, "quantity_change": 10})
test("Stock adjust nonexistent product returns 404", r.status_code == 404)

# 25. Stock adjust below zero (use a product we created)
r = client.post("/api/products/", json={"name": "Edge Stock Test", "sku": f"EDGE-STOCK-{uid}", "unit_price": 5.0, "quantity": 10})
assert r.status_code == 201
stk_pid = r.get_json()["product"]["id"]
r = client.post("/api/stock/adjust", json={"product_id": stk_pid, "quantity_change": -999999})
test("Stock adjust below zero returns 400", r.status_code == 400)

# 26. Alerts endpoint returns valid response
r = client.get("/api/stock/alerts")
data = r.get_json()
test("Stock alerts returns alert_count", "alert_count" in data)

# 27. Resolve alert missing product_id
r = client.patch("/api/stock/alerts/resolve", json={})
test("Resolve alert no product_id returns 400", r.status_code == 400)

# 28. Resolve alert nonexistent product
r = client.patch("/api/stock/alerts/resolve", json={"product_id": 999999})
test("Resolve alert nonexistent product returns 404", r.status_code == 404)

# 29. Movements endpoint
r = client.get("/api/stock/movements")
test("Stock movements returns 200", r.status_code == 200)
data = r.get_json()
test("Stock movements has movements key", "movements" in data)

# ── Dashboard ───────────────────────────────────────────────────────────

# 30. Dashboard stats
r = client.get("/api/dashboard/stats")
test("Dashboard stats returns 200", r.status_code == 200)
data = r.get_json()
test("Dashboard stats has total_products", "total_products" in data)
test("Dashboard stats has total_sales", "total_sales" in data)
test("Dashboard stats has low_stock_alerts", "low_stock_alerts" in data)

# 31. Dashboard low-stock
r = client.get("/api/dashboard/low-stock")
test("Dashboard low-stock returns 200", r.status_code == 200)
data = r.get_json()
test("Dashboard low-stock is array", isinstance(data, list))

# ── Products Categories ─────────────────────────────────────────────────

# 32. Products categories returns list
r = client.get("/api/products/categories")
test("Products categories returns 200", r.status_code == 200)
data = r.get_json()
test("Products categories is array", isinstance(data, list))

# ── Auth ────────────────────────────────────────────────────────────────

# 33. Login with wrong password
r = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
test("Login wrong password returns 401", r.status_code == 401)

# 34. Login with nonexistent user
r = client.post("/api/auth/login", json={"username": "nonexistent_user_xyz", "password": "test"})
test("Login nonexistent user returns 401", r.status_code == 401)

# 35. Login missing fields
r = client.post("/api/auth/login", json={})
test("Login missing fields returns 400", r.status_code == 400)

# 36. Register duplicate username
test_user = f"edge_test_{uid}"
r = client.post("/api/auth/register", json={"username": test_user, "email": f"{test_user}@test.com", "password": "test123"})
assert r.status_code == 201
r = client.post("/api/auth/register", json={"username": test_user, "password": "test123"})
test("Register duplicate username returns 409", r.status_code == 409)

# 37. Register missing fields
r = client.post("/api/auth/register", json={})
test("Register missing fields returns 400", r.status_code == 400)

# 38. Me without login (create temporary client without session)
anon_client = app.test_client()
r = anon_client.get("/api/auth/me")
test("Me without login returns 401", r.status_code == 401)

# ── Frontend Pages ──────────────────────────────────────────────────────

# 39. Frontend pages load
pages = ["/dashboard.html", "/products.html", "/inventory.html", "/sales.html", "/alerts.html", "/login.html"]
for page in pages:
    r = client.get(page)
    test(f"Page {page} returns 200", r.status_code == 200)

# 40. Static files
static_files = ["/static/css/style.css", "/static/js/app.js"]
for f in static_files:
    r = client.get(f)
    test(f"Static {f} returns 200", r.status_code == 200)

# ── Health ──────────────────────────────────────────────────────────────

# 41. Health endpoint
r = client.get("/health")
test("Health returns 200", r.status_code == 200)
data = r.get_json()
test("Health has status ok", data.get("status") == "ok")


# ── Summary ─────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"RESULTS: {pass_count} passed, {fail_count} failed out of {pass_count + fail_count} tests")
if fail_count > 0:
    sys.exit(1)
else:
    print("ALL EDGE-CASE TESTS PASSED")
