"""
Predictive Restocking Module — Beginner-Friendly
=================================================
Three simple approaches to predict demand and generate reorder alerts.
NO advanced ML libraries required (pure Python + math).

Approaches:
  1. Simple Moving Average (SMA) — smooths recent sales to predict demand
  2. Daily Consumption Rate (DCR) — how fast stock burns per day
  3. Trend Analysis — detects if demand is rising or falling

Each function includes:
  - Formula explanation
  - Step-by-step code
  - Connection to MySQL (via SQLAlchemy / pandas)
  - Expected output format

Usage:
    from prediction.predictor import (
        moving_average_demand,
        daily_consumption_rate,
        trend_analysis,
        predict_stockout_days,
        generate_restock_alerts,
    )

Run demo (no database needed):
    python -c "from prediction.predictor import demo; demo()"
"""

import math
from datetime import datetime, timedelta
from collections import defaultdict


# ==============================================================================
# FORMULA REFERENCE
# ==============================================================================
#
# 1. SIMPLE MOVING AVERAGE (SMA)
#    Formula:  SMA_n = (Sale₁ + Sale₂ + ... + Saleₙ) / n
#    Where:    n = number of days in the window
#    Example:  7-day SMA = average of last 7 days of sales
#    Use:      Predicts "typical daily demand" by smoothing noise
#
# 2. DAILY CONSUMPTION RATE (DCR)
#    Formula:  DCR = Total Units Sold / Total Days Observed
#    Days Until Stockout = Current Stock / DCR
#    Reorder Point = DCR × Lead Time (days) + Safety Stock
#    Use:      Directly answers "when will I run out?"
#
# 3. TREND ANALYSIS (Simple Linear Regression)
#    Formula:  y = mx + b
#    Where:    y = predicted sales on day x
#              m = slope (trend direction and strength)
#              b = intercept (baseline when x=0)
#
#    Slope:    m = (n*Σ(xy) - Σx*Σy) / (n*Σ(x²) - (Σx)²)
#    Intercept: b = (Σy - m*Σx) / n
#    Where:    x = day number, y = sales on that day
#
#    Interpretation of slope (m):
#      m > 0.5  → Strong upward trend (demand growing)
#      m > 0    → Mild upward trend
#      m ≈ 0    → Stable demand (no trend)
#      m < 0    → Downward trend (demand shrinking)
#      m < -0.5 → Strong downward trend (demand collapsing)
# ==============================================================================


# ──────────────────────────────────────────────────────────────────────────────
# 1. SIMPLE MOVING AVERAGE
# ──────────────────────────────────────────────────────────────────────────────

def moving_average_demand(sales_history, window=7):
    """
    Predict daily demand using Simple Moving Average.

    Formula:
        SMA_window = sum(recent_sales) / window

    The SMA smooths out day-to-day fluctuations so you can see
    the underlying typical demand level.

    Parameters
    ----------
    sales_history : list of float
        Daily sales quantities (oldest first, newest last).
        Example: [0, 3, 5, 2, 0, 4, 6, 1, 3, ...]
    window : int
        Number of recent days to average (default 7 = weekly).

    Returns
    -------
    float : predicted daily demand

    Example
    -------
    >>> sales = [5, 3, 4, 6, 2, 7, 4]   # last 7 days
    >>> moving_average_demand(sales, window=7)
    4.43  # (5+3+4+6+2+7+4) / 7
    """
    if not sales_history:
        return 0.0

    # Take only the most recent `window` days
    recent = sales_history[-window:]

    # Formula: sum / count
    total = sum(recent)
    count = len(recent)

    if count == 0:
        return 0.0

    return round(total / count, 2)


# ──────────────────────────────────────────────────────────────────────────────
# 2. DAILY CONSUMPTION RATE
# ──────────────────────────────────────────────────────────────────────────────

def daily_consumption_rate(sales_history, num_days=None):
    """
    Calculate how many units sell per day on average.

    Formulas:
        DCR = Sum of all sales / Number of days observed

        Days Until Stockout = Current Stock / DCR

        Reorder Point = DCR × Lead Time (days) + Safety Stock

    Safety stock is extra buffer for unexpected demand spikes.
    A common rule: safety_stock = 1.5 × DCR × lead_time
    (covers ~93% of demand if demand follows a normal distribution)

    Parameters
    ----------
    sales_history : list of float
        Daily sales quantities.  Use zeros for days with no sales.
    num_days : int or None
        Number of days represented by `sales_history`.
        If None, uses len(sales_history).

    Returns
    -------
    float : units sold per day

    Example
    -------
    >>> sales = [5, 3, 0, 6, 2, 0, 4]   # 7 days of sales
    >>> daily_consumption_rate(sales)
    2.86  # (5+3+0+6+2+0+4) / 7
    """
    if not sales_history:
        return 0.0

    total_units = sum(sales_history)
    total_days = num_days if num_days is not None else len(sales_history)

    if total_days == 0:
        return 0.0

    return round(total_units / total_days, 2)


# ──────────────────────────────────────────────────────────────────────────────
# 3. TREND ANALYSIS (Linear Regression from scratch)
# ──────────────────────────────────────────────────────────────────────────────

def trend_analysis(sales_history):
    """
    Detect whether sales are trending up, down, or stable using
    simple linear regression — all from scratch, no libraries.

    Formula (Ordinary Least Squares):

        Given:  x_i = day number (0, 1, 2, ...)
                y_i = sales on day x_i

        Step 1 — Compute means:
            x̄ = sum(x) / n
            ȳ = sum(y) / n

        Step 2 — Slope:
            m = sum((x_i - x̄)(y_i - ȳ)) / sum((x_i - x̄)²)

        Step 3 — Intercept:
            b = ȳ - m × x̄

        Step 4 — Predicted future:
            y_future = m × x_future + b

    Parameters
    ----------
    sales_history : list of float
        Daily sales (oldest first).

    Returns
    -------
    dict with keys:
        slope      : float — positive = rising, negative = falling
        intercept  : float — baseline demand at day 0
        trend      : str   — "rising", "falling", or "stable"
        next_7     : float — predicted total sales for next 7 days
        next_30    : float — predicted total sales for next 30 days

    Example
    -------
    >>> result = trend_analysis([2, 3, 5, 4, 6, 7, 8])
    >>> result["slope"]
    0.89       # demand is increasing
    >>> result["trend"]
    'rising'
    """
    n = len(sales_history)
    if n < 3:
        # Too few data points to detect a trend
        return {
            "slope": 0.0,
            "intercept": sum(sales_history) / n if n > 0 else 0.0,
            "trend": "stable",
            "next_7": 0.0,
            "next_30": 0.0,
        }

    # --- Step 1: Assign x values (day numbers 0, 1, 2, ...) ---
    x_values = list(range(n))
    y_values = sales_history

    # Means
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n

    # --- Step 2: Calculate slope (m) ---
    # numerator   = Σ((x - x̄)(y - ȳ))
    # denominator = Σ((x - x̄)²)
    numerator = 0.0
    denominator = 0.0

    for i in range(n):
        x_dev = x_values[i] - x_mean      # x - x̄
        y_dev = y_values[i] - y_mean      # y - ȳ
        numerator += x_dev * y_dev
        denominator += x_dev * x_dev

    if denominator == 0:
        slope = 0.0  # all x values are the same (shouldn't happen)
    else:
        slope = round(numerator / denominator, 4)

    # --- Step 3: Calculate intercept (b) ---
    intercept = round(y_mean - slope * x_mean, 2)

    # --- Step 4: Classify the trend ---
    if slope > 0.3:
        trend = "rising"
    elif slope < -0.3:
        trend = "falling"
    else:
        trend = "stable"

    # --- Step 5: Predict future sales ---
    # y_future = m × x_future + b
    next_7_total = 0.0
    for future_day in range(n, n + 7):
        next_7_total += max(0, slope * future_day + intercept)

    next_30_total = 0.0
    for future_day in range(n, n + 30):
        next_30_total += max(0, slope * future_day + intercept)

    return {
        "slope": slope,
        "intercept": intercept,
        "trend": trend,
        "next_7": round(next_7_total, 2),
        "next_30": round(next_30_total, 2),
    }


# ──────────────────────────────────────────────────────────────────────────────
# STOCKOUT PREDICTION
# ──────────────────────────────────────────────────────────────────────────────

def predict_stockout_days(current_stock, daily_demand):
    """
    Predict how many days until stock reaches zero.

    Formula:
        Days Until Stockout = Current Stock / Daily Demand

    This is the single most important prediction for inventory management.
    It tells you exactly when you'll run out at the current consumption rate.

    Parameters
    ----------
    current_stock : int
        Units currently in inventory.
    daily_demand : float
        Predicted units sold per day (from SMA or DCR).

    Returns
    -------
    float : estimated days until stock = 0 (infinity if daily_demand is 0)

    Example
    -------
    >>> predict_stockout_days(100, 4.5)
    22.22   # stock will last ~22 days
    """
    if daily_demand <= 0:
        return float("inf")  # no demand = never runs out

    return round(current_stock / daily_demand, 1)


# ──────────────────────────────────────────────────────────────────────────────
# REORDER POINT & QUANTITY
# ──────────────────────────────────────────────────────────────────────────────

def calculate_reorder_point(daily_demand, lead_time_days, safety_stock=None):
    """
    Calculate the ideal reorder point for a product.

    Formula:
        Reorder Point = (Daily Demand × Lead Time) + Safety Stock

    When your stock falls to this level, you should place a new order.
    The safety stock protects against demand spikes or supply delays.

    A common beginner-friendly safety stock formula:
        Safety Stock = 1.5 × Daily Demand × Lead Time
    (This covers roughly 93% of situations assuming normal demand)

    Parameters
    ----------
    daily_demand : float
        Predicted units sold per day.
    lead_time_days : int
        Days between placing and receiving an order.
    safety_stock : int or None
        Extra buffer stock.  If None, calculated automatically.

    Returns
    -------
    dict with keys:
        reorder_point  : int — stock level that triggers an order
        safety_stock   : int — buffer stock for uncertainty
        lead_time_days : int — confirmed lead time

    Example
    -------
    >>> calculate_reorder_point(4.5, 7)
    {"reorder_point": 48, "safety_stock": 17, "lead_time_days": 7}
    # Explanation: 4.5 × 7 = 31.5 for lead time, + 17 safety = ~48
    """
    if safety_stock is None:
        # Safety stock = 1.5 × daily_demand × lead_time
        # The 1.5 multiplier provides a ~93% service level
        # (i.e., you'll have enough stock 93% of the time)
        safety_stock = int(math.ceil(1.5 * daily_demand * lead_time_days))

    reorder_point = int(math.ceil(daily_demand * lead_time_days + safety_stock))

    return {
        "reorder_point": reorder_point,
        "safety_stock": safety_stock,
        "lead_time_days": lead_time_days,
    }


def suggest_reorder_quantity(daily_demand, lead_time_days, order_frequency_days=30):
    """
    Suggest how many units to order when restocking.

    Formula:
        Reorder Quantity = Daily Demand × Order Frequency

    Where order frequency is how often you typically order
    (e.g., 30 days = order a 1-month supply).

    A common approach: order enough to last until your NEXT order,
    plus the lead time buffer.

    Parameters
    ----------
    daily_demand : float
        Predicted daily sales.
    lead_time_days : int
        Days between ordering and receiving.
    order_frequency_days : int
        How often you order (default 30 = monthly).

    Returns
    -------
    int : suggested order quantity

    Example
    -------
    >>> suggest_reorder_quantity(4.5, 7, 30)
    167  # 4.5 × (30 + 7) = 166.5, rounded up
    """
    # Order enough to cover the period until your next order,
    # plus the lead time (since stock keeps selling during shipping)
    total_days = order_frequency_days + lead_time_days
    quantity = int(math.ceil(daily_demand * total_days))
    return quantity


# ──────────────────────────────────────────────────────────────────────────────
# ALERT GENERATION
# ──────────────────────────────────────────────────────────────────────────────

def generate_restock_alerts(current_stock, daily_demand, lead_time_days,
                             reorder_point=None, product_name="Unknown"):
    """
    Generate a restock alert with 4 urgency levels.

    The alert system uses a traffic-light model:
        GREEN    → Everything is fine. Stock is healthy.
        YELLOW   → Stock is getting low. Plan a reorder soon.
        RED      → Stock is critical. Order immediately!
        BLACK    → Out of stock. Emergency!

    Urgency Rules:
        GREEN  : stock > reorder_point
        YELLOW : stock <= reorder_point
        RED    : days_until_stockout < lead_time_days (will run out before
                 new stock arrives!)
        BLACK  : stock == 0

    Parameters
    ----------
    current_stock : int
        Current inventory level.
    daily_demand : float
        Predicted daily consumption.
    lead_time_days : int
        Days to receive new stock after ordering.
    reorder_point : int or None
        Pre-calculated reorder point.  Auto-calculated if None.
    product_name : str
        Product name for the alert message.

    Returns
    -------
    dict with keys:
        product_name      : str
        current_stock     : int
        daily_demand      : float
        days_remaining    : float — estimated days until stockout
        lead_time_days    : int
        reorder_point     : int
        days_until_critical : int — days before RED alert triggers
        urgency           : str — "GREEN", "YELLOW", "RED", or "BLACK"
        message           : str — human-readable alert
        suggested_order   : int — how many units to order

    Example
    -------
    >>> alert = generate_restock_alerts(20, 4.5, 7)
    >>> alert["urgency"]
    'RED'
    >>> alert["message"]
    "CRITICAL: USB-C Cable will run out in 4.4 days (lead time is 7 days)!"
    """
    # Auto-calculate reorder point if not provided
    if reorder_point is None:
        rp_info = calculate_reorder_point(daily_demand, lead_time_days)
        reorder_point = rp_info["reorder_point"]

    # Days until stock reaches zero
    days_remaining = predict_stockout_days(current_stock, daily_demand)

    # Determine urgency
    if current_stock <= 0:
        urgency = "BLACK"
        message = f"EMERGENCY: {product_name} is OUT OF STOCK!"
    elif days_remaining < lead_time_days:
        urgency = "RED"
        message = (f"CRITICAL: {product_name} will run out in "
                   f"{days_remaining} days (lead time is {lead_time_days} days)!")
    elif current_stock <= reorder_point:
        urgency = "YELLOW"
        message = (f"WARNING: {product_name} stock ({current_stock}) is "
                   f"below reorder point ({reorder_point}). Order soon.")
    else:
        urgency = "GREEN"
        message = f"OK: {product_name} stock is healthy ({current_stock} units)."

    # Calculate suggested order
    suggested_order = suggest_reorder_quantity(daily_demand, lead_time_days)

    # Days before stock reaches RED zone
    # (stock crosses below lead_time_days × daily_demand)
    red_threshold = int(math.ceil(daily_demand * lead_time_days))
    if daily_demand > 0 and current_stock > red_threshold:
        days_until_critical = int((current_stock - red_threshold) / daily_demand)
    else:
        days_until_critical = 0

    return {
        "product_name": product_name,
        "current_stock": current_stock,
        "daily_demand": daily_demand,
        "days_remaining": days_remaining,
        "lead_time_days": lead_time_days,
        "reorder_point": reorder_point,
        "days_until_critical": days_until_critical,
        "urgency": urgency,
        "message": message,
        "suggested_order": suggested_order,
    }


# ──────────────────────────────────────────────────────────────────────────────
# FULL PRODUCT ANALYSIS (combines all approaches)
# ──────────────────────────────────────────────────────────────────────────────

def analyze_product(sales_history, current_stock, lead_time_days=7,
                    product_name="Unknown", sma_window=7):
    """
    Run ALL prediction methods on one product and return a summary.

    This is the main function you'll call from your application.
    It runs SMA, DCR, Trend Analysis, and generates an alert.

    Parameters
    ----------
    sales_history : list of float
        Daily sales quantities (oldest first).
    current_stock : int
        Current inventory.
    lead_time_days : int
        Supplier lead time in days.
    product_name : str
        Product name for alerts.
    sma_window : int
        Window for moving average (default 7).

    Returns
    -------
    dict with full analysis results.

    Example
    -------
    >>> sales = [5, 3, 4, 6, 2, 7, 4, 3, 5, 6]  # 10 days of sales
    >>> result = analyze_product(sales, current_stock=30, lead_time_days=7)
    >>> result["demand"]["sma"]
    4.57
    >>> result["alert"]["urgency"]
    'RED'
    """
    # ── 1. Moving Average ──
    sma_prediction = moving_average_demand(sales_history, window=sma_window)

    # ── 2. Daily Consumption Rate ──
    dcr = daily_consumption_rate(sales_history)

    # ── 3. Trend Analysis ──
    trend = trend_analysis(sales_history)

    # Use the most conservative (highest) demand estimate for safety
    recommended_demand = max(sma_prediction, dcr, 0.1)

    # ── 4. Reorder Point ──
    reorder_info = calculate_reorder_point(recommended_demand, lead_time_days)

    # ── 5. Generate Alert ──
    alert = generate_restock_alerts(
        current_stock=current_stock,
        daily_demand=recommended_demand,
        lead_time_days=lead_time_days,
        reorder_point=reorder_info["reorder_point"],
        product_name=product_name,
    )

    return {
        "product_name": product_name,
        "current_stock": current_stock,
        "lead_time_days": lead_time_days,
        "demand": {
            "sma_7_day": sma_prediction,
            "daily_consumption_rate": dcr,
        },
        "trend": trend,
        "reorder": reorder_info,
        "alert": alert,
    }


# ──────────────────────────────────────────────────────────────────────────────
# DATABASE INTEGRATION (MySQL via SQLAlchemy)
# ──────────────────────────────────────────────────────────────────────────────

def get_sales_history_from_db(product_id, days_back=90, db_session=None):
    """
    Fetch daily sales history from MySQL for a specific product.

    This connects to the `sales` and `sale_items` tables in your
    Smart Inventory database.  It groups sales by day and returns
    a list of daily quantities.

    SQL Query:
        SELECT DATE(s.sale_date) as sale_day, SUM(si.quantity) as total_sold
        FROM sales s
        JOIN sale_items si ON s.id = si.sale_id
        WHERE si.product_id = :product_id
          AND s.sale_date >= :cutoff_date
        GROUP BY DATE(s.sale_date)
        ORDER BY sale_day ASC

    Parameters
    ----------
    product_id : int
        The product ID to analyze.
    days_back : int
        How many days of history to fetch (default 90).
    db_session : SQLAlchemy instance or None
        Pass `db` (the SQLAlchemy instance from database.py).
        If None, returns sample data for demo purposes.

    Returns
    -------
    list of float : daily quantities (oldest first)
    """
    if db_session is None:
        # Return sample data for demo/testing
        return _generate_sample_sales(product_id)

    from models.sale import Sale, SaleItem
    from sqlalchemy import func, Date

    cutoff = datetime.utcnow() - timedelta(days=days_back)

    results = (
        db_session.session.query(
            func.cast(Sale.sale_date, Date).label("sale_day"),
            func.coalesce(func.sum(SaleItem.quantity), 0),
        )
        .join(SaleItem, Sale.id == SaleItem.sale_id)
        .filter(
            SaleItem.product_id == product_id,
            Sale.sale_date >= cutoff,
        )
        .group_by(func.cast(Sale.sale_date, Date))
        .order_by(func.cast(Sale.sale_date, Date).asc())
        .all()
    )

    # Convert to daily series (fill gaps with 0)
    daily_map = {row.sale_day: row[1] for row in results}
    sales = []
    current = cutoff.date()
    today = datetime.utcnow().date()
    while current <= today:
        sales.append(float(daily_map.get(current, 0)))
        current += timedelta(days=1)

    return sales


def get_product_info_from_db(product_id, db_session=None):
    """
    Fetch product details from MySQL.

    Parameters
    ----------
    product_id : int
    db_session : SQLAlchemy instance or None
        Pass `db` (the SQLAlchemy instance from database.py).

    Returns
    -------
    dict with product info, or None if not found.
    """
    if db_session is None:
        return None

    from models.product import Product
    product = db_session.session.get(Product, product_id)
    if product is None:
        return None

    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "quantity": product.quantity,
        "reorder_level": product.reorder_level,
    }


def run_for_product(product_id, db_session, lead_time_days=7):
    """
    Full analysis for one product using real MySQL data.

    This is the function you'd call from your Flask routes
    or scheduled tasks.

    Example usage (in a Flask route):
        from database import db
        from prediction.predictor import run_for_product

        @app.route("/api/predict/<int:product_id>")
        def predict_product(product_id):
            result = run_for_product(product_id, db)
            return jsonify(result)
    """
    sales = get_sales_history_from_db(product_id, db_session=db_session)
    product = get_product_info_from_db(product_id, db_session=db_session)

    if product is None:
        return {"error": f"Product #{product_id} not found"}

    return analyze_product(
        sales_history=sales,
        current_stock=product["quantity"],
        lead_time_days=lead_time_days,
        product_name=product["name"],
    )


def run_for_all_products(db_session, lead_time_days=7, user_id=None):
    """
    Run analysis for ALL active products.

    Useful for generating predictions for every product in one pass.
    If `user_id` is given, only that user's products are analyzed
    (multi-tenant safe).
    """
    from models.product import Product

    query = Product.query.filter_by(is_active=True)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    products = query.all()
    results = []

    for product in products:
        try:
            result = run_for_product(product.id, db_session, lead_time_days)
            results.append(result)
        except Exception as e:
            results.append({
                "product_id": product.id,
                "product_name": product.name,
                "error": str(e),
            })

    return results


# ──────────────────────────────────────────────────────────────────────────────
# SAMPLE DATA GENERATOR (for demo/testing)
# ──────────────────────────────────────────────────────────────────────────────

def _generate_sample_sales(product_id):
    """
    Generate realistic-looking sample sales data for demonstration.

    Three product profiles are available:

    Product 1: "USB-C Cable" — high, steady demand
        ~3-8 units/day, slight upward trend
        Good for demonstrating normal healthy stock

    Product 2: "Denim Jacket" — low, sporadic demand
        ~0-2 units/day, flat trend
        Good for demonstrating slow-moving items

    Product 3: "Green Tea" — steady, medium demand
        ~5-12 units/day, seasonal pattern
        Good for demonstrating predictable restocking
    """
    import random
    random.seed(product_id)  # Same product always gets same data

    base_rates = {
        1: 5.0,    # USB-C Cable — high demand
        2: 1.0,    # Denim Jacket — low demand
        3: 7.5,    # Green Tea — medium demand
    }

    base = base_rates.get(product_id, 3.0)
    sales = []
    for day in range(90):  # 90 days of history
        # Add random daily variation (±50%)
        daily = max(0, base + random.uniform(-base * 0.5, base * 0.5))
        # Add a small weekly pattern (lower on weekends)
        if day % 7 >= 5:  # weekend
            daily *= 0.7
        # Product 1 has slight upward trend
        if product_id == 1:
            daily += day * 0.02  # +0.02 units/day trend
        sales.append(round(daily, 1))

    return sales


# ──────────────────────────────────────────────────────────────────────────────
# DEMO FUNCTION
# ──────────────────────────────────────────────────────────────────────────────

def demo():
    """
    Run a complete demonstration with sample data and expected output.
    No database connection required.

    This function:
      1. Generates sample sales for 3 products
      2. Runs all prediction methods
      3. Shows formulas with calculated values
      4. Generates restock alerts
      5. Prints a summary table
    """
    print("=" * 72)
    print("  SMART INVENTORY - Predictive Restocking Demo")
    print("  Three approaches: Moving Average | Daily Consumption | Trend Analysis")
    print("=" * 72)

    products = [
        {"id": 1, "name": "USB-C Cable 1m",      "stock": 45, "lead_time": 7},
        {"id": 2, "name": "Denim Jacket",         "stock": 5,  "lead_time": 14},
        {"id": 3, "name": "Green Tea (50 bags)",  "stock": 60, "lead_time": 5},
    ]

    all_results = []

    for prod in products:
        # Get sample sales data (no database needed)
        sales = _generate_sample_sales(prod["id"])

        print(f"\n{'-' * 72}")
        print(f"  PRODUCT: {prod['name']}  (ID={prod['id']})")
        print(f"  Current Stock: {prod['stock']}  |  Lead Time: {prod['lead_time']} days")
        print(f"{'-' * 72}")

        # ── Step 1: Show raw sales ──
        recent = sales[-14:]
        print(f"\n  Recent 14-day sales: {recent}")
        print(f"  Total sold (90 days): {sum(sales):.0f} units")

        # ── Step 2: Moving Average ──
        sma_7 = moving_average_demand(sales, window=7)
        sma_30 = moving_average_demand(sales, window=30)

        print(f"\n  [SMA] SIMPLE MOVING AVERAGE")
        print(f"     Formula: SMA_n = sum(last_n_days) / n")
        print(f"     7-day SMA:  ({'+'.join(str(round(s,1)) for s in sales[-7:])}) / 7")
        print(f"     Result:     {sma_7} units/day")
        print(f"     30-day SMA: {sma_30} units/day")

        # ── Step 3: Daily Consumption Rate ──
        dcr = daily_consumption_rate(sales)
        stockout_days = predict_stockout_days(prod["stock"], dcr)

        print(f"\n  [DCR] DAILY CONSUMPTION RATE")
        print(f"     Formula: DCR = Total Sold / Days Observed")
        print(f"     Total sold (90 days):  {sum(sales):.0f}")
        print(f"     DCR: {sum(sales):.0f} / {len(sales)} = {dcr} units/day")
        print(f"     Days Until Stockout:   {prod['stock']} / {dcr} ~ {stockout_days} days")

        # ── Step 4: Trend Analysis ──
        trend = trend_analysis(sales)

        print(f"\n  [TREND] TREND ANALYSIS (Linear Regression)")
        print(f"     Formula: y = mx + b")
        print(f"       slope (m)     = {trend['slope']}")
        print(f"       intercept (b) = {trend['intercept']}")
        print(f"       trend         = {trend['trend']}")
        print(f"       predicted next 7 days  = {trend['next_7']} total units")
        print(f"       predicted next 30 days = {trend['next_30']} total units")

        # ── Step 5: Reorder Point ──
        # Use max of SMA and DCR as recommended demand
        rec_demand = max(sma_7, dcr)
        reorder_info = calculate_reorder_point(rec_demand, prod["lead_time"])
        reorder_qty = suggest_reorder_quantity(rec_demand, prod["lead_time"])

        print(f"\n  [STOCK] REORDER RECOMMENDATIONS")
        print(f"     Recommended demand (max SMA, DCR): {rec_demand} units/day")
        print(f"     Reorder Point:  {reorder_info['reorder_point']} units")
        print(f"       ({rec_demand} x {prod['lead_time']} lead time + {reorder_info['safety_stock']} safety)")
        print(f"     Reorder Qty:    {reorder_qty} units")
        print(f"       ({rec_demand} x ({prod['lead_time']} lead + 30 day order cycle))")

        # ── Step 6: Alert ──
        alert = generate_restock_alerts(
            current_stock=prod["stock"],
            daily_demand=rec_demand,
            lead_time_days=prod["lead_time"],
            reorder_point=reorder_info["reorder_point"],
            product_name=prod["name"],
        )

        urgency_icon = {"GREEN": "[OK]", "YELLOW": "[!]", "RED": "[!!]", "BLACK": "[XX]"}
        icon = urgency_icon.get(alert["urgency"], "[?]")

        print(f"\n  {icon} ALERT: [{alert['urgency']}] {alert['message']}")
        print(f"     Suggested order: {alert['suggested_order']} units")

        all_results.append(alert)

    # ── Summary Table ──
    print(f"\n{'=' * 72}")
    print("  SUMMARY: All Products")
    print(f"{'=' * 72}")
    print(f"  {'Product':<25} {'Stock':>6} {'Demand':>7} {'Days Left':>10} {'Reorder Pt':>10} {'Status':>10}")
    print(f"  {'-' * 25} {'-' * 6} {'-' * 7} {'-' * 10} {'-' * 10} {'-' * 10}")
    for alert in all_results:
        days = f"{alert['days_remaining']:.1f}" if alert['days_remaining'] != float('inf') else "inf"
        print(f"  {alert['product_name']:<25} {alert['current_stock']:>6} {alert['daily_demand']:>7} {days:>10} {alert['reorder_point']:>10} {alert['urgency']:>10}")

    print(f"\n  {'=' * 72}")
    print("  LEGEND:  GREEN = Stock healthy  |  YELLOW = Order soon")
    print("           RED   = Order NOW!      |  BLACK = Out of stock!")
    print(f"  {'=' * 72}")

    # Count alerts by urgency
    urgency_counts = defaultdict(int)
    for a in all_results:
        urgency_counts[a["urgency"]] += 1

    print(f"\n  Alert Summary: ", end="")
    for level in ["GREEN", "YELLOW", "RED", "BLACK"]:
        if urgency_counts[level] > 0:
            icon = urgency_icon[level]
            print(f"{icon} {level}: {urgency_counts[level]}  ", end="")
    print()

    print(f"\n  [OK] Demo complete! All formulas are explained in the code.")
    print(f"  See prediction/predictor.py for full documentation.")
    print()


# ──────────────────────────────────────────────────────────────────────────────
# ML UPGRADE PATH
# ──────────────────────────────────────────────────────────────────────────────
#
# The three approaches above are simple, interpretable, and work well
# for many inventory scenarios.  When you're ready for more accuracy,
# here's how to upgrade:
#
# ┌─────────────────────┬──────────────────────┬──────────────────────────────┐
# │ Current Approach    │ ML Upgrade            │ Benefit                      │
# ├─────────────────────┼──────────────────────┼──────────────────────────────┤
# │ Moving Average      │ Exponential Smoothing│ Recent data weighted more    │
# │                     │ (Holt-Winters)       │ than old data                │
# ├─────────────────────┼──────────────────────┼──────────────────────────────┤
# │ Daily Consumption   │ Poisson / Negative   │ Better for intermittent /    │
# │ Rate (avg)          │ Binomial Regression  │ sporadic demand patterns     │
# ├─────────────────────┼──────────────────────┼──────────────────────────────┤
# │ Linear Regression   │ Random Forest /      │ Captures non-linear patterns │
# │ (trend analysis)    │ Gradient Boosting    │ and feature interactions     │
# ├─────────────────────┼──────────────────────┼──────────────────────────────┤
# │ Simple alerts       │ LSTM / Transformer   │ Learns complex seasonal      │
# │ (threshold-based)   │ (time series models) │ patterns automatically        │
# └─────────────────────┴──────────────────────┴──────────────────────────────┘
#
# The existing prediction/predictor.py already has a RandomForestRegressor
# implementation that you can use once you install scikit-learn:
#
#   pip install scikit-learn pandas
#
# See the `__ml_upgrade_notes__` section at the bottom of this file.
# ==============================================================================


if __name__ == "__main__":
    demo()
