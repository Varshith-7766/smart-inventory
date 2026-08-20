import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from database import db, utcnow
from models import User, Category, Supplier, Product, Sale, SaleItem
from datetime import timedelta
import random

app = create_app()

with app.app_context():
    db.create_all()

    if User.query.first():
        print("Database already seeded. Skipping.")
        sys.exit(0)

    admin = User(username="admin", email="admin@inventory.com", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.flush()

    uid = admin.id

    categories = [
        Category(name="Electronics", description="Electronic components and devices", user_id=uid),
        Category(name="Clothing", description="Apparel and fashion items", user_id=uid),
        Category(name="Food & Beverages", description="Edible goods and drinks", user_id=uid),
    ]
    db.session.add_all(categories)
    db.session.flush()

    suppliers = [
        Supplier(name="TechDistributor Inc.", contact_person="John Smith", email="john@techdist.com", user_id=uid),
        Supplier(name="FashionWholesale Ltd.", contact_person="Sarah Lee", email="sarah@fashionwl.com", user_id=uid),
    ]
    db.session.add_all(suppliers)
    db.session.flush()

    products = [
        Product(name="USB-C Cable 1m", sku="ELEC-001", quantity=150, reorder_level=20, unit_price=12.99, category_id=categories[0].id, supplier_id=suppliers[0].id, category="Electronics", user_id=uid),
        Product(name="Wireless Mouse", sku="ELEC-002", quantity=45, reorder_level=10, unit_price=29.99, category_id=categories[0].id, supplier_id=suppliers[0].id, category="Electronics", user_id=uid),
        Product(name="Cotton T-Shirt", sku="CLTH-001", quantity=80, reorder_level=15, unit_price=19.99, category_id=categories[1].id, supplier_id=suppliers[1].id, category="Clothing", user_id=uid),
        Product(name="Green Tea (50 bags)", sku="FOOD-001", quantity=200, reorder_level=30, unit_price=8.99, category_id=categories[2].id, category="Food & Beverages", user_id=uid),
        Product(name="Sparkling Water Case", sku="FOOD-002", quantity=60, reorder_level=20, unit_price=15.99, category_id=categories[2].id, category="Food & Beverages", user_id=uid),
    ]
    db.session.add_all(products)
    db.session.flush()

    today = utcnow()
    for day_offset in range(60, 0, -1):
        sale_date = today - timedelta(days=day_offset)
        for product in products:
            if random.random() < 0.3:
                qty = random.randint(1, 5)
                total = qty * float(product.unit_price)
                sale = Sale(sale_date=sale_date, total_amount=total, customer_name="Auto-generated")
                sale.items = [SaleItem(product_id=product.id, quantity=qty, unit_price=float(product.unit_price), total_price=total)]
                db.session.add(sale)
                product.quantity -= qty

    db.session.commit()
    print("Database seeded successfully with sample data!")
