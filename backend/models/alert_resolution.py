from database import db, utcnow


class AlertResolution(db.Model):
    """
    Acknowledgement of a low-stock alert.

    When a user resolves a low-stock alert they acknowledge it; the record
    persists so the action is auditable instead of being a no-op 200.
    """

    __tablename__ = "alert_resolutions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_alert_resolution_user_product"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    resolved_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    notes = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "resolved_at": self.resolved_at.isoformat(),
            "notes": self.notes,
        }