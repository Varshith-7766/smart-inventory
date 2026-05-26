from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import pandas as pd
import os


class SalesDataLoader:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv("DATABASE_URL")

    def load_product_sales(self, product_id, days_back=90):
        engine = create_engine(self.database_url)
        cutoff = datetime.utcnow() - timedelta(days=days_back)

        query = text("""
            SELECT s.sale_date, si.quantity, si.unit_price
            FROM sales s
            JOIN sale_items si ON s.id = si.sale_id
            WHERE si.product_id = :pid AND s.sale_date >= :cutoff
            ORDER BY s.sale_date ASC
        """)

        df = pd.read_sql(query, engine, params={"pid": product_id, "cutoff": cutoff})
        if df.empty:
            return pd.DataFrame()

        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df.set_index("sale_date", inplace=True)
        daily = df.resample("D")["quantity"].sum().fillna(0).reset_index()
        daily.columns = ["date", "quantity"]
        return daily

    def load_all_products(self):
        engine = create_engine(self.database_url)
        query = text("SELECT id, name FROM products WHERE is_active = 1")
        return pd.read_sql(query, engine)
