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
    connect_timeout=5,
)
cursor = conn.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS smart_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cursor.execute("SHOW DATABASES LIKE 'smart_inventory'")
result = cursor.fetchone()
print("Database ready:", result[0] if result else "NOT FOUND")
conn.close()
