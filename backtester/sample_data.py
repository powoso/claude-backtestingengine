"""Generate synthetic OHLCV data for offline testing and demo purposes."""

import numpy as np
import pandas as pd


def generate_sample_data(
    ticker: str = "DEMO",
    days: int = 500,
    start_price: float = 150.0,
    volatility: float = 0.02,
    seed: int = 42,
) -> pd.DataFrame:
    """Create realistic-looking synthetic daily OHLCV data."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range(start="2021-01-04", periods=days)

    prices = [start_price]
    for _ in range(days - 1):
        ret = rng.normal(0.0003, volatility)
        prices.append(prices[-1] * (1 + ret))
    close = np.array(prices)

    # Build OHLCV from close
    high = close * (1 + rng.uniform(0, 0.015, days))
    low = close * (1 - rng.uniform(0, 0.015, days))
    opn = low + (high - low) * rng.uniform(0.2, 0.8, days)
    volume = rng.randint(5_000_000, 50_000_000, days).astype(float)

    df = pd.DataFrame({
        "Open": opn,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates)
    df.index.name = "Date"
    return df
