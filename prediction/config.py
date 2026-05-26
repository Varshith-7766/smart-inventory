import os

FORECAST_HORIZON_DAYS = int(os.getenv("FORECAST_HORIZON_DAYS", 30))
MIN_HISTORY_DAYS = int(os.getenv("MIN_HISTORY_DAYS", 60))
DEFAULT_CONFIDENCE = 0.85
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
