"""
Stock Routes
============
Manual stock adjustments and low-stock alert management.

Endpoints:
  POST /api/stock/adjust       — Adjust stock (+/-) for a product
  GET  /api/stock/alerts       — List all low-stock alerts
  PATCH /api/stock/alerts/<id>/resolve — Mark an alert as resolved
"""

import os
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from database import db
from models.product import Product
from models.sale import Sale, SaleItem
from models.inventory_log import InventoryLog
from routes.decorators import login_required
from csrf_init import csrf

stock_bp = Blueprint("stock", __name__)


# ======================================================================
# STOCK MOVEMENTS (recent sale activity)
# ======================================================================
# GET /api/stock/movements
# Returns recent stock movements aggregated from sales data.
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
# POST /api/stock/adjust
# Use this to add stock (positive change) or remove stock (negative change)
# for reasons other than a sale (e.g., receiving a shipment, damage, return).
#
# Request body (JSON):
#   {
#     "product_id": 1,
#     "quantity_change": 50,     // positive = add, negative = remove
#     "reason": "New shipment received"
#   }
# ======================================================================
@csrf.exempt
@stock_bp.route("/adjust", methods=["POST"])
@login_required
def adjust_stock():
    uid = session["user_id"]
    data = request.get_json()

    # --- Validate ---
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    product_id = data.get("product_id")
    quantity_change = data.get("quantity_change")

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400
    if quantity_change is None or quantity_change == 0:
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
# GET /api/stock/alerts
# Returns all products that are currently below their reorder level.
# This is a live query — it always reflects the current stock state.
# ======================================================================
@stock_bp.route("/alerts", methods=["GET"])
@login_required
def list_alerts():
    uid = session["user_id"]
    # Query all active products where quantity <= reorder_level
    products = Product.query.filter(
        Product.is_active == True,
        Product.quantity <= Product.reorder_level,
        Product.user_id == uid
    ).order_by(Product.quantity.asc()).all()

    alerts = []
    for product in products:
        alerts.append({
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "current_quantity": product.quantity,
            "reorder_level": product.reorder_level,
            "shortfall": product.reorder_level - product.quantity,
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
# PATCH /api/stock/alerts/resolve
# After restocking a product, the alert can be dismissed.
# The alert will re-appear if the product drops below reorder level again.
#
# Request body (JSON):
#   { "product_id": 5 }
# ======================================================================
@stock_bp.route("/alerts/resolve", methods=["PATCH"])
@login_required
def resolve_alert():
    uid = session["user_id"]
    data = request.get_json()
    if not data or not data.get("product_id"):
        return jsonify({"error": "product_id is required"}), 400

    product = Product.query.filter_by(id=data["product_id"], user_id=uid).first()
    if product is None:
        return jsonify({"error": f"Product #{data['product_id']} not found"}), 404

    # "Resolving" here means we acknowledge the alert.
    # In a full system you'd have a dedicated alerts table with a resolved flag.
    # For now, we just return a success message.
    return jsonify({
        "message": f"Alert resolved for '{product.name}'",
        "product_id": product.id,
        "current_quantity": product.quantity,
        "reorder_level": product.reorder_level,
        "still_low": product.is_low_stock(),
    })
