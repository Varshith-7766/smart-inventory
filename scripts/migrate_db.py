import os
import sys
import pymysql

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

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

try:
    cursor.execute("ALTER TABLE sales ADD COLUMN payment_method VARCHAR(50) DEFAULT 'cash' AFTER notes")
    conn.commit()
    print("Added payment_method column to sales table")
except pymysql.err.OperationalError as e:
    if e.args[0] == 1060:
        print("Column already exists")
    else:
        raise
finally:
    cursor.close()
    conn.close()
