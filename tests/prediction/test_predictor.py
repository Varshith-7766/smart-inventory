import pytest
import pandas as pd
from prediction.preprocess import create_features
from prediction.data_loader import SalesDataLoader


def test_create_features():
    dates = pd.date_range(start="2026-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "quantity": [1, 0, 3, 2, 5, 1, 0, 4, 2, 0, 3, 5, 1, 0, 2, 4, 6, 1, 0, 3, 2, 5, 1, 0, 4, 2, 3, 1, 5, 0]})
    result = create_features(df)
    assert "day_of_week" in result.columns
    assert "lag_7" in result.columns
    assert "rolling_mean_7" in result.columns
    assert len(result) == 30
