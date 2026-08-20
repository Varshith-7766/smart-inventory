import os
import secrets
import threading
from flask import Blueprint, request, jsonify, session
from sqlalchemy import func
from database import db
from models.iot_device import IoTDeviceLog, IoTDevice
from models.product import Product
from models.inventory_log import InventoryLog
from routes.decorators import login_required, role_required
from csrf_init import csrf

_simulator_instance = None
_simulator_lock = threading.Lock()

iot_bp = Blueprint("iot", __name__)

# Header used by devices to authenticate: X-Device-Key
DEVICE_KEY_HEADER = "X-Device-Key"


# ======================================================================
# DEVICE REGISTRATION
# ======================================================================
# A device must be registered before it can post events. Registration issues
# a per-device API key that the hardware sends as the X-Device-Key header.
# The key binds every event to the owning user, so multi-tenant isolation
# holds and unauthenticated clients cannot flood the event log.
@iot_bp.route("/devices/register", methods=["POST"])
@role_required("manager", "admin")
def register_device():
    uid = session["user_id"]
    data = request.get_json()
    if not data or not data.get("device_id"):
        return jsonify({"error": "device_id is required"}), 400

    device_id = str(data["device_id"])[:100]
    device_type = data.get("device_type", "generic")
    VALID_DEVICE_TYPES = ("barcode_scanner", "rfid_reader", "temperature_sensor", "weight_scale", "generic")
    if device_type not in VALID_DEVICE_TYPES:
        return jsonify({"error": f"Invalid device_type '{device_type}'"}), 400

    existing = IoTDevice.query.filter_by(user_id=uid, device_id=device_id).first()
    if existing:
        if existing.is_active:
            # Idempotent re-registration: keep the existing key stable so
            # devices don't break on re-register.
            existing.device_type = device_type
            existing.location = data.get("location", existing.location)
            db.session.commit()
            return jsonify({"message": "Device already registered", "device": existing.to_dict(include_key=True)}), 200
        existing.is_active = True
        existing.device_type = device_type
        existing.location = data.get("location", existing.location)
        db.session.commit()
        return jsonify({"message": "Device re-activated", "device": existing.to_dict(include_key=True)}), 200

    device = IoTDevice(
        user_id=uid,
        device_id=device_id,
        device_type=device_type,
        api_key=secrets.token_hex(32),
        location=data.get("location"),
    )
    db.session.add(device)
    db.session.commit()

    return jsonify({
        "message": "Device registered",
        "device": device.to_dict(include_key=True),
    }), 201


@iot_bp.route("/devices/registered", methods=["GET"])
@login_required
def list_registered_devices():
    uid = session["user_id"]
    devices = IoTDevice.query.filter_by(user_id=uid).order_by(IoTDevice.created_at.desc()).all()
    return jsonify([d.to_dict() for d in devices])


# ======================================================================
# EVENT INGESTION (called by hardware)
# ======================================================================
# Authentication: the X-Device-Key header must match a registered, active
# device. Events are recorded under that device's owner.
@iot_bp.route("/events", methods=["POST"])
@csrf.exempt  # devices have no browser session; auth is via X-Device-Key
def ingest_event():
    """
    Receive an event from an IoT device.

    The device must be registered first (POST /api/iot/devices/register)
    and must send its API key as the `X-Device-Key` header.

    Payload (JSON):
    {
        "device_id": "SCANNER-WH001",
        "device_type": "barcode_scanner",
        "event_type": "scan",
        "barcode_data": "5901234567897",
        "location": "Warehouse-A",
        "battery_level": 85.0,
        "firmware_version": "v2.3.1",
        "raw_payload": { ... }
    }
    """
    api_key = request.headers.get(DEVICE_KEY_HEADER, "")
    device = IoTDevice.query.filter_by(api_key=api_key, is_active=True).first() if api_key else None
    if device is None:
        return jsonify({"error": "Invalid or missing device API key"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if not data.get("device_id"):
        return jsonify({"error": "device_id is required"}), 400

    # The device_id in the payload must match the key's registered device.
    if data["device_id"] != device.device_id:
        return jsonify({"error": "device_id does not match the API key"}), 403

    device_id = device.device_id
    device_type = data.get("device_type", device.device_type)
    VALID_DEVICE_TYPES = ("barcode_scanner", "rfid_reader", "temperature_sensor", "weight_scale", "generic")
    if device_type not in VALID_DEVICE_TYPES:
        return jsonify({"error": f"Invalid device_type '{device_type}'"}), 400
    VALID_EVENT_TYPES = ("scan", "tag_read", "tag_lost", "connect", "disconnect", "heartbeat", "error", "data")
    event_type = data.get("event_type", "scan")
    if event_type not in VALID_EVENT_TYPES:
        return jsonify({"error": f"Invalid event_type '{event_type}'"}), 400

    # Auto-resolve product from barcode or RFID (scoped to the device owner)
    uid = device.user_id
    product_id = data.get("product_id")
    barcode = data.get("barcode_data")
    rfid_epc = data.get("rfid_epc")

    if not product_id and barcode:
        product = Product.query.filter_by(barcode=barcode, user_id=uid).first()
        if product:
            product_id = product.id

    if not product_id and rfid_epc:
        product = Product.query.filter_by(barcode=rfid_epc, user_id=uid).first()
        if product:
            product_id = product.id

    log = IoTDeviceLog(
        user_id=uid,
        device_id=device_id,
        device_type=device_type,
        event_type=event_type,
        product_id=product_id,
        barcode_data=barcode,
        rfid_epc=rfid_epc,
        rfid_antenna=data.get("rfid_antenna"),
        rssi=data.get("rssi"),
        raw_payload=data.get("raw_payload"),
        location=data.get("location") or device.location,
        battery_level=data.get("battery_level"),
        firmware_version=data.get("firmware_version"),
        is_processed=False,
        error_message=data.get("error_message"),
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "message": "Event recorded",
        "event": log.to_dict(),
    }), 201


@iot_bp.route("/events", methods=["GET"])
@login_required
def list_events():
    uid = session["user_id"]
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)

    query = IoTDeviceLog.query.filter_by(user_id=uid)

    device_id = request.args.get("device_id")
    if device_id:
        query = query.filter(IoTDeviceLog.device_id == device_id)

    device_type = request.args.get("device_type")
    if device_type:
        query = query.filter(IoTDeviceLog.device_type == device_type)

    unprocessed_only = request.args.get("unprocessed", "").lower() in ("1", "true", "yes")
    if unprocessed_only:
        query = query.filter(IoTDeviceLog.is_processed == False)

    pagination = query.order_by(IoTDeviceLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "events": [e.to_dict() for e in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@iot_bp.route("/events/<int:event_id>/process", methods=["PATCH"])
@login_required
def process_event(event_id):
    uid = session["user_id"]
    event = IoTDeviceLog.query.filter_by(id=event_id, user_id=uid).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    if event.event_type == "scan" and event.product_id:
        product = Product.query.filter_by(id=event.product_id, user_id=uid).first()
        if product:
            body = request.get_json(silent=True) or {}
            try:
                qty = int(body.get("quantity", 1))
            except (TypeError, ValueError):
                return jsonify({"error": "quantity must be an integer"}), 400
            if qty <= 0:
                return jsonify({"error": "quantity must be a positive integer"}), 400

            previous_qty = product.quantity
            product.quantity += qty
            db.session.add(InventoryLog(
                product_id=product.id,
                user_id=uid,
                movement_type="purchase_in",
                quantity_change=qty,
                quantity_before=previous_qty,
                quantity_after=product.quantity,
                reference_type="iot_scan",
                notes=f"IoT scan processed for {event.device_id}, added {qty} x {product.name}",
            ))

    event.is_processed = True
    db.session.commit()

    return jsonify({
        "message": "Event processed",
        "event": event.to_dict(),
    })


@iot_bp.route("/devices", methods=["GET"])
@login_required
def list_devices():
    uid = session["user_id"]
    devices = (
        db.session.query(
            IoTDeviceLog.device_id,
            IoTDeviceLog.device_type,
            IoTDeviceLog.location,
            func.count(IoTDeviceLog.id).label("event_count"),
            func.max(IoTDeviceLog.created_at).label("last_seen"),
            func.avg(IoTDeviceLog.battery_level).label("avg_battery"),
        )
        .filter(IoTDeviceLog.user_id == uid)
        .group_by(IoTDeviceLog.device_id, IoTDeviceLog.device_type, IoTDeviceLog.location)
        .order_by(func.max(IoTDeviceLog.created_at).desc())
        .all()
    )

    return jsonify([{
        "device_id": d.device_id,
        "device_type": d.device_type,
        "location": d.location,
        "event_count": d.event_count,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        "avg_battery": round(float(d.avg_battery), 1) if d.avg_battery else None,
    } for d in devices])


@iot_bp.route("/stats", methods=["GET"])
@login_required
def iot_stats():
    uid = session["user_id"]
    total_events = db.session.query(func.count(IoTDeviceLog.id)).filter(
        IoTDeviceLog.user_id == uid
    ).scalar()
    unprocessed = db.session.query(func.count(IoTDeviceLog.id)).filter(
        IoTDeviceLog.user_id == uid,
        IoTDeviceLog.is_processed == False
    ).scalar()
    device_count = (
        db.session.query(func.count(func.distinct(IoTDeviceLog.device_id)))
        .filter(IoTDeviceLog.user_id == uid)
        .scalar()
    )
    scan_count = db.session.query(func.count(IoTDeviceLog.id)).filter(
        IoTDeviceLog.user_id == uid,
        IoTDeviceLog.event_type == "scan"
    ).scalar()

    return jsonify({
        "total_events": total_events,
        "unprocessed_events": unprocessed,
        "registered_devices": device_count,
        "total_scans": scan_count,
    })


@iot_bp.route("/simulator/start", methods=["POST"])
@login_required
def simulator_start():
    global _simulator_instance
    with _simulator_lock:
        if _simulator_instance and _simulator_instance.is_running():
            return jsonify({"status": "already_running"})

        # The simulator needs a registered device key to authenticate with
        # the ingest endpoint.
        api_key = os.getenv("IOT_API_KEY", "")
        if not api_key:
            return jsonify({
                "status": "error",
                "error": "Set IOT_API_KEY to a registered device key before starting the simulator.",
            }), 400

        from iot.simulator import IoTSimulator
        _simulator_instance = IoTSimulator(interval_range=(1, 4), error_rate=0.05)
        result = _simulator_instance.start()
        return jsonify(result)


@iot_bp.route("/simulator/stop", methods=["POST"])
@login_required
def simulator_stop():
    global _simulator_instance
    with _simulator_lock:
        if not _simulator_instance:
            return jsonify({"status": "not_running"})
        result = _simulator_instance.stop()
        _simulator_instance = None
        return jsonify(result)


@iot_bp.route("/simulator/status", methods=["GET"])
@login_required
def simulator_status():
    global _simulator_instance
    with _simulator_lock:
        running = _simulator_instance is not None and _simulator_instance.is_running()
        return jsonify({"running": running})