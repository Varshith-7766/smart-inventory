import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


def test_create_sale(client, db):
    from models import Category, Product
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-001", unit_price=10.0, quantity=50, category_id=cat.id, category="TestCat", user_id=1)
    db.session.add(product)
    db.session.commit()

    response = client.post("/api/sales/", json={
        "customer_name": "Test Customer",
        "items": [{"product_id": product.id, "quantity": 3}],
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["sale"]["total_amount"] == 30.0


def test_sale_uses_product_price_not_client_price(client, db):
    """Client-supplied unit_price must be ignored (price tampering fix)."""
    from models import Category, Product
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-002", unit_price=10.0, quantity=50, category_id=cat.id, category="TestCat", user_id=1)
    db.session.add(product)
    db.session.commit()

    response = client.post("/api/sales/", json={
        "items": [{"product_id": product.id, "quantity": 2, "unit_price": 0.01}],
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["sale"]["total_amount"] == 20.0


def test_sale_insufficient_stock(client, db):
    from models import Category, Product
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-003", unit_price=10.0, quantity=1, category_id=cat.id, category="TestCat", user_id=1)
    db.session.add(product)
    db.session.commit()

    response = client.post("/api/sales/", json={
        "items": [{"product_id": product.id, "quantity": 5}],
    })
    assert response.status_code == 400


def test_sale_negative_quantity_rejected(client, db):
    from models import Category, Product
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-004", unit_price=10.0, quantity=50, category_id=cat.id, category="TestCat", user_id=1)
    db.session.add(product)
    db.session.commit()

    response = client.post("/api/sales/", json={
        "items": [{"product_id": product.id, "quantity": -3}],
    })
    assert response.status_code == 400