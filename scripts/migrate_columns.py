"""
Migration: add sale status column, change unit_price from FLOAT to DECIMAL(10,2).

Run:  python scripts/migrate_columns.py
"""

import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["FLASK_DEBUG"] = "false"

from app import create_app
from database import db

app = create_app()

with app.app_context():
    engine = db.engine
    inspector = db.inspect(engine)
    conn = engine.raw_connection()
    cursor = conn.cursor()

    # 1. Add status column to sales table
    columns = [col["name"] for col in inspector.get_columns("sales")]
    if "status" not in columns:
        cursor.execute(
            "ALTER TABLE sales ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active', "
            "ADD INDEX idx_sales_status (status)"
        )
        print("Added 'status' column to 'sales' table")
    else:
        print("'status' column already exists in 'sales' table")

    # 2. Change unit_price from FLOAT to DECIMAL(10,2) in products table
    col_info = [c for c in inspector.get_columns("products") if c["name"] == "unit_price"]
    if col_info and str(col_info[0]["type"]) == "FLOAT":
        cursor.execute("ALTER TABLE products MODIFY COLUMN unit_price DECIMAL(10,2) NOT NULL")
        print("Changed products.unit_price from FLOAT to DECIMAL(10,2)")
    else:
        print("products.unit_price already DECIMAL or not found")

    # 3. Change unit_price from FLOAT to DECIMAL(10,2) in sale_items table
    col_info2 = [c for c in inspector.get_columns("sale_items") if c["name"] == "unit_price"]
    if col_info2 and str(col_info2[0]["type"]) == "FLOAT":
        cursor.execute("ALTER TABLE sale_items MODIFY COLUMN unit_price DECIMAL(10,2) NOT NULL")
        print("Changed sale_items.unit_price from FLOAT to DECIMAL(10,2)")
    else:
        print("sale_items.unit_price already DECIMAL or not found")

    # 4. Change total_price from FLOAT to DECIMAL(12,2) in sale_items
    col_info3 = [c for c in inspector.get_columns("sale_items") if c["name"] == "total_price"]
    if col_info3 and str(col_info3[0]["type"]) == "FLOAT":
        cursor.execute("ALTER TABLE sale_items MODIFY COLUMN total_price DECIMAL(12,2) NOT NULL")
        print("Changed sale_items.total_price from FLOAT to DECIMAL(12,2)")
    else:
        print("sale_items.total_price already DECIMAL or not found")

    # 5. Change total_amount from FLOAT to DECIMAL(12,2) in sales table
    col_info4 = [c for c in inspector.get_columns("sales") if c["name"] == "total_amount"]
    if col_info4 and str(col_info4[0]["type"]) == "FLOAT":
        cursor.execute("ALTER TABLE sales MODIFY COLUMN total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00")
        print("Changed sales.total_amount from FLOAT to DECIMAL(12,2)")
    else:
        print("sales.total_amount already DECIMAL or not found")

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration complete.")
