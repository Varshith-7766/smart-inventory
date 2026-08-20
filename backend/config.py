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

# Known-weak secret keys that must never be accepted silently.
# If one of these is set, a random key is generated instead so that
# sessions can never be forged with a publicly-known key.
WEAK_SECRET_KEYS = (
    "change-this",
    "change-this-to-a-random-secret-key",
    "change-me-in-production",
    "super-secret-key-change-in-production",
    "secret",
    "password",
)


class Config:
    """
    Central configuration class.
    Each attribute maps to a setting that Flask or our extensions read.
    """

    # --- Flask Core ---
    # Auto-generate a secure key if none is set or if a known-weak value is in use
    _raw_key = os.getenv("SECRET_KEY", "")
    if not _raw_key or _raw_key in WEAK_SECRET_KEYS:
        _raw_key = secrets.token_hex(32)
    SECRET_KEY = _raw_key

    # --- Session hardening ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to "True" when serving over HTTPS (production on Render)
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

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

    # --- CORS ---
    # The frontend is served same-origin by Flask, so no cross-origin access
    # is needed by default. To allow a separate frontend origin, set
    # ALLOWED_ORIGINS to a comma-separated list (e.g. https://app.example.com).
    # Keep credentials-enabled CORS locked to explicit origins — never "*".
    ALLOWED_ORIGINS = [
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]

    # --- CSRF ---
    # Tokens are valid for 24 hours. The frontend refreshes the token on
    # every page load, so a bounded lifetime is safe and more secure than None.
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", 86400))

    # --- Application Settings ---
    # Stock level below which a product triggers a low-stock alert
    LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", 10))
    # How often (in days) the prediction engine re-runs
    PREDICTION_INTERVAL_DAYS = int(os.getenv("PREDICTION_INTERVAL_DAYS", 7))