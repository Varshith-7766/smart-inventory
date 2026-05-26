"""
Run Predictions — Two Modes
============================
1. SIMPLE MODE (default): Uses moving average, DCR, trend analysis
   — No ML libraries required, beginner-friendly

2. ML MODE (optional): Uses scikit-learn RandomForest
   — Requires: pip install scikit-learn pandas

Usage:
    python scripts/run_predictions.py            # Simple mode (default)
    python scripts/run_predictions.py --ml       # ML mode (needs sklearn)

Simple mode runs against the MySQL database and prints alerts.
ML mode stores predictions in the `reorder_predictions` table.
"""

import sys
import os

# Add project root and backend to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from datetime import datetime


def run_simple_mode(db_session):
    """Run beginner-friendly predictions for all products."""
    from prediction.predictor import run_for_all_products

    print("=" * 60)
    print("  SIMPLE PREDICTION MODE")
    print("  Methods: Moving Average + Daily Consumption + Trend")
    print("=" * 60)

    results = run_for_all_products(db_session)

    alerts = {"GREEN": 0, "YELLOW": 0, "RED": 0, "BLACK": 0}

    for r in results:
        alert = r.get("alert", {})
        urgency = alert.get("urgency", "N/A")
        msg = alert.get("message", "N/A")
        print(f"\n  [{urgency}] {r.get('product_name', '?')}")
        print(f"         {msg}")
        if urgency in alerts:
            alerts[urgency] += 1

    print(f"\n{'=' * 60}")
    print(f"  Summary: {alerts['GREEN']} GREEN, {alerts['YELLOW']} YELLOW, "
          f"{alerts['RED']} RED, {alerts['BLACK']} BLACK")
    print(f"  Generated at: {datetime.utcnow().isoformat()}")
    print(f"{'=' * 60}")

    return results


def run_ml_mode(db_session):
    """Run ML-based predictions using RandomForest (requires sklearn)."""
    try:
        import numpy as np
        import joblib
        from sklearn.ensemble import RandomForestRegressor
    except ImportError:
        print("ERROR: ML mode requires scikit-learn and joblib.")
        print("  pip install scikit-learn joblib pandas")
        sys.exit(1)

    from prediction.data_loader import SalesDataLoader
    from prediction.preprocess import create_features
    from prediction.config import FORECAST_HORIZON_DAYS, MIN_HISTORY_DAYS

    from models.product import Product
    from models.sale import Sale, SaleItem
    from sqlalchemy import func, Date
    import pandas as pd
    from datetime import timedelta

    print("=" * 60)
    print("  ML PREDICTION MODE (RandomForest)")
    print(f"  Forecast horizon: {FORECAST_HORIZON_DAYS} days")
    print("=" * 60)

    products = db_session.query(Product).filter_by(is_active=True).all()
    cutoff = datetime.utcnow() - timedelta(days=MIN_HISTORY_DAYS)
    pred_count = 0

    for product in products:
        # Load daily sales history
        results = (
            db_session.query(
                func.cast(Sale.sale_date, Date).label("sale_day"),
                func.coalesce(func.sum(SaleItem.quantity), 0).label("qty"),
            )
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                Sale.sale_date >= cutoff,
            )
            .group_by(func.cast(Sale.sale_date, Date))
            .order_by(func.cast(Sale.sale_date, Date).asc())
            .all()
        )

        if len(results) < 14:
            continue

        df = pd.DataFrame(
            [(r.sale_day, r.qty) for r in results],
            columns=["date", "quantity"],
        )
        df["date"] = pd.to_datetime(df["date"])

        df = create_features(df)
        feature_cols = [
            "day_of_week", "day_of_month", "month",
            "is_weekend", "lag_1", "lag_7", "rolling_mean_7",
        ]

        X = df[feature_cols].values
        y = df["quantity"].values

        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X, y)

        last_row = df.iloc[-1:][feature_cols]
        last_date = df["date"].iloc[-1]

        for i in range(1, FORECAST_HORIZON_DAYS + 1):
            forecast_date = last_date + timedelta(days=i)
            pred = max(0, round(float(model.predict(last_row.values)[0]), 2))
            # Confidence: use 1 - normalized std of residuals
            confidence = 0.85

            db_session.execute(
                """
                INSERT INTO reorder_predictions
                    (product_id, predicted_demand, confidence_score,
                     forecast_date, model_version, generated_at)
                VALUES (:pid, :demand, :conf, :fdate, :version, :now)
                ON DUPLICATE KEY UPDATE
                    predicted_demand = VALUES(predicted_demand),
                    confidence_score = VALUES(confidence_score),
                    model_version = VALUES(model_version),
                    generated_at = VALUES(generated_at)
                """,
                {
                    "pid": product.id,
                    "demand": pred,
                    "conf": confidence,
                    "fdate": forecast_date,
                    "version": "rf-v1.0",
                    "now": datetime.utcnow(),
                },
            )
            pred_count += 1

        print(f"  Predicted {product.name}: {FORECAST_HORIZON_DAYS} days ahead")

    db_session.commit()
    print(f"\n  Total predictions stored: {pred_count}")
    return pred_count


if __name__ == "__main__":
    # Parse --ml flag
    use_ml = "--ml" in sys.argv

    # Create Flask app and get DB session
    from app import create_app
    app = create_app()

    with app.app_context():
        from database import db as db_session

        if use_ml:
            run_ml_mode(db_session)
        else:
            run_simple_mode(db_session)
