"""
API Testing Examples
====================
A standalone script that demonstrates how to interact with every
endpoint of the Smart Inventory API.

This uses the `requests` library.  Install it first:
    pip install requests

Usage:
    # Make sure app.py is running in another terminal:
    python app.py

    # Then run this script:
    python api_examples.py
"""

import json
import requests

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
BASE_URL = "http://localhost:5000/api"
HEADERS = {"Content-Type": "application/json"}


def print_response(label, response):
    """Pretty-print an API response."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Status: {response.status_code}")
    print(f"{'='*60}")
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)
    print()


def run_all_examples():
    """
    Runs through every API endpoint in logical order:

      1. Auth    → Register / Login
      2. Products → Create / List / Update / Delete / Low-Stock
      3. Stock   → Adjust / Alerts
      4. Sales   → Record / List
    """

    # ==================================================================
    # 1. AUTH
    # ==================================================================

    # --- 1a. Register a new user ---
    print_response("REGISTER USER", requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "username": "demo_user",
            "email": "demo@example.com",
            "password": "demo1234",
            "role": "admin",
        },
        headers=HEADERS,
    ))

    # --- 1b. Login (stores a session cookie) ---
    # We use a `session` object so the cookie is preserved for subsequent requests.
    session = requests.Session()
    print_response("LOGIN", session.post(
        f"{BASE_URL}/auth/login",
        json={"username": "demo_user", "password": "demo1234"},
        headers=HEADERS,
    ))

    # --- 1c. Get current user ---
    print_response("GET CURRENT USER", session.get(
        f"{BASE_URL}/auth/me",
        headers=HEADERS,
    ))

    # ==================================================================
    # 2. PRODUCTS
    # ==================================================================

    # --- 2a. Add products ---
    print_response("ADD PRODUCT 1", session.post(
        f"{BASE_URL}/products/",
        json={
            "name": "USB-C Cable 1m",
            "sku": "ELEC-001",
            "description": "High-speed USB-C charging cable, braided nylon",
            "quantity": 100,
            "reorder_level": 20,
            "unit_price": 12.99,
            "category": "Electronics",
            "barcode": "5901234567897",
        },
        headers=HEADERS,
    ))

    print_response("ADD PRODUCT 2", session.post(
        f"{BASE_URL}/products/",
        json={
            "name": "Wireless Mouse",
            "sku": "ELEC-002",
            "description": "Ergonomic Bluetooth 5.0 wireless mouse",
            "quantity": 45,
            "reorder_level": 10,
            "unit_price": 29.99,
            "category": "Electronics",
        },
        headers=HEADERS,
    ))

    print_response("ADD PRODUCT 3 (low stock)", session.post(
        f"{BASE_URL}/products/",
        json={
            "name": "Denim Jacket",
            "sku": "CLTH-001",
            "quantity": 3,
            "reorder_level": 10,
            "unit_price": 59.99,
            "category": "Clothing",
        },
        headers=HEADERS,
    ))

    # --- 2b. List all products ---
    print_response("LIST PRODUCTS", session.get(
        f"{BASE_URL}/products/",
        headers=HEADERS,
    ))

    # --- 2c. Search products by name ---
    print_response("SEARCH PRODUCTS (keyword='mouse')", session.get(
        f"{BASE_URL}/products/?q=mouse",
        headers=HEADERS,
    ))

    # --- 2d. Get single product (ID=1) ---
    print_response("GET PRODUCT #1", session.get(
        f"{BASE_URL}/products/1",
        headers=HEADERS,
    ))

    # --- 2e. Update product (change price of product #2) ---
    print_response("UPDATE PRODUCT #2 (price change)", session.put(
        f"{BASE_URL}/products/2",
        json={"unit_price": 24.99},
        headers=HEADERS,
    ))

    # --- 2f. Low-stock alerts (should show Denim Jacket: qty=3 <= reorder=10) ---
    print_response("LOW STOCK PRODUCTS", session.get(
        f"{BASE_URL}/products/low-stock",
        headers=HEADERS,
    ))

    # ==================================================================
    # 3. STOCK
    # ==================================================================

    # --- 3a. Adjust stock (add 50 units to product #1) ---
    print_response("ADJUST STOCK (+50 to Product #1)", session.post(
        f"{BASE_URL}/stock/adjust",
        json={
            "product_id": 1,
            "quantity_change": 50,
            "reason": "New shipment arrived",
        },
        headers=HEADERS,
    ))

    # --- 3b. Adjust stock (remove stock — damage) ---
    print_response("ADJUST STOCK (-5 from Product #2, damage)", session.post(
        f"{BASE_URL}/stock/adjust",
        json={
            "product_id": 2,
            "quantity_change": -5,
            "reason": "Damaged in warehouse",
        },
        headers=HEADERS,
    ))

    # --- 3c. List current alerts (live query) ---
    print_response("STOCK ALERTS", session.get(
        f"{BASE_URL}/stock/alerts",
        headers=HEADERS,
    ))

    # --- 3d. Resolve alert for product #3 ---
    print_response("RESOLVE ALERT for Product #3", session.patch(
        f"{BASE_URL}/stock/alerts/resolve",
        json={"product_id": 3},
        headers=HEADERS,
    ))

    # ==================================================================
    # 4. SALES
    # ==================================================================

    # --- 4a. Record a sale ---
    print_response("RECORD SALE", session.post(
        f"{BASE_URL}/sales/",
        json={
            "customer_name": "Alice Johnson",
            "notes": "Walk-in customer, paid by card",
            "items": [
                {"product_id": 1, "quantity": 2},
                {"product_id": 2, "quantity": 1},
            ],
        },
        headers=HEADERS,
    ))

    # --- 4b. List sales history ---
    print_response("SALES HISTORY", session.get(
        f"{BASE_URL}/sales/",
        headers=HEADERS,
    ))

    # --- 4c. Get single sale detail (ID=1) ---
    print_response("GET SALE #1", session.get(
        f"{BASE_URL}/sales/1",
        headers=HEADERS,
    ))

    # --- 4d. Filter sales by date range ---
    print_response("SALES IN MAY 2026", session.get(
        f"{BASE_URL}/sales/?start_date=2026-05-01&end_date=2026-05-31",
        headers=HEADERS,
    ))

    # --- 4e. Verify stock was deducted after the sale ---
    print_response("VERIFY STOCK AFTER SALE (Product #1)", session.get(
        f"{BASE_URL}/products/1",
        headers=HEADERS,
    ))

    # ==================================================================
    # 5. DELETE a product (soft-delete)
    # ==================================================================
    print_response("DELETE PRODUCT #3", session.delete(
        f"{BASE_URL}/products/3",
        headers=HEADERS,
    ))

    # Verify it's no longer in the list
    print_response("LIST PRODUCTS (after delete)", session.get(
        f"{BASE_URL}/products/",
        headers=HEADERS,
    ))

    print("\n✅ All API examples completed successfully!")


if __name__ == "__main__":
    run_all_examples()
