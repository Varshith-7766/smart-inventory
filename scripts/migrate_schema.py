"""
Add missing columns/tables to bring the MySQL database in line with schema.sql.

Run:  python scripts/migrate_schema.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

import pymysql

db_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/smart_inventory")
parts = db_url.replace("mysql+pymysql://", "").split("@")
userpass = parts[0].split(":")
hostport_db = parts[1].split("/")
hostport = hostport_db[0].split(":")

conn = pymysql.connect(
    host=hostport[0],
    user=userpass[0],
    password=userpass[1] if len(userpass) > 1 else "",
    port=int(hostport[1]) if len(hostport) > 1 else 3306,
    database=hostport_db[1],
)
cursor = conn.cursor()


def try_add_column(table, col_def):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        conn.commit()
        print(f"  + Added {col_def.split()[0]} to {table}")
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1060:
            print(f"  ~ {col_def.split()[0]} already exists in {table}")
        else:
            raise


def try_add_table(name, ddl):
    try:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {name} {ddl}")
        conn.commit()
        print(f"  + Created table {name}")
    except pymysql.err.OperationalError as e:
        print(f"  ! Error creating {name}: {e}")


print("=== Migrating products table ===")
try_add_column("products", "cost_price DECIMAL(10,2) DEFAULT NULL AFTER unit_price")
try_add_column("products", "weight_kg DECIMAL(8,3) DEFAULT NULL AFTER cost_price")
try_add_column("products", "category_id INT NOT NULL DEFAULT 1 AFTER weight_kg")
try_add_column("products", "barcode_format VARCHAR(20) DEFAULT NULL AFTER barcode")
try_add_column("products", "image_url VARCHAR(500) DEFAULT NULL AFTER barcode_format")
try_add_column("products", "reorder_quantity INT NOT NULL DEFAULT 0 AFTER reorder_level")
try_add_column("products", "updated_at DATETIME DEFAULT NULL AFTER created_at")

print("\n=== Migrating sales table ===")
try_add_column("sales", "invoice_number VARCHAR(50) DEFAULT NULL AFTER id")
try_add_column("sales", "discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER total_amount")
try_add_column("sales", "tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER discount_amount")
try_add_column("sales", "customer_email VARCHAR(120) DEFAULT NULL AFTER customer_name")
try_add_column("sales", "payment_status VARCHAR(30) NOT NULL DEFAULT 'paid' AFTER payment_method")
try_add_column("sales", "processed_by INT DEFAULT NULL AFTER payment_status")
try_add_column("sales", "updated_at DATETIME DEFAULT NULL AFTER created_at")
try_add_column("sales", "grand_total DECIMAL(12,2) GENERATED ALWAYS AS (total_amount - discount_amount + tax_amount) STORED AFTER payment_status")

print("\n=== Migrating sale_items table ===")
try_add_column("sale_items", "discount DECIMAL(10,2) NOT NULL DEFAULT 0.00 AFTER unit_price")

print("\n=== Migrating users table ===")
try_add_column("users", "updated_at DATETIME DEFAULT NULL AFTER last_login")

print("\n=== Adding FK for products.category_id ===")
try:
    cursor.execute(
        "ALTER TABLE products ADD CONSTRAINT fk_products_category "
        "FOREIGN KEY (category_id) REFERENCES categories(id) "
        "ON DELETE RESTRICT ON UPDATE CASCADE"
    )
    conn.commit()
    print("  + Added FK products.category_id -> categories.id")
except pymysql.err.OperationalError as e:
    print(f"  ~ FK may already exist: {e}")

print("\n=== Migration complete ===")
cursor.close()
conn.close()
