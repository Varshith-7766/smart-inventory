"""
Sales Routes
============
Record new sales and fetch historical sales data.

Endpoints:
  GET    /api/sales          — List sales history (paginated, date-filtered)
  GET    /api/sales/<id>     — Get one sale with all its items
  POST   /api/sales          — Record a new sale
  DELETE /api/sales/<id>     — Void a sale and restore inventory
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
from decimal import Decimal
from database import db
from csrf_init import csrf
from models.product import Product
from models.sale import Sale, SaleItem
from models.inventory_log import InventoryLog
from routes.decorators import login_required

sales_bp = Blueprint("sales", __name__)


# ======================================================================
# LIST SALES HISTORY
# ======================================================================
# GET /api/sales
# Query params:
#   page        — Page number (default 1)
#   per_page    — Items per page (default 50)
#   start_date  — Filter: only sales on or after this date  (ISO format)
#   end_date    — Filter: only sales on or before this date (ISO format)
#   product_id  — Filter: only sales containing this product
# ======================================================================
@sales_bp.route("/", methods=["GET"])
@login_required
def list_sales():
    uid = session["user_id"]
    # --- Build query ---
    query = Sale.query.filter_by(processed_by=uid)

    # --- Date range filter ---
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if start_date:
        query = query.filter(
            Sale.sale_date >= datetime.fromisoformat(start_date)
        )
    if end_date:
        query = query.filter(
            Sale.sale_date <= datetime.fromisoformat(end_date)
        )

    # --- Filter by product (joins through SaleItem) ---
    product_id = request.args.get("product_id", type=int)
    if product_id:
        query = query.join(SaleItem).filter(SaleItem.product_id == product_id)

    # --- Pagination ---
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)

    pagination = query.order_by(Sale.sale_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "sales": [s.to_dict() for s in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


# ======================================================================
# GET SINGLE SALE
# ======================================================================
# GET /api/sales/<id>
# Returns the sale header plus all line items.
# ======================================================================
@sales_bp.route("/<int:sale_id>", methods=["GET"])
@login_required
def get_sale(sale_id):
    uid = session["user_id"]
    sale = Sale.query.filter_by(id=sale_id, processed_by=uid).first()
    if sale is None:
        return jsonify({"error": "Sale not found"}), 404

    return jsonify({"sale": sale.to_dict()})


# ======================================================================
# DELETE SALE (soft-delete / void)
# ======================================================================
# DELETE /api/sales/<id>
# Voids a sale: marks it void and restores inventory.
# ======================================================================
@csrf.exempt
@sales_bp.route("/<int:sale_id>", methods=["DELETE"])
@login_required
def delete_sale(sale_id):
    uid = session["user_id"]
    sale = Sale.query.filter_by(id=sale_id, processed_by=uid).first()
    if sale is None:
        return jsonify({"error": "Sale not found"}), 404

    if sale.status == "void":
        return jsonify({"error": "Sale is already void"}), 400

    previous_qty = []
    for item in sale.items:
        product = Product.query.get(item.product_id)
        if product:
            prev = product.quantity
            product.quantity += item.quantity
            previous_qty.append((item, prev))
            db.session.add(InventoryLog(
                product_id=item.product_id,
                user_id=uid,
                movement_type="return_in",
                quantity_change=item.quantity,
                quantity_before=prev,
                quantity_after=product.quantity,
                reference_type="sale_void",
                notes=f"Voided sale #{sale_id}, returned {item.quantity} x {product.name}",
            ))

    sale.status = "void"
    db.session.commit()

    return jsonify({
        "message": f"Sale #{sale_id} voided. {len(previous_qty)} item(s) returned to stock.",
    })


# ======================================================================
# RECORD A NEW SALE
# ======================================================================
# POST /api/sales
# Request body (JSON):
#   {
#     "customer_name": "Alice Johnson",
#     "notes": "Walk-in customer",
#     "items": [
#       { "product_id": 1, "quantity": 2, "unit_price": 12.99 },
#       { "product_id": 7, "quantity": 1, "unit_price": 8.99 }
#     ]
#   }
#
# What happens:
#   1. Validate that every product exists and has enough stock
#   2. Deduct quantities from product stock
#   3. Calculate the total amount
#   4. Create the Sale + SaleItem records
#   5. Commit everything in one transaction
# ======================================================================
@csrf.exempt
@sales_bp.route("/", methods=["POST"])
@login_required
def record_sale():
    uid = session["user_id"]
    data = request.get_json()

    # --- Validate request structure ---
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    customer_name = data.get("customer_name", "")
    if customer_name and len(customer_name) > 100:
        return jsonify({"error": "customer_name must be 100 characters or fewer"}), 400
    notes = data.get("notes")
    if notes and len(notes) > 500:
        return jsonify({"error": "notes must be 500 characters or fewer"}), 400

    items_data = data.get("items", [])
    if not items_data:
        return jsonify({"error": "Sale must include at least one item"}), 400

    # ----------------------------------------------------------------
    # Process each item: validate stock, calculate totals
    # ----------------------------------------------------------------
    sale_items = []
    grand_total = Decimal("0.00")

    for idx, item_data in enumerate(items_data):
        # --- Validate item fields ---
        if "product_id" not in item_data:
            return jsonify({"error": f"Item {idx}: product_id is required"}), 400
        if "quantity" not in item_data:
            return jsonify({"error": f"Item {idx}: quantity is required"}), 400

        product_id = item_data["product_id"]
        quantity = item_data["quantity"]

        # --- Check if product exists (must belong to current user) ---
        product = Product.query.filter_by(id=product_id, user_id=uid).first()
        if product is None:
            return jsonify({
                "error": f"Item {idx}: Product #{product_id} not found"
            }), 404

        # --- Check stock availability ---
        if product.quantity < quantity:
            return jsonify({
                "error": f"Item {idx}: Insufficient stock for '{product.name}' "
                         f"(available: {product.quantity}, requested: {quantity})"
            }), 400

        # --- Use provided unit price, or fall back to product's current price ---
        unit_price = item_data.get("unit_price", product.unit_price)
        if not isinstance(unit_price, Decimal):
            unit_price = Decimal(str(unit_price))
        total_price = round(quantity * unit_price, 2)
        grand_total += total_price

        previous_qty = product.quantity

        # --- Deduct from stock ---
        product.quantity -= quantity

        # --- Record audit trail ---
        db.session.add(InventoryLog(
            product_id=product_id,
            user_id=uid,
            movement_type="sale_out",
            quantity_change=-quantity,
            quantity_before=previous_qty,
            quantity_after=product.quantity,
            reference_type="sale",
            notes=f"Sale of {quantity} x {product.name}",
        ))

        # --- Create SaleItem (not yet saved — will cascade from Sale) ---
        sale_items.append(SaleItem(
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
        ))

    # ----------------------------------------------------------------
    # Create the Sale record with all its items
    # ----------------------------------------------------------------
    sale = Sale(
        processed_by=uid,
        total_amount=round(grand_total, 2),
        customer_name=customer_name,
        notes=notes,
        payment_method=data.get("payment_method", "cash"),
        items=sale_items,  # SQLAlchemy automatically links these
    )

    db.session.add(sale)
    db.session.commit()

    return jsonify({
        "message": "Sale recorded successfully",
        "sale": sale.to_dict(),
    }), 201
