import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app

app = create_app(test_config={"WTF_CSRF_ENABLED": False, "TESTING": True})
client = app.test_client()

suffix = str(int(time.time()))[-6:]

# --- Auth first: log in as the seeded admin ---
r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
print(f'LOGIN: {r.status_code} {r.get_json().get("message", r.get_json())}')
if r.status_code != 200:
    print('Make sure the database is seeded first: python scripts/seed_data.py')
    raise SystemExit(1)

# Add a product (unique SKU so re-runs work against a seeded DB)
r = client.post('/api/products/', json={'name': f'USB-C Cable {suffix}', 'sku': f'ELEC-1{suffix}', 'unit_price': 12.99, 'quantity': 100, 'reorder_level': 20, 'category': 'Electronics'})
print(f'ADD: {r.status_code} {r.get_json().get("message", r.get_json())}')
if r.status_code not in (200, 201):
    raise SystemExit(1)
prod1 = r.get_json()["product"]["id"]

# Add another (low stock)
r = client.post('/api/products/', json={'name': f'Wireless Mouse {suffix}', 'sku': f'ELEC-2{suffix}', 'unit_price': 29.99, 'quantity': 5, 'reorder_level': 10, 'category': 'Electronics'})
print(f'ADD: {r.status_code} {r.get_json().get("message", r.get_json())}')
if r.status_code not in (200, 201):
    raise SystemExit(1)
prod2 = r.get_json()["product"]["id"]

# List products
r = client.get('/api/products/')
data = r.get_json()
print(f'LIST: {data["total"]} products')

# Low stock
r = client.get('/api/products/low-stock')
data = r.get_json()
print(f'LOW STOCK: {data["count"]} products')

# Record a sale
r = client.post('/api/sales/', json={'customer_name': 'Test Customer', 'items': [{'product_id': prod1, 'quantity': 3}]})
print(f'SALE: {r.status_code} {r.get_json().get("message", r.get_json())}')
if r.status_code not in (200, 201):
    raise SystemExit(1)

# Check stock after sale
r = client.get(f'/api/products/{prod1}')
data = r.get_json()
print(f'STOCK AFTER SALE: Product #{prod1} quantity = {data["product"]["quantity"]} (expect 97)')

# Sales history
r = client.get('/api/sales/')
data = r.get_json()
print(f'SALES: {data["total"]} records')

# Stock alert
r = client.get('/api/stock/alerts')
data = r.get_json()
print(f'ALERTS: {data["alert_count"]} alerts')

# Stock adjust
r = client.post('/api/stock/adjust', json={'product_id': prod2, 'quantity_change': 10, 'reason': 'New shipment'})
print(f'ADJUST: {r.status_code} - new qty = {r.get_json()["new_quantity"]}')

# Register a new user — the client-supplied "role" is always ignored,
# new accounts are viewers only.
uname = f'newuser{suffix}'
r = client.post('/api/auth/register', json={'username': uname, 'email': f'{uname}@test.com', 'password': 'password123', 'role': 'admin'})
print(f'REGISTER: {r.status_code} {r.get_json().get("message", r.get_json())}')
role = r.get_json().get("user", {}).get("role")
print(f'ROLE (should be viewer, not admin): {role}')

# A viewer must NOT be able to create products
r2 = client.post('/api/auth/logout')
v = app.test_client()
r = v.post('/api/auth/login', json={'username': uname, 'password': 'password123'})
print(f'VIEWER LOGIN: {r.status_code}')
r = v.post('/api/products/', json={'name': 'Blocked', 'sku': f'BLOCKED-{suffix}', 'unit_price': 1.0, 'category': 'General'})
print(f'VIEWER CREATE PRODUCT (should be 403): {r.status_code}')
if r.status_code != 403:
    print('FAIL: viewer was able to create a product!')
    raise SystemExit(1)

print('\n=== ALL TESTS PASSED ===')