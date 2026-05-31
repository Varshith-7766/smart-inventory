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

    # --- Database ---
    # Reads DATABASE_URL from environment (set on Render as postgresql://...)
    # Render provides URLs starting with postgres:// which SQLAlchemy doesn't like,
    # so we replace it with postgresql://
    _db_url = os.getenv("DATABASE_URL", "sqlite:///inventory.db")
    if _db_url and _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    # Disable Flask-SQLAlchemy event system (saves memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Application Settings ---
    # Stock level below which a product triggers a low-stock alert
    LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", 10))
    # How often (in days) the prediction engine re-runs
    PREDICTION_INTERVAL_DAYS = int(os.getenv("PREDICTION_INTERVAL_DAYS", 7))
