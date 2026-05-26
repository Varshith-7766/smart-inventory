import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


def test_create_product(client, db):
    from models import Category
    cat = Category(name="TestCat")
    db.session.add(cat)
    db.session.commit()

    response = client.post("/api/products/", json={
        "name": "Test Product",
        "sku": "TST-001",
        "unit_price": 10.99,
        "category_id": cat.id,
        "category": "TestCat",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "Product added successfully"


def test_list_products(client, db):
    from models import Category, Product
    cat = Category(name="TestCat")
    db.session.add(cat)
    db.session.commit()
    db.session.add(Product(name="P1", sku="P-001", unit_price=5.0, category_id=cat.id, category="TestCat"))
    db.session.commit()

    response = client.get("/api/products/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 1
