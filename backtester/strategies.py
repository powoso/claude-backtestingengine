"""Built-in trading strategies."""

from __future__ import annotations

from backtester.data import add_sma, add_ema, add_rsi, add_vwap

import pandas as pd


class SMACrossover:
    """Buy when fast SMA crosses above slow SMA; sell on cross below."""

    def __init__(self, fast: int = 20, slow: int = 50):
        self.fast = fast
        self.slow = slow
        self.name = f"SMA Crossover ({fast}/{slow})"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        add_sma(df, self.fast)
        add_sma(df, self.slow)
        return df

    def signal(self, row: pd.Series, prev_row: pd.Series) -> str:
        fast_col = f"SMA_{self.fast}"
        slow_col = f"SMA_{self.slow}"
        if prev_row[fast_col] <= prev_row[slow_col] and row[fast_col] > row[slow_col]:
            return "BUY"
        if prev_row[fast_col] >= prev_row[slow_col] and row[fast_col] < row[slow_col]:
            return "SELL"
        return "HOLD"


class EMACrossover:
    """Buy when fast EMA crosses above slow EMA; sell on cross below."""

    def __init__(self, fast: int = 12, slow: int = 26):
        self.fast = fast
        self.slow = slow
        self.name = f"EMA Crossover ({fast}/{slow})"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        add_ema(df, self.fast)
        add_ema(df, self.slow)
        return df

    def signal(self, row: pd.Series, prev_row: pd.Series) -> str:
        fast_col = f"EMA_{self.fast}"
        slow_col = f"EMA_{self.slow}"
        if prev_row[fast_col] <= prev_row[slow_col] and row[fast_col] > row[slow_col]:
            return "BUY"
        if prev_row[fast_col] >= prev_row[slow_col] and row[fast_col] < row[slow_col]:
            return "SELL"
        return "HOLD"


class RSIStrategy:
    """Buy when RSI crosses above oversold; sell when it crosses above overbought."""

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"RSI ({period}, {oversold}/{overbought})"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        add_rsi(df, self.period)
        return df

    def signal(self, row: pd.Series, prev_row: pd.Series) -> str:
        rsi_col = f"RSI_{self.period}"
        if prev_row[rsi_col] <= self.oversold and row[rsi_col] > self.oversold:
            return "BUY"
        if prev_row[rsi_col] < self.overbought and row[rsi_col] >= self.overbought:
            return "SELL"
        return "HOLD"


class VWAPDeviation:
    """Buy when price crosses below VWAP by threshold; sell when above by threshold."""

    def __init__(self, buy_dev: float = -0.02, sell_dev: float = 0.02):
        self.buy_dev = buy_dev
        self.sell_dev = sell_dev
        self.name = f"VWAP Deviation ({self.buy_dev}/{self.sell_dev})"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        add_vwap(df)
        df["VWAP_dev"] = (df["Close"] - df["VWAP"]) / df["VWAP"]
        return df

    def signal(self, row: pd.Series, prev_row: pd.Series) -> str:
        if prev_row["VWAP_dev"] >= self.buy_dev and row["VWAP_dev"] < self.buy_dev:
            return "BUY"
        if prev_row["VWAP_dev"] <= self.sell_dev and row["VWAP_dev"] > self.sell_dev:
            return "SELL"
        return "HOLD"


STRATEGY_REGISTRY: dict[str, type] = {
    "sma_crossover": SMACrossover,
    "ema_crossover": EMACrossover,
    "rsi": RSIStrategy,
    "vwap_deviation": VWAPDeviation,
}
