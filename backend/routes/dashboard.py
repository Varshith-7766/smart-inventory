from flask import Blueprint, jsonify, session
from datetime import timedelta
from database import db, utcnow
from models.product import Product
from models.sale import Sale
from routes.decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/stats", methods=["GET"])
@login_required
def dashboard_stats():
    uid = session["user_id"]
    total_products = Product.query.filter_by(is_active=True, user_id=uid).count()

    total_sales = db.session.query(
        db.func.coalesce(db.func.sum(Sale.total_amount), 0)
    ).filter(Sale.processed_by == uid).scalar()

    low_stock = Product.query.filter(
        Product.is_active == True,
        Product.quantity <= Product.reorder_level,
        Product.user_id == uid
    ).count()

    thirty_days_ago = utcnow() - timedelta(days=30)
    recent_sales = db.session.query(
        db.func.coalesce(db.func.sum(Sale.total_amount), 0)
    ).filter(Sale.sale_date >= thirty_days_ago, Sale.processed_by == uid).scalar()

    daily_totals = (
        db.session.query(
            db.func.date(Sale.sale_date).label("day"),
            db.func.coalesce(db.func.sum(Sale.total_amount), 0).label("total"),
        )
        .filter(Sale.sale_date >= thirty_days_ago, Sale.processed_by == uid)
        .group_by(db.func.date(Sale.sale_date))
        .order_by(db.func.date(Sale.sale_date))
        .all()
    )
    sales_trend = [{"date": r.day.isoformat(), "total": float(r.total)} for r in daily_totals]

    category_counts = (
        db.session.query(
            Product.category,
            db.func.count(Product.id),
        )
        .filter(
            Product.is_active == True,
            Product.category != None,
            Product.category != "",
            Product.user_id == uid
        )
        .group_by(Product.category)
        .order_by(db.func.count(Product.id).desc())
        .all()
    )
    category_data = [{"name": r[0], "count": r[1]} for r in category_counts]

    return jsonify({
        "total_products": total_products,
        "total_sales": float(total_sales),
        "low_stock_alerts": low_stock,
        "recent_sales_30d": float(recent_sales),
        "sales_trend": sales_trend,
        "categories": category_data,
    })


@dashboard_bp.route("/low-stock", methods=["GET"])
@login_required
def dashboard_low_stock():
    uid = session["user_id"]
    products = Product.query.filter(
        Product.is_active == True,
        Product.quantity <= Product.reorder_level,
        Product.user_id == uid
    ).order_by(Product.quantity.asc()).all()

    return jsonify([{
        "product_id": p.id,
        "product_name": p.name,
        "sku": p.sku,
        "current_quantity": p.quantity,
        "reorder_level": p.reorder_level,
    } for p in products])
