import os, sys, pymysql

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

db_url = os.getenv("DATABASE_URL")
parts = db_url.replace("mysql+pymysql://", "").split("@")
userpass = parts[0].split(":")
hostport_db = parts[1].split("/")
hostport = hostport_db[0].split(":")

conn = pymysql.connect(
    host=hostport[0], user=userpass[0],
    password=userpass[1] if len(userpass) > 1 else "",
    port=int(hostport[1]) if len(hostport) > 1 else 3306,
    database=hostport_db[1],
)
cursor = conn.cursor()

cursor.execute("INSERT IGNORE INTO categories (id, name, description, sort_order) VALUES (1, 'General', 'Default category', 0)")
conn.commit()
print("Default category ready")

try:
    cursor.execute(
        "ALTER TABLE products ADD CONSTRAINT fk_products_category "
        "FOREIGN KEY (category_id) REFERENCES categories(id) "
        "ON DELETE RESTRICT ON UPDATE CASCADE"
    )
    conn.commit()
    print("FK constraint added")
except pymysql.err.OperationalError as e:
    print(f"FK may already exist: {e}")

cursor.close()
conn.close()
print("Done")
