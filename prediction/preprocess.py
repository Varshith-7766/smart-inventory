import pandas as pd
import numpy as np


def create_features(df):
    if df.empty or len(df) < 7:
        return df

    df = df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    df["lag_1"] = df["quantity"].shift(1).fillna(0)
    df["lag_7"] = df["quantity"].shift(7).fillna(0)
    df["rolling_mean_7"] = df["quantity"].rolling(window=7).mean().bfill().fillna(0)
    df["rolling_std_7"] = df["quantity"].rolling(window=7).std().fillna(0)

    return df


def split_series(df, test_days=7):
    if len(df) <= test_days:
        return df, pd.DataFrame()
    train = df.iloc[:-test_days]
    test = df.iloc[-test_days:]
    return train, test
