"""
Database Module
===============
Single source of truth for the database connection object (`db`).

Flask-SQLAlchemy gives us:
  - `db.session`  — the transactional scope
  - `db.Model`    — base class for our models
  - `db.engine`   — raw SQLAlchemy engine (for direct queries)
  - `db.create_all()`  — creates tables from models
  - `db.drop_all()`    — drops all tables (use with care in dev)

Usage in other files:
    from database import db
    db.session.add(...)
    db.session.commit()
"""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

# Instantiate once and import wherever needed.
# This is the "One SQLAlchemy to rule them all" pattern.
db = SQLAlchemy()


def utcnow():
    """
    Timezone-aware UTC timestamp, stored as naive for DB compatibility.

    `datetime.utcnow()` is deprecated since Python 3.12, so all models and
    routes should use this helper instead. Returns a naive datetime in UTC
    so it stays compatible with SQLAlchemy `DateTime` columns (which do not
    store timezone info) across SQLite / MySQL / PostgreSQL.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)