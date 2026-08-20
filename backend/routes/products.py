"""
Product Routes
==============
Full CRUD (Create, Read, Update, Delete) for products.

Endpoints:
  GET    /api/products          — List all products (with search & pagination)
  GET    /api/products/<id>     — Get a single product by ID
  POST   /api/products          — Add a new product (manager+)
  PUT    /api/products/<id>     — Update an existing product (manager+)
  DELETE /api/products/<id>     — Soft-delete a product (manager+)
  GET    /api/products/low-stock — List products below reorder level

Role model:
  viewer  — read-only
  manager — manage products, sales, stock
  admin   — everything (also passes manager checks)
"""

from flask import Blueprint, request, jsonify, session
from database import db
from models.product import Product
from models.supplier import Supplier
from models.category import Category
from routes.decorators import login_required, role_required

products_bp = Blueprint("products", __name__)


# ======================================================================
# LIST / CREATE CATEGORIES
# ======================================================================
@products_bp.route("/categories", methods=["GET"])
@login_required
def list_categories():
    uid = session["user_id"]
    cats = Category.query.filter_by(is_active=True, user_id=uid).order_by(Category.name).all()
    if cats:
        return jsonify([{"id": c.id, "name": c.name} for c in cats])

    legacy = db.session.query(Product.category).distinct().filter(
        Product.is_active == True,
        Product.category != None,
        Product.category != "",
        Product.user_id == uid
    ).order_by(Product.category).all()
    return jsonify([{"id": c[0], "name": c[0]} for c in legacy])


@products_bp.route("/categories", methods=["POST"])
@role_required("manager", "admin")
def create_category():
    uid = session["user_id"]
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Category name is required"}), 400

    name = data["name"].strip()
    if not name:
        return jsonify({"error": "Category name cannot be empty"}), 400
    if len(name) > 100:
        return jsonify({"error": "Category name must be 100 characters or fewer"}), 400

    existing = Category.query.filter_by(name=name, user_id=uid).first()
    if existing:
        return jsonify({"id": existing.id, "name": existing.name}), 200

    cat = Category(name=name, user_id=uid)
    db.session.add(cat)
    db.session.commit()
    return jsonify({"id": cat.id, "name": cat.name}), 201


