"""
Authentication Routes
=====================
Endpoints for user registration and login.

Uses session-based auth (Flask's built-in session object).
For a simple internal dashboard this is sufficient.
For production, consider JWT tokens instead.

Endpoints:
  POST /api/auth/register  — Create a new user
  POST /api/auth/login     — Authenticate and start a session
  POST /api/auth/logout    — Clear the session
  GET  /api/auth/me        — Return the currently logged-in user
"""

from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime
from database import db
from models.user import User
from routes.decorators import login_required
from csrf_init import csrf

# Create the Blueprint — a named group of routes
auth_bp = Blueprint("auth", __name__)


# ----------------------------------------------------------------
# POST /api/auth/register
# Creates a new user account.
# Request body (JSON):
#   { "username": "admin", "email": "a@b.com", "password": "secret" }
# ----------------------------------------------------------------
@auth_bp.route("/csrf-token", methods=["GET"])
def get_csrf_token():
    from flask_wtf.csrf import generate_csrf
    token = generate_csrf()
    return jsonify({"csrf_token": token})


@csrf.exempt
@auth_bp.route("/register", methods=["POST"])
def register():
    # Parse the incoming JSON body
    data = request.get_json()

    # --- Validate required fields ---
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "username" not in data or "password" not in data:
        return jsonify({"error": "username and password are required"}), 400

    # --- Check for duplicate username ---
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 409  # 409 = Conflict

    # --- Check for duplicate email ---
    if data.get("email") and User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    # --- Input validation ---
    username = data["username"].strip()
    if len(username) > 80:
        return jsonify({"error": "Username must be 80 characters or fewer"}), 400
    if not username:
        return jsonify({"error": "Username cannot be empty"}), 400
    password = data["password"]
    if len(password) > 128:
        return jsonify({"error": "Password must be 128 characters or fewer"}), 400

    # --- Create the user ---
    user = User(
        username=username,
        email=data.get("email", ""),
        role=data.get("role", "viewer"),
    )
    user.set_password(password)

    # --- Save to database ---
    db.session.add(user)
    db.session.commit()

    # Auto-login after registration
    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify({"message": "User created", "user": user.to_dict()}), 201


# ----------------------------------------------------------------
# POST /api/auth/login
# Authenticates a user and creates a session.
# Request body (JSON):
#   { "username": "admin", "password": "secret" }
# ----------------------------------------------------------------
@csrf.exempt
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "username and password are required"}), 400

    # Find user by username
    user = User.query.filter_by(username=data["username"]).first()

    # Validate credentials
    if user is None or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401

    # Check if account is active
    if not user.is_active:
        return jsonify({"error": "Account is disabled"}), 403

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Store user ID in the session (Flask signs the cookie)
    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
    })


# ----------------------------------------------------------------
# POST /api/auth/logout
# Clears the session (logs the user out).
# ----------------------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": user.to_dict()})
