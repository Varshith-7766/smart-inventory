import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


def test_adjust_stock(client, db):
    from models import Category, Product
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-001", unit_price=10.0, quantity=50, category_id=cat.id, category="TestCat", user_id=1)
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


def test_adjust_stock_below_zero_rejected(client, db):
    from models import Category, Product
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-002", unit_price=10.0, quantity=5, category_id=cat.id, category="TestCat", user_id=1)
    db.session.add(product)
    db.session.commit()

    response = client.post("/api/stock/adjust", json={
        "product_id": product.id,
        "quantity_change": -10,
        "reason": "adjustment",
    })
    assert response.status_code == 400


def test_adjust_stock_bad_type_rejected(client, db):
    from models import Category, Product
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-003", unit_price=10.0, quantity=5, category_id=cat.id, category="TestCat", user_id=1)
    db.session.add(product)
    db.session.commit()

    response = client.post("/api/stock/adjust", json={
        "product_id": product.id,
        "quantity_change": "not-a-number",
        "reason": "adjustment",
    })
    assert response.status_code == 400


def test_resolve_alert_persists(client, db):
    from models import Category, Product, AlertResolution
    cat = Category(name="TestCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    product = Product(name="P1", sku="P-004", unit_price=10.0, quantity=2, reorder_level=10, category_id=cat.id, category="TestCat", user_id=1)
    db.session.add(product)
    db.session.commit()

    response = client.patch("/api/stock/alerts/resolve", json={"product_id": product.id})
    assert response.status_code == 200
    assert response.get_json()["resolved_at"] is not None

    resolution = AlertResolution.query.filter_by(user_id=1, product_id=product.id).first()
    assert resolution is not None