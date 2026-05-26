from datetime import datetime
from database import db


class IoTDeviceLog(db.Model):
    __tablename__ = "iot_device_logs"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    device_id = db.Column(db.String(100), nullable=False, index=True)
    device_type = db.Column(
        db.Enum("barcode_scanner", "rfid_reader", "temperature_sensor", "weight_scale", "generic"),
        nullable=False,
    )
    event_type = db.Column(
        db.Enum("scan", "tag_read", "tag_lost", "connect", "disconnect", "heartbeat", "error", "data"),
        nullable=False, default="scan",
    )
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    barcode_data = db.Column(db.String(255), nullable=True)
    rfid_epc = db.Column(db.String(255), nullable=True)
    rfid_antenna = db.Column(db.Integer, nullable=True)
    rssi = db.Column(db.Float, nullable=True)
    raw_payload = db.Column(db.JSON, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    battery_level = db.Column(db.Float, nullable=True)
    firmware_version = db.Column(db.String(50), nullable=True)
    is_processed = db.Column(db.Boolean, nullable=False, default=False)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    product = db.relationship("Product", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_type": self.device_type,
            "event_type": self.event_type,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "barcode_data": self.barcode_data,
            "rfid_epc": self.rfid_epc,
            "rfid_antenna": self.rfid_antenna,
            "rssi": self.rssi,
            "raw_payload": self.raw_payload,
            "location": self.location,
            "battery_level": self.battery_level,
            "firmware_version": self.firmware_version,
            "is_processed": self.is_processed,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }
