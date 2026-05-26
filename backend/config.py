"""
Configuration Module
====================
Loads all environment variables and provides a Config class
that Flask can consume.

Sensitive data (passwords, secret keys) are NOT hardcoded here.
They are read from a .env file or system environment variables.
"""

import os
import secrets
from dotenv import load_dotenv

# Load variables from the .env file into os.environ
load_dotenv()


class Config:
    """
    Central configuration class.
    Each attribute maps to a setting that Flask or our extensions read.
    """

    # --- Flask Core ---
    # Auto-generate a secure key if none is set or if the default is still in use
    _raw_key = os.getenv("SECRET_KEY", "")
    if not _raw_key or _raw_key in ("change-this", "super-secret-key-change-in-production"):
        _raw_key = secrets.token_hex(32)
    SECRET_KEY = _raw_key

    # --- MySQL Database ---
    # Format: mysql+pymysql://username:password@host:port/database
    # Must be set via environment variable or .env file
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    # Disable Flask-SQLAlchemy event system (saves memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Application Settings ---
    # Stock level below which a product triggers a low-stock alert
    LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", 10))
    # How often (in days) the prediction engine re-runs
    PREDICTION_INTERVAL_DAYS = int(os.getenv("PREDICTION_INTERVAL_DAYS", 7))
