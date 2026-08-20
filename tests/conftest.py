import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import create_app
from database import db as _db


@pytest.fixture
def app():
    # The database URI is passed INSIDE test_config so that create_app()
    # binds the SQLAlchemy engine to the in-memory SQLite database from the
    # start. Setting it after create_app() would leave the engine bound to
    # whatever DATABASE_URL is in the environment (e.g. a real MySQL/Postgres
    # server) — tests must never touch a real database.
    app = create_app(test_config={
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    client = app.test_client()
    # Pre-set session so @login_required doesn't block requests.
    # Role is set to "admin" so role-guarded mutation endpoints work too.
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "admin"
    return client


@pytest.fixture
def db(app):
    return _db