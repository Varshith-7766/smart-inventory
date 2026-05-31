"""
Smart Inventory Management System — Flask Application
=====================================================
This is ENTRY POINT of the entire backend.

To run the server:
    python app.py

The server starts on http://0.0.0.0:5000

Architecture:
    app.py          ← You are here — creates and runs the Flask app
    config.py       ← Reads environment variables
    database.py     ← Creates the SQLAlchemy `db` object
    models/         ← Defines database tables as Python classes
    routes/         ← Defines API endpoints (organized by feature)
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory, redirect
from flask_cors import CORS
from config import Config
from database import db
from routes import register_routes
from csrf_init import csrf

# Ensure project root is on sys.path (so IoT handlers can be imported from routes)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Path to the frontend pages directory (two levels up from backend/)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
PAGES_DIR = os.path.join(FRONTEND_DIR, "pages")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")


def create_app(test_config=None):
    """
    Application Factory.

    This function:
      1. Creates a Flask instance
      2. Loads configuration
      3. Connects the database
      4. Registers all API routes (Blueprints)
      5. Serves frontend pages
      6. Adds a health-check endpoint

    Parameters:
      test_config (dict, optional): Config overrides for testing (e.g. disable CSRF)

    Returns a fully-configured Flask application.
    """

    # ---- Step 1: Create Flask app ----
    # Set static folder to the frontend/static directory
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")

    # ---- Step 2: Load configuration from config.py ----
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # ---- SECRET_KEY safety check ----
    sk = app.config.get("SECRET_KEY", "")
    if not sk or len(sk) < 16:
        import warnings
        warnings.warn(
            "SECRET_KEY is weak or missing. A random key has been generated, "
            "but sessions will be invalidated on restart. "
            "Set the SECRET_KEY environment variable for persistence.",
            RuntimeWarning,
        )

    # ---- Step 3: Enable CORS (so frontend can call API) ----
    CORS(app, supports_credentials=True)

    # ---- Step 3b: CSRF protection ----
    app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]
    app.config["WTF_CSRF_TIME_LIMIT"] = None
    csrf.init_app(app)

    # ---- Step 4: Initialize database ----
    db.init_app(app)

    # ---- Step 5: Import models so SQLAlchemy knows about them ----
    with app.app_context():
        from models import Product, Sale, SaleItem, Supplier, User, Category, InventoryLog, IoTDeviceLog, ReorderPrediction  # noqa: F401

        # ---- Step 6: Create tables (if they don't exist yet) ----
        db.create_all()

    # ---- Step 7: Register all route Blueprints ----
    register_routes(app)

    # ---- Step 8: Serve frontend pages ----
    @app.route("/")
    def index():
        return redirect("/dashboard.html")

    @app.route("/<path:filename>.html")
    def serve_page(filename):
        """Serve HTML pages from frontend/pages/ directory."""
        return send_from_directory(PAGES_DIR, f"{filename}.html")

    # ---- Step 9: Health-check endpoint ----
    @app.route("/health")
    def health():
        """Simple endpoint to verify the server is running."""
        return jsonify({
            "status": "ok",
            "message": "Smart Inventory API is running",
        })

    return app


# Create the app instance (used by Gunicorn in production)
try:
    application = create_app()
except Exception as e:
    import traceback
    print(f"ERROR: Failed to create app: {e}")
    traceback.print_exc()
    raise

# -------------------------------------------------------------------
# Run the application
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Read host/port from environment, with sensible defaults
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    print(f"*** Starting Smart Inventory API on http://{host}:{port} ***")
    application.run(host=host, port=port, debug=debug)
