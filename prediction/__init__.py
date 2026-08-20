from prediction.predictor import (
    moving_average_demand,
    daily_consumption_rate,
    trend_analysis,
    predict_stockout_days,
    calculate_reorder_point,
    suggest_reorder_quantity,
    generate_restock_alerts,
    analyze_product,
    get_sales_history_from_db,
    run_for_product,
    run_for_all_products,
    demo,
)

__all__ = [
    "moving_average_demand",
    "daily_consumption_rate",
    "trend_analysis",
    "predict_stockout_days",
    "calculate_reorder_point",
    "suggest_reorder_quantity",
    "generate_restock_alerts",
    "analyze_product",
    "get_sales_history_from_db",
    "run_for_product",
    "run_for_all_products",
    "demo",
]