import threading
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from database import db
from models.iot_device import IoTDeviceLog
from models.product import Product
from routes.decorators import login_required
from csrf_init import csrf

_simulator_instance = None
_simulator_lock = threading.Lock()

iot_bp = Blueprint("iot", __name__)


@csrf.exempt
@iot_bp.route("/events", methods=["POST"])
def ingest_event():
    """
    Receive an event from an IoT device.

    This is the endpoint that barcode scanners, RFID readers,
    and other hardware POST their data to.

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
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    device_id = data.get("device_id")
    device_type = data.get("device_type")
    if not device_id or not device_type:
        return jsonify({"error": "device_id and device_type are required"}), 400

    # Validate device_type against allowed ENUM values
    VALID_DEVICE_TYPES = ("barcode_scanner", "rfid_reader", "temperature_sensor", "weight_scale", "generic")
    if device_type not in VALID_DEVICE_TYPES:
        return jsonify({"error": f"Invalid device_type '{device_type}'. Must be one of: {', '.join(VALID_DEVICE_TYPES)}"}), 400
    VALID_EVENT_TYPES = ("scan", "tag_read", "tag_lost", "connect", "disconnect", "heartbeat", "error", "data")
    event_type = data.get("event_type", "scan")
    if event_type not in VALID_EVENT_TYPES:
        return jsonify({"error": f"Invalid event_type '{event_type}'. Must be one of: {', '.join(VALID_EVENT_TYPES)}"}), 400

    # Auto-resolve product from barcode or RFID
    product_id = data.get("product_id")
    barcode = data.get("barcode_data")
    rfid_epc = data.get("rfid_epc")

    if not product_id and barcode:
        product = Product.query.filter_by(barcode=barcode).first()
        if product:
            product_id = product.id

    if not product_id and rfid_epc:
        product = Product.query.filter_by(barcode=rfid_epc).first()
        if product:
            product_id = product.id

    log = IoTDeviceLog(
        device_id=device_id,
        device_type=device_type,
        event_type=data.get("event_type", "scan"),
        product_id=product_id,
        barcode_data=barcode,
        rfid_epc=rfid_epc,
        rfid_antenna=data.get("rfid_antenna"),
        rssi=data.get("rssi"),
        raw_payload=data.get("raw_payload"),
        location=data.get("location"),
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
            qty = body.get("quantity", 1)
            product.quantity += qty

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
    from sqlalchemy import func
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
    from sqlalchemy import func
    total_events = db.session.query(func.count(IoTDeviceLog.id)).scalar()
    unprocessed = db.session.query(func.count(IoTDeviceLog.id)).filter(
        IoTDeviceLog.is_processed == False
    ).scalar()
    device_count = (
        db.session.query(func.count(func.distinct(IoTDeviceLog.device_id))).scalar()
    )
    scan_count = db.session.query(func.count(IoTDeviceLog.id)).filter(
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
