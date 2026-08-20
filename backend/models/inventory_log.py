from database import db, utcnow


class InventoryLog(db.Model):
    __tablename__ = "inventory_logs"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    movement_type = db.Column(
        db.Enum(
            "sale_out", "purchase_in", "adjustment", "return_in",
            "damage_out", "transfer_out", "transfer_in", "count_correct",
        ),
        nullable=False,
    )
    quantity_change = db.Column(db.Integer, nullable=False)
    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(
        db.Integer, nullable=False,
        comment="quantity_before + quantity_change",
    )
    reference_type = db.Column(db.String(50), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    product = db.relationship("Product", lazy="joined")
    user = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "user_id": self.user_id,
            "movement_type": self.movement_type,
            "quantity_change": self.quantity_change,
            "quantity_before": self.quantity_before,
            "quantity_after": self.quantity_after,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