# ======================================================================
# LIST / SEARCH PRODUCTS
# ======================================================================
@products_bp.route("/", methods=["GET"])
@login_required
def list_products():
    uid = session["user_id"]
    # --- Start with all active products ---
    query = Product.query.filter_by(is_active=True, user_id=uid)

    # --- Apply search filter (if provided) ---
    search_term = request.args.get("q", "")
    if search_term:
        query = query.filter(
            Product.name.like(f"%{search_term}%") |
            Product.sku.like(f"%{search_term}%")
        )

    # --- Apply category filter (scoped to the current user) ---
    category = request.args.get("category", "")
    if category:
        cat_obj = Category.query.filter_by(name=category, user_id=uid).first()
        if cat_obj:
            query = query.filter(Product.category_id == cat_obj.id)
        else:
            # No matching category → return empty
            return jsonify({"products": [], "total": 0, "page": 1, "pages": 0, "per_page": 0})

    # --- Pagination ---
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)

    pagination = query.order_by(Product.name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    products = [p.to_dict() for p in pagination.items]

    return jsonify({
        "products": products,
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": per_page,
    })


# ======================================================================
# GET SINGLE PRODUCT
# ======================================================================
@products_bp.route("/<int:product_id>", methods=["GET"])
@login_required
def get_product(product_id):
    uid = session["user_id"]
    product = Product.query.filter_by(id=product_id, user_id=uid).first()

    if product is None:
        return jsonify({"error": "Product not found"}), 404

    return jsonify({"product": product.to_dict()})


# ======================================================================
# ADD PRODUCT
# ======================================================================
@products_bp.route("/", methods=["POST"])
@role_required("manager", "admin")
def add_product():
    uid = session["user_id"]
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # --- Validate required fields ---
    required_fields = ["name", "sku", "unit_price"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({
            "error": f"Missing required fields: {', '.join(missing)}"
        }), 400

    # --- Validate numeric fields ---
    try:
        unit_price = float(data["unit_price"])
    except (TypeError, ValueError):
        return jsonify({"error": "unit_price must be a number"}), 400
    if unit_price < 0:
        return jsonify({"error": "unit_price cannot be negative"}), 400

    quantity = data.get("quantity", 0)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return jsonify({"error": "quantity must be an integer"}), 400
    if quantity < 0:
        return jsonify({"error": "quantity cannot be negative"}), 400

    reorder_level = data.get("reorder_level", 10)
    try:
        reorder_level = int(reorder_level)
    except (TypeError, ValueError):
        return jsonify({"error": "reorder_level must be an integer"}), 400

    # --- Check for duplicate SKU (within same user) ---
    if Product.query.filter_by(sku=data["sku"], user_id=uid).first():
        return jsonify({"error": f"SKU '{data['sku']}' already exists"}), 409

    # --- Check for duplicate barcode (if provided, within same user) ---
    if data.get("barcode") and Product.query.filter_by(barcode=data["barcode"], user_id=uid).first():
        return jsonify({"error": f"Barcode '{data['barcode']}' already exists"}), 409

    # --- Validate supplier_id (must belong to the current user) ---
    if data.get("supplier_id"):
        supplier = Supplier.query.filter_by(id=data["supplier_id"], user_id=uid).first()
        if not supplier:
            return jsonify({"error": f"Supplier #{data['supplier_id']} not found"}), 404

    # --- Validate category_id ownership (if provided) ---
    category_id = data.get("category_id")
    if category_id is not None:
        cat = Category.query.filter_by(id=category_id, user_id=uid).first()
        if not cat:
            return jsonify({"error": f"Category #{category_id} not found"}), 404

    category_name = data.get("category", "General")
    if not category_id and category_name:
        existing = Category.query.filter_by(name=category_name, user_id=uid).first()
        if existing:
            category_id = existing.id
        elif category_name != "General":
            cat = Category(name=category_name, user_id=uid)
            db.session.add(cat)
            db.session.flush()
            category_id = cat.id

    # Fall back to (or create) the user's "General" category
    if not category_id:
        general = Category.query.filter_by(name="General", user_id=uid).first()
        if not general:
            general = Category(name="General", user_id=uid)
            db.session.add(general)
            db.session.flush()
        category_id = general.id

    product = Product(
        user_id=uid,
        name=data["name"],
        sku=data["sku"],
        description=data.get("description", ""),
        quantity=quantity,
        reorder_level=reorder_level,
        unit_price=unit_price,
        category_id=category_id,
        category=category_name,
        supplier_id=data.get("supplier_id"),
        barcode=data.get("barcode"),
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        "message": "Product added successfully",
        "product": product.to_dict(),
    }), 201


# ======================================================================
# UPDATE PRODUCT
# ======================================================================
@products_bp.route("/<int:product_id>", methods=["PUT"])
@role_required("manager", "admin")
def update_product(product_id):
    uid = session["user_id"]
    product = Product.query.filter_by(id=product_id, user_id=uid).first()
    if product is None:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # --- Update only the fields that were sent (partial update) ---
    if "name" in data:
        product.name = data["name"]

    if "sku" in data:
        existing = Product.query.filter(
            Product.sku == data["sku"],
            Product.id != product_id,
            Product.user_id == uid
        ).first()
        if existing:
            return jsonify({"error": f"SKU '{data['sku']}' is already in use"}), 409
        product.sku = data["sku"]

    if "description" in data:
        product.description = data["description"]

    if "quantity" in data:
        try:
            product.quantity = int(data["quantity"])
        except (TypeError, ValueError):
            return jsonify({"error": "quantity must be an integer"}), 400
        if product.quantity < 0:
            return jsonify({"error": "quantity cannot be negative"}), 400

    if "reorder_level" in data:
        try:
            product.reorder_level = int(data["reorder_level"])
        except (TypeError, ValueError):
            return jsonify({"error": "reorder_level must be an integer"}), 400

    if "unit_price" in data:
        try:
            unit_price = float(data["unit_price"])
        except (TypeError, ValueError):
            return jsonify({"error": "unit_price must be a number"}), 400
        if unit_price < 0:
            return jsonify({"error": "unit_price cannot be negative"}), 400
        product.unit_price = unit_price

    if "category_id" in data:
        if data["category_id"] is not None:
            cat = Category.query.filter_by(id=data["category_id"], user_id=uid).first()
            if not cat:
                return jsonify({"error": f"Category #{data['category_id']} not found"}), 404
        product.category_id = data["category_id"]

    if "category" in data:
        product.category = data["category"]
        if not data.get("category_id"):
            existing = Category.query.filter_by(name=data["category"], user_id=uid).first()
            if existing:
                product.category_id = existing.id
            elif data["category"] != "General":
                cat = Category(name=data["category"], user_id=uid)
                db.session.add(cat)
                db.session.flush()
                product.category_id = cat.id

    if "supplier_id" in data:
        if data["supplier_id"] is not None:
            supplier = Supplier.query.filter_by(id=data["supplier_id"], user_id=uid).first()
            if not supplier:
                return jsonify({"error": f"Supplier #{data['supplier_id']} not found"}), 404
        product.supplier_id = data["supplier_id"]

    if "barcode" in data:
        if data["barcode"]:
            existing = Product.query.filter(
                Product.barcode == data["barcode"],
                Product.id != product_id,
                Product.user_id == uid
            ).first()
            if existing:
                return jsonify({"error": f"Barcode '{data['barcode']}' already in use"}), 409
        product.barcode = data["barcode"]

    db.session.commit()

    return jsonify({
        "message": "Product updated successfully",
        "product": product.to_dict(),
    })


# ======================================================================
# DELETE PRODUCT (soft-delete)
# ======================================================================
@products_bp.route("/<int:product_id>", methods=["DELETE"])
@role_required("manager", "admin")
def delete_product(product_id):
    uid = session["user_id"]
    product = Product.query.filter_by(id=product_id, user_id=uid).first()
    if product is None:
        return jsonify({"error": "Product not found"}), 404

    # Soft delete: just mark as inactive
    product.is_active = False
    db.session.commit()

    return jsonify({"message": "Product deleted successfully"})


# ======================================================================
# LOW STOCK PRODUCTS
# ======================================================================
@products_bp.route("/low-stock", methods=["GET"])
@login_required
def low_stock_products():
    uid = session["user_id"]
    products = Product.query.filter(
        Product.is_active == True,
        Product.quantity <= Product.reorder_level,
        Product.user_id == uid
    ).order_by(Product.quantity.asc()).all()

    return jsonify({
        "count": len(products),
        "products": [p.to_dict() for p in products],
    })