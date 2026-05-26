from functools import wraps
from flask import session, jsonify


def login_required(f):
    """Decorator that requires a valid user session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function
