"""Core backtesting engine — simulates trades and computes performance metrics."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd


@dataclass
class Trade:
    entry_date: str
    entry_price: float
    exit_date: str | None = None
    exit_price: float | None = None
    direction: str = "LONG"  # LONG or SHORT
    shares: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0

    def close(self, exit_date: str, exit_price: float) -> None:
        self.exit_date = exit_date
        self.exit_price = exit_price
        if self.direction == "LONG":
            self.pnl = (exit_price - self.entry_price) * self.shares
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl = (self.entry_price - exit_price) * self.shares
            self.pnl_pct = (self.entry_price - exit_price) / self.entry_price


@dataclass
class BacktestResult:
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    trades: List[Trade] = field(default_factory=list)
    ticker: str = ""
    strategy_name: str = ""
    initial_capital: float = 0.0

    # --- Metric properties ---

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve.iloc[-1]) if len(self.equity_curve) > 0 else 0.0

    @property
    def total_return_pct(self) -> float:
        if self.initial_capital == 0:
            return 0.0
        return (self.final_equity - self.initial_capital) / self.initial_capital * 100

    @property
    def sharpe_ratio(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        daily_returns = self.equity_curve.pct_change().dropna()
        if daily_returns.std() == 0:
            return 0.0
        return float(daily_returns.mean() / daily_returns.std() * math.sqrt(252))

    @property
    def max_drawdown_pct(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        cummax = self.equity_curve.cummax()
        drawdown = (self.equity_curve - cummax) / cummax
        return float(drawdown.min() * 100)

    @property
    def win_rate(self) -> float:
        closed = [t for t in self.trades if t.exit_date is not None]
        if not closed:
            return 0.0
        winners = sum(1 for t in closed if t.pnl > 0)
        return winners / len(closed) * 100

    @property
    def total_trades(self) -> int:
        return len([t for t in self.trades if t.exit_date is not None])

    def summary(self) -> dict:
        return {
            "strategy": self.strategy_name,
            "ticker": self.ticker,
            "initial_capital": round(self.initial_capital, 2),
            "final_equity": round(self.final_equity, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "win_rate_pct": round(self.win_rate, 2),
            "total_trades": self.total_trades,
        }

    def trade_log(self) -> pd.DataFrame:
        rows = []
        for t in self.trades:
            if t.exit_date is None:
                continue
            rows.append({
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "direction": t.direction,
                "entry_price": round(t.entry_price, 4),
                "exit_price": round(t.exit_price, 4),
                "shares": round(t.shares, 4),
                "pnl": round(t.pnl, 2),
                "pnl_pct": round(t.pnl_pct * 100, 2),
            })
        return pd.DataFrame(rows)


class Backtester:
    """Event-driven backtester that walks through data bar-by-bar."""

    def __init__(self, initial_capital: float = 100_000.0):
        self.initial_capital = initial_capital

    def run(self, df: pd.DataFrame, strategy, ticker: str = "") -> BacktestResult:
        """Run a strategy against the supplied DataFrame.

        `strategy` must implement:
            - name: str
            - prepare(df) -> df   — add indicators / columns needed
            - signal(row, prev_row) -> str  — return "BUY", "SELL", or "HOLD"
        """
        df = strategy.prepare(df.copy())
        df.dropna(inplace=True)

        cash = self.initial_capital
        position: Trade | None = None
        trades: list[Trade] = []
        equity = []

        rows = list(df.iterrows())
        for i, (date, row) in enumerate(rows):
            date_str = str(date.date()) if hasattr(date, "date") else str(date)
            price = float(row["Close"])

            if i == 0:
                equity.append(cash)
                continue

            prev_row = rows[i - 1][1]
            signal = strategy.signal(row, prev_row)

            if signal == "BUY" and position is None:
                shares = math.floor(cash / price)
                if shares > 0:
                    cost = shares * price
                    cash -= cost
                    position = Trade(
                        entry_date=date_str,
                        entry_price=price,
                        direction="LONG",
                        shares=shares,
                    )

            elif signal == "SELL" and position is not None:
                position.close(date_str, price)
                cash += position.shares * price
                trades.append(position)
                position = None

            # Mark-to-market equity
            mtm = cash + (position.shares * price if position else 0)
            equity.append(mtm)

        # Force-close open position on last bar
        if position is not None:
            last_date, last_row = rows[-1]
            last_price = float(last_row["Close"])
            date_str = str(last_date.date()) if hasattr(last_date, "date") else str(last_date)
            position.close(date_str, last_price)
            cash += position.shares * last_price
            trades.append(position)

        equity_series = pd.Series(equity, index=df.index[: len(equity)])

        result = BacktestResult(
            equity_curve=equity_series,
            trades=trades,
            ticker=ticker,
            strategy_name=strategy.name,
            initial_capital=self.initial_capital,
        )
        return result
