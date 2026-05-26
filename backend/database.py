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

from flask_sqlalchemy import SQLAlchemy

# Instantiate once and import wherever needed.
# This is the "One SQLAlchemy to rule them all" pattern.
db = SQLAlchemy()
