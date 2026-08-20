"""
Stock Routes
============
Manual stock adjustments and low-stock alert management.

Endpoints:
  POST /api/stock/adjust       — Adjust stock (+/-) for a product (manager+)
  GET  /api/stock/alerts       — List all low-stock alerts
  PATCH /api/stock/alerts/resolve — Persist an alert acknowledgement
"""

from flask import Blueprint, request, jsonify, session
from database import db
from models.product import Product
from models.sale import Sale
from models.inventory_log import InventoryLog
from models.alert_resolution import AlertResolution
from routes.decorators import login_required, role_required

stock_bp = Blueprint("stock", __name__)


# ======================================================================
# STOCK MOVEMENTS (recent sale activity)
# ======================================================================
@stock_bp.route("/movements", methods=["GET"])
@login_required
def stock_movements():
    uid = session["user_id"]
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 15, type=int), 100)

    pagination = Sale.query.filter_by(processed_by=uid).order_by(Sale.sale_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    movements = []
    for sale in pagination.items:
        for item in sale.items:
            product_name = item.product.name if item.product else f"Product #{item.product_id}"
            movements.append({
                "id": item.id,
                "created_at": sale.sale_date.isoformat(),
                "product_id": item.product_id,
                "product_name": product_name,
                "movement_type": "sale_out",
                "quantity_change": -item.quantity,
                "reason": f"Sale #{sale.id}",
                "notes": sale.notes or "",
            })

    return jsonify({
        "movements": movements,
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


# ======================================================================
# ADJUST STOCK
# ======================================================================
@stock_bp.route("/adjust", methods=["POST"])
@role_required("manager", "admin")
def adjust_stock():
    uid = session["user_id"]
    data = request.get_json()

    # --- Validate ---
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    product_id = data.get("product_id")

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return jsonify({"error": "product_id must be an integer"}), 400

    try:
        quantity_change = int(data.get("quantity_change"))
    except (TypeError, ValueError):
        return jsonify({"error": "quantity_change must be an integer"}), 400
    if quantity_change == 0:
        return jsonify({"error": "quantity_change must be a non-zero integer"}), 400

    # --- Find the product (must belong to current user) ---
    product = Product.query.filter_by(id=product_id, user_id=uid).first()
    if product is None:
        return jsonify({"error": f"Product #{product_id} not found"}), 404

    # --- Prevent negative stock ---
    new_quantity = product.quantity + quantity_change
    if new_quantity < 0:
        return jsonify({
            "error": f"Cannot reduce stock below 0. "
                     f"Current: {product.quantity}, attempted change: {quantity_change}"
        }), 400

    previous_quantity = product.quantity

    # --- Apply the change ---
    product.quantity = new_quantity

    # --- Record audit trail ---
    log = InventoryLog(
        product_id=product.id,
        user_id=uid,
        movement_type=data.get("movement_type", "adjustment"),
        quantity_change=quantity_change,
        quantity_before=previous_quantity,
        quantity_after=new_quantity,
        reference_type="stock_adjust",
        notes=data.get("reason", ""),
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "message": "Stock adjusted successfully",
        "product_id": product.id,
        "product_name": product.name,
        "previous_quantity": previous_quantity,
        "quantity_change": quantity_change,
        "new_quantity": product.quantity,
        "is_low_stock": product.is_low_stock(),
    })


# ======================================================================
# LIST LOW-STOCK ALERTS
# ======================================================================
@stock_bp.route("/alerts", methods=["GET"])
@login_required
def list_alerts():
    uid = session["user_id"]
    products = Product.query.filter(
        Product.is_active == True,
        Product.quantity <= Product.reorder_level,
        Product.user_id == uid
    ).order_by(Product.quantity.asc()).all()

    # Include whether each alert has been acknowledged (and when)
    resolved_map = {
        r.product_id: r.resolved_at.isoformat()
        for r in AlertResolution.query.filter_by(user_id=uid).all()
    }

    alerts = []
    for product in products:
        alerts.append({
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "current_quantity": product.quantity,
            "reorder_level": product.reorder_level,
            "shortfall": product.reorder_level - product.quantity,
            "resolved_at": resolved_map.get(product.id),
            # How many units we recommend ordering
            "suggested_order_qty": max(
                product.reorder_level * 2 - product.quantity,  # bring up to 2x reorder
                0
            ),
        })

    return jsonify({
        "alert_count": len(alerts),
        "alerts": alerts,
    })


# ======================================================================
# RESOLVE AN ALERT (mark as handled)
# ======================================================================
# After restocking a product, the alert can be acknowledged. The
# acknowledgement is persisted so it is auditable. The alert will re-appear
# if the product drops below its reorder level again.
@stock_bp.route("/alerts/resolve", methods=["PATCH"])
@login_required
def resolve_alert():
    uid = session["user_id"]
    data = request.get_json()
    if not data or not data.get("product_id"):
        return jsonify({"error": "product_id is required"}), 400

    try:
        product_id = int(data["product_id"])
    except (TypeError, ValueError):
        return jsonify({"error": "product_id must be an integer"}), 400

    product = Product.query.filter_by(id=product_id, user_id=uid).first()
    if product is None:
        return jsonify({"error": f"Product #{product_id} not found"}), 404

    # Upsert the acknowledgement
    resolution = AlertResolution.query.filter_by(user_id=uid, product_id=product_id).first()
    if resolution is None:
        resolution = AlertResolution(user_id=uid, product_id=product_id)
        db.session.add(resolution)
    resolution.notes = (data.get("notes") or "")[:255]
    db.session.commit()

    return jsonify({
        "message": f"Alert resolved for '{product.name}'",
        "product_id": product.id,
        "current_quantity": product.quantity,
        "reorder_level": product.reorder_level,
        "still_low": product.is_low_stock(),
        "resolved_at": resolution.resolved_at.isoformat(),
    })