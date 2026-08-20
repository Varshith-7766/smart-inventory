"""
User Model
==========
Manages admin/manager/viewer authentication.

Password storage:
  - Raw passwords are NEVER stored.
  - We store a Werkzeug hash (one-way, salted).
  - `set_password()` hashes before saving.
  - `check_password()` compares a plain-text attempt against the stored hash.

Table: users
Columns:
  id              - Auto-increment primary key
  username        - Unique login name (indexed for fast lookups)
  email           - Unique email address
  password_hash   - Password hash
  role            - admin | manager | viewer
  is_active       - Soft-delete: 0 = disabled, 1 = active (default)
  last_login      - Set when user successfully authenticates
  created_at      - Row creation timestamp
  updated_at      - Auto-updated on every change
"""

from database import db, utcnow
from werkzeug.security import generate_password_hash, check_password_hash

# Valid roles. New accounts default to the least-privileged role.
ROLES = ("admin", "manager", "viewer")


class User(db.Model):
    """System user who can log in and perform actions."""

    __tablename__ = "users"

    # ----- Primary Key -----
    id = db.Column(db.Integer, primary_key=True)

    # ----- Authentication Fields -----
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # ----- Authorization -----
    # Default is the least-privileged role. Admins must be created explicitly
    # (e.g. via scripts/seed_data.py); the registration endpoint never grants
    # anything beyond "viewer".
    role = db.Column(
        db.String(20),
        nullable=False,
        default="viewer",
        comment="admin | manager | viewer"
    )

    # ----- Status -----
    is_active = db.Column(db.Boolean, default=True, comment="0 = disabled, 1 = active")
    last_login = db.Column(db.DateTime, nullable=True)

    # ----- Timestamps -----
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # ----------------------------------------------------------------
    # Password helpers  (abstract away the hashing detail)
    # ----------------------------------------------------------------
    def set_password(self, plain_password):
        """Hash the password and store it."""
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password):
        """Return True if the plain-text matches the stored hash."""
        return check_password_hash(self.password_hash, plain_password)

    # ----------------------------------------------------------------
    # String representation (useful for debugging / admin panels)
    # ----------------------------------------------------------------
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

    def to_dict(self):
        """Serialize the user object to a dictionary (safe, no hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
        }