"""
Routes Package
==============
Registers all Blueprint route modules with the Flask app.

Each route module is a Blueprint — a self-contained group of endpoints
that share a common URL prefix.  This keeps the codebase organized:

  /api/products/...   → handled by routes/products.py
  /api/sales/...      → handled by routes/sales.py
  /api/stock/...      → handled by routes/stock.py
  /api/auth/...       → handled by routes/auth.py
"""

from flask import Flask


def register_routes(app: Flask):
    """Import each Blueprint and register it under its URL prefix."""

    from routes.auth import auth_bp
    from routes.products import products_bp
    from routes.sales import sales_bp
    from routes.stock import stock_bp
    from routes.dashboard import dashboard_bp
    from routes.iot import iot_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(sales_bp, url_prefix="/api/sales")
    app.register_blueprint(stock_bp, url_prefix="/api/stock")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(iot_bp, url_prefix="/api/iot")
