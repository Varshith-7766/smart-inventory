from datetime import datetime
from database import db


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=True)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    customer_name = db.Column(db.String(200), nullable=True)
    customer_email = db.Column(db.String(120), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True, default="cash")
    payment_status = db.Column(db.String(30), nullable=False, default="paid")
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    processed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship(
        "SaleItem", backref="sale", lazy="joined", cascade="all, delete-orphan"
    )
    processor = db.relationship("User", lazy="joined")

    def __repr__(self):
        return f"<Sale #{self.id} | ${self.total_amount:.2f} | {self.sale_date}>"

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "sale_date": self.sale_date.isoformat(),
            "total_amount": float(self.total_amount) if self.total_amount else 0.0,
            "discount_amount": float(self.discount_amount) if self.discount_amount else 0.0,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0.0,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "payment_method": self.payment_method or "cash",
            "payment_status": self.payment_status,
            "status": self.status,
            "notes": self.notes,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at.isoformat(),
        }


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)

    product = db.relationship("Product", lazy="joined")

    def __repr__(self):
        return f"<SaleItem Product#{self.product_id} x{self.quantity}>"

    def to_dict(self):
        return {
            "id": self.id,
            "sale_id": self.sale_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price) if self.unit_price else 0.0,
            "discount": float(self.discount) if self.discount else 0.0,
            "total_price": float(self.total_price) if self.total_price else 0.0,
        }
