from functools import wraps
from flask import session, jsonify

# Roles, ordered from most to least privileged.
# Higher roles implicitly include the permissions of lower roles.
ADMIN = "admin"
MANAGER = "manager"
VIEWER = "viewer"

ROLE_RANK = {VIEWER: 1, MANAGER: 2, ADMIN: 3}


def login_required(f):
    """Decorator that requires a valid user session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator that requires the logged-in user to hold one of `roles`.

    Usage:
        @role_required("admin", "manager")
        def create_product(): ...

    A user whose role is at or above the highest requested role passes,
    so `role_required("manager")` also admits admins.
    """
    required_rank = max(ROLE_RANK[r] for r in roles)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            role = session.get("role") or VIEWER
            if ROLE_RANK.get(role, 0) < required_rank:
                return jsonify({
                    "error": f"Insufficient permissions. Required role: {', '.join(roles)}"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator