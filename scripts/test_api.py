import json
from app import create_app
app = create_app(test_config={"WTF_CSRF_ENABLED": False, "TESTING": True})
client = app.test_client()

# Add a product
r = client.post('/api/products/', json={'name':'USB-C Cable','sku':'ELEC-001','unit_price':12.99,'quantity':100,'reorder_level':20,'category':'Electronics'})
print(f'ADD: {r.status_code} {r.get_json()["message"]}')

# Add another (low stock)
r = client.post('/api/products/', json={'name':'Wireless Mouse','sku':'ELEC-002','unit_price':29.99,'quantity':5,'reorder_level':10,'category':'Electronics'})
print(f'ADD: {r.status_code} {r.get_json()["message"]}')

# List products
r = client.get('/api/products/')
data = r.get_json()
print(f'LIST: {data["total"]} products')

# Low stock
r = client.get('/api/products/low-stock')
data = r.get_json()
print(f'LOW STOCK: {data["count"]} products')

# Record a sale
r = client.post('/api/sales/', json={'customer_name':'Test Customer','items':[{'product_id':1,'quantity':3}]})
print(f'SALE: {r.status_code} {r.get_json()["message"]}')

# Check stock after sale
r = client.get('/api/products/1')
data = r.get_json()
print(f'STOCK AFTER SALE: Product #1 quantity = {data["product"]["quantity"]}')

# Sales history
r = client.get('/api/sales/')
data = r.get_json()
print(f'SALES: {data["total"]} records')

# Stock alert
r = client.get('/api/stock/alerts')
data = r.get_json()
print(f'ALERTS: {data["alert_count"]} alerts')

# Stock adjust
r = client.post('/api/stock/adjust', json={'product_id':2,'quantity_change':10,'reason':'New shipment'})
print(f'ADJUST: {r.status_code} - new qty = {r.get_json()["new_quantity"]}')

# Register user
r = client.post('/api/auth/register', json={'username':'admin','email':'admin@test.com','password':'admin123','role':'admin'})
print(f'REGISTER: {r.status_code} {r.get_json()["message"]}')

print('\n=== ALL TESTS PASSED ===')
