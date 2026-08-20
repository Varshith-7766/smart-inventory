from database import db, utcnow


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        # SKU / barcode uniqueness is scoped per user so different tenants
        # can use the same codes without colliding (multi-tenant isolation).
        db.UniqueConstraint("user_id", "sku", name="uq_product_user_sku"),
        db.UniqueConstraint("user_id", "barcode", name="uq_product_user_barcode"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    sku = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, default="")

    quantity = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, default=10)
    reorder_quantity = db.Column(db.Integer, nullable=False, default=0)

    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2), nullable=True)
    weight_kg = db.Column(db.Numeric(8, 3), nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    category = db.Column(db.String(100), default="General")
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)

    barcode = db.Column(db.String(100), nullable=True, index=True)
    barcode_format = db.Column(db.String(20), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    def __repr__(self):
        return f"<Product {self.sku}: {self.name} (qty={self.quantity})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "description": self.description,
            "quantity": self.quantity,
            "reorder_level": self.reorder_level,
            "reorder_quantity": self.reorder_quantity,
            "unit_price": float(self.unit_price) if self.unit_price else 0.0,
            "cost_price": float(self.cost_price) if self.cost_price else None,
            "weight_kg": float(self.weight_kg) if self.weight_kg else None,
            "category_id": self.category_id,
            "category": self.category,
            "supplier_id": self.supplier_id,
            "barcode": self.barcode,
            "barcode_format": self.barcode_format,
            "image_url": self.image_url,
            "is_active": self.is_active,
            "is_low_stock": self.is_low_stock(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }