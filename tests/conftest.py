import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import create_app
from database import db as _db


@pytest.fixture
def app():
    app = create_app(test_config={"WTF_CSRF_ENABLED": False, "TESTING": True})
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    client = app.test_client()
    # Pre-set session so @login_required doesn't block requests
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
    return client


@pytest.fixture
def db(app):
    return _db
