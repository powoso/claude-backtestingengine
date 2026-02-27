# Backtesting Engine

A Python-based backtesting framework for evaluating trading strategies against historical market data. Define strategies using simple rules — moving average crossovers, RSI thresholds, VWAP deviations — and visualize results through an interactive web dashboard.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **4 built-in strategies** — SMA Crossover, EMA Crossover, RSI Thresholds, VWAP Deviation
- **Yahoo Finance integration** — fetch real historical OHLCV data for any ticker
- **Offline fallback** — synthetic data generation when network is unavailable
- **Performance metrics** — Sharpe ratio, max drawdown, win rate, total return, equity curves
- **Full trade logs** — entry/exit dates, prices, PnL per trade
- **Interactive web UI** — dark-themed dashboard with Plotly candlestick charts, equity curves, drawdown plots
- **CLI mode** — run backtests from the terminal without a browser

---

## Screenshots

### Web Dashboard
After running a backtest, the dashboard shows:
- **Metric cards** — total return, Sharpe ratio, max drawdown, win rate
- **Candlestick chart** — price action with buy/sell markers
- **Equity curve** — portfolio value over time with drawdown subplot
- **Trade log table** — every trade with PnL and win/loss badges
- **Summary tab** — all metrics in a clean, scannable layout

---

## Installation on macOS

### Prerequisites

- **macOS** 12 (Monterey) or later
- **Python 3.10+** (3.11 or 3.12 recommended)
- **pip** (comes with Python)
- **Git**

### Step 1: Install Python (if needed)

**Option A — Homebrew (recommended):**

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.12
```

**Option B — Official installer:**

Download from [python.org/downloads](https://www.python.org/downloads/) and run the `.pkg` installer.

Verify your installation:

```bash
python3 --version   # Should show 3.10 or higher
pip3 --version
```

### Step 2: Clone the repository

```bash
git clone https://github.com/powoso/claude-backtestingengine.git
cd claude-backtestingengine
```

### Step 3: Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

That's it — you're ready to go.

---

## Usage

### Web UI (recommended)

Launch the interactive dashboard:

```bash
python run.py web
```

Then open **http://localhost:5000** in your browser.

From the dashboard you can:
1. Enter a ticker symbol (e.g. `AAPL`, `MSFT`, `TSLA`)
2. Set a date range
3. Choose a strategy and tune its parameters
4. Click **Run Backtest** to see results

### CLI Mode

Run a backtest directly from the terminal:

```bash
# Basic run
python run.py run --ticker AAPL --start 2020-01-01 --end 2024-01-01

# With a specific strategy and trade log output
python run.py run --ticker TSLA --strategy rsi --trades

# EMA crossover with custom capital
python run.py run --ticker MSFT --strategy ema_crossover --capital 50000 --trades
```

**CLI options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--ticker` | `AAPL` | Stock ticker symbol |
| `--start` | `2020-01-01` | Backtest start date |
| `--end` | `2024-01-01` | Backtest end date |
| `--strategy` | `sma_crossover` | Strategy to use (see below) |
| `--capital` | `100000` | Initial portfolio capital |
| `--trades` | off | Print the full trade log |

---

## Strategies

| Key | Name | Signal Logic |
|-----|------|-------------|
| `sma_crossover` | SMA Crossover | Buy when fast SMA crosses above slow SMA; sell on cross below |
| `ema_crossover` | EMA Crossover | Buy when fast EMA crosses above slow EMA; sell on cross below |
| `rsi` | RSI Thresholds | Buy when RSI crosses up through oversold level; sell when it hits overbought |
| `vwap_deviation` | VWAP Deviation | Buy when price drops below VWAP by threshold; sell when it rises above |

Each strategy's parameters are configurable both in the web UI and via code.

---

## Output Metrics

| Metric | Description |
|--------|-------------|
| **Total Return %** | Percentage gain/loss over the backtest period |
| **Final Equity** | Portfolio value at the end of the backtest |
| **Sharpe Ratio** | Risk-adjusted return (annualized, 252 trading days) |
| **Max Drawdown %** | Largest peak-to-trough decline |
| **Win Rate %** | Percentage of trades that were profitable |
| **Total Trades** | Number of completed round-trip trades |

---

## Project Structure

```
claude-backtestingengine/
├── run.py                    # Entry point (CLI + web launcher)
├── requirements.txt          # Python dependencies
├── README.md
├── backtester/
│   ├── __init__.py
│   ├── data.py               # Yahoo Finance fetcher + technical indicators
│   ├── engine.py             # Backtester core, Trade & BacktestResult classes
│   ├── strategies.py         # Built-in strategy implementations
│   ├── sample_data.py        # Synthetic OHLCV data generator (offline fallback)
│   └── app.py                # Flask web application + Plotly chart builder
├── templates/
│   └── index.html            # Web dashboard (single-page app)
└── static/                   # Static assets directory
```

---

## Adding Custom Strategies

Create a class with three things: a `name`, a `prepare()` method, and a `signal()` method.

```python
from backtester.data import add_sma, add_rsi
import pandas as pd

class MyStrategy:
    name = "My Custom Strategy"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add any indicators your strategy needs."""
        add_sma(df, 50)
        add_rsi(df, 14)
        return df

    def signal(self, row: pd.Series, prev_row: pd.Series) -> str:
        """Return 'BUY', 'SELL', or 'HOLD' for each bar."""
        if row["RSI_14"] < 30 and row["Close"] > row["SMA_50"]:
            return "BUY"
        if row["RSI_14"] > 70:
            return "SELL"
        return "HOLD"
```

Then register it in `backtester/strategies.py`:

```python
STRATEGY_REGISTRY["my_strategy"] = MyStrategy
```

---

## Troubleshooting

**`No data returned` / network errors:**
The engine falls back to synthetic sample data when Yahoo Finance is unreachable. You'll still see results, but they won't reflect real market data. Check your internet connection and try again.

**Port 5000 already in use:**
```bash
python run.py web --port 8080
```

**`ModuleNotFoundError`:**
Make sure your virtual environment is activated:
```bash
source venv/bin/activate
```

---

## License

MIT
