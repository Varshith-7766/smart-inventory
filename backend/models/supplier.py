"""
Supplier Model
==============
Represents a vendor or manufacturer that supplies products.

Table: suppliers
Columns:
  id              - Primary key
  name            - Company name (e.g., "TechDistributor Inc.")
  contact_person  - Name of the person we communicate with
  email / phone   - Contact details
  address         - Physical or mailing address
  lead_time_days  - Average days from placing an order to receiving it
  is_active       - Soft-delete flag
  created_at / updated_at
"""

from database import db, utcnow


class Supplier(db.Model):
    """A vendor that provides products to the business."""

    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, comment="Company name")
    contact_person = db.Column(db.String(100), comment="Primary contact name")
    email = db.Column(db.String(120), comment="Contact email")
    phone = db.Column(db.String(30), comment="Contact phone number")
    address = db.Column(db.Text, comment="Full address")
    lead_time_days = db.Column(db.Integer, comment="Avg days from order to delivery")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # One supplier → many products
    products = db.relationship("Product", backref="supplier", lazy="dynamic")

    def __repr__(self):
        return f"<Supplier {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact_person": self.contact_person,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "lead_time_days": self.lead_time_days,
            "is_active": self.is_active,
        }
