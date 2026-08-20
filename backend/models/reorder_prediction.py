from database import db, utcnow


class ReorderPrediction(db.Model):
    __tablename__ = "reorder_predictions"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    forecast_date = db.Column(db.Date, nullable=False, index=True)
    predicted_daily_demand = db.Column(db.Float, nullable=False)
    predicted_weekly_demand = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)
    days_until_stockout = db.Column(db.Integer, nullable=True)
    suggested_reorder_qty = db.Column(db.Integer, nullable=True)
    model_version = db.Column(db.String(50), nullable=True)
    alert_level = db.Column(
        db.Enum("GREEN", "YELLOW", "RED", "BLACK"), nullable=True
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    product = db.relationship("Product", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "forecast_date": self.forecast_date.isoformat(),
            "predicted_daily_demand": self.predicted_daily_demand,
            "predicted_weekly_demand": self.predicted_weekly_demand,
            "confidence_score": self.confidence_score,
            "days_until_stockout": self.days_until_stockout,
            "suggested_reorder_qty": self.suggested_reorder_qty,
            "model_version": self.model_version,
            "alert_level": self.alert_level,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
