import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


def test_adjust_stock(client, db):
    from models import Category, Product
    cat = Category(name="TestCat")
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-001", unit_price=10.0, quantity=50, category_id=cat.id, category="TestCat")
    db.session.add(product)
    db.session.commit()

    response = client.post("/api/stock/adjust", json={
        "product_id": product.id,
        "quantity_change": -10,
        "reason": "adjustment",
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["new_quantity"] == 40
