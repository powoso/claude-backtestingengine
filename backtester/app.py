"""Flask web application for the backtesting engine."""

from __future__ import annotations

import json
import traceback

from flask import Flask, render_template, request, jsonify
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backtester.data import fetch_data
from backtester.engine import Backtester
from backtester.strategies import STRATEGY_REGISTRY

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
)

# ── Shared Plotly theme ──

_LAYOUT_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(17,24,39,0.5)",
    font=dict(family="Inter, system-ui, sans-serif", color="#94a3b8", size=12),
    margin=dict(l=56, r=24, t=36, b=40),
    legend=dict(
        orientation="h", y=1.06, x=0,
        font=dict(size=11),
        bgcolor="rgba(0,0,0,0)",
    ),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.04)",
        zerolinecolor="rgba(255,255,255,0.06)",
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.04)",
        zerolinecolor="rgba(255,255,255,0.06)",
    ),
    hoverlabel=dict(
        bgcolor="#1a1f35",
        bordercolor="rgba(255,255,255,0.1)",
        font=dict(family="JetBrains Mono, monospace", size=12, color="#f1f5f9"),
    ),
)


def _date_strs(index):
    return [str(d.date()) if hasattr(d, "date") else str(d) for d in index]


def _build_price_chart(df, result) -> dict:
    """Candlestick price chart with buy/sell markers."""
    dates = _date_strs(df.index)

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=dates,
        open=df["Open"].values.tolist(),
        high=df["High"].values.tolist(),
        low=df["Low"].values.tolist(),
        close=df["Close"].values.tolist(),
        increasing_line_color="#10b981",
        decreasing_line_color="#ef4444",
        increasing_fillcolor="#10b981",
        decreasing_fillcolor="#ef4444",
        name="Price",
        showlegend=False,
    ))

    # Buy markers
    buys = [(t.entry_date, t.entry_price) for t in result.trades if t.exit_date]
    if buys:
        fig.add_trace(go.Scatter(
            x=[b[0] for b in buys],
            y=[b[1] for b in buys],
            mode="markers",
            marker=dict(
                symbol="triangle-up", size=12,
                color="#10b981", line=dict(width=1, color="#065f46"),
            ),
            name="Buy",
            hovertemplate="BUY %{x}<br>$%{y:.2f}<extra></extra>",
        ))

    # Sell markers
    sells = [(t.exit_date, t.exit_price) for t in result.trades if t.exit_date]
    if sells:
        fig.add_trace(go.Scatter(
            x=[s[0] for s in sells],
            y=[s[1] for s in sells],
            mode="markers",
            marker=dict(
                symbol="triangle-down", size=12,
                color="#ef4444", line=dict(width=1, color="#7f1d1d"),
            ),
            name="Sell",
            hovertemplate="SELL %{x}<br>$%{y:.2f}<extra></extra>",
        ))

    fig.update_layout(
        **_LAYOUT_BASE,
        height=400,
        title=dict(
            text=f"{result.ticker} Price",
            font=dict(size=14, color="#f1f5f9"),
            x=0.01,
        ),
        xaxis_rangeslider_visible=False,
        yaxis_title="Price ($)",
    )

    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


def _build_equity_chart(result) -> dict:
    """Equity curve + drawdown subplot."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.72, 0.28],
    )

    dates = _date_strs(result.equity_curve.index)
    equity_vals = result.equity_curve.values.tolist()

    # Equity
    fig.add_trace(
        go.Scatter(
            x=dates, y=equity_vals,
            mode="lines",
            name="Equity",
            line=dict(color="#6366f1", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.07)",
            hovertemplate="$%{y:,.0f}<extra>Equity</extra>",
        ),
        row=1, col=1,
    )

    # Initial capital reference
    fig.add_hline(
        y=result.initial_capital, row=1, col=1,
        line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dot"),
        annotation_text=f"Initial: ${result.initial_capital:,.0f}",
        annotation_font_size=10,
        annotation_font_color="#64748b",
    )

    # Drawdown
    cummax = result.equity_curve.cummax()
    drawdown = (result.equity_curve - cummax) / cummax * 100
    fig.add_trace(
        go.Scatter(
            x=dates, y=drawdown.values.tolist(),
            mode="lines",
            name="Drawdown",
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.1)",
            line=dict(color="#ef4444", width=1.5),
            hovertemplate="%{y:.2f}%<extra>Drawdown</extra>",
        ),
        row=2, col=1,
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        height=440,
    )
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1,
                     gridcolor="rgba(255,255,255,0.04)")
    fig.update_yaxes(title_text="DD %", row=2, col=1,
                     gridcolor="rgba(255,255,255,0.04)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)", row=1, col=1)
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)", row=2, col=1)

    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


@app.route("/")
def index():
    strategies = {k: v().name for k, v in STRATEGY_REGISTRY.items()}
    return render_template("index.html", strategies=strategies)


@app.route("/run", methods=["POST"])
def run_backtest():
    try:
        data = request.get_json()
        ticker = data.get("ticker", "AAPL").upper().strip()
        start = data.get("start", "2020-01-01")
        end = data.get("end", "2024-01-01")
        strategy_key = data.get("strategy", "sma_crossover")
        capital = float(data.get("capital", 100000))
        params = data.get("params", {})

        if strategy_key not in STRATEGY_REGISTRY:
            return jsonify({"error": f"Unknown strategy: {strategy_key}"}), 400

        strat_cls = STRATEGY_REGISTRY[strategy_key]
        strategy = strat_cls(**{
            k: float(v) if "." in str(v) else int(v)
            for k, v in params.items()
        })

        df = fetch_data(ticker, start, end)
        bt = Backtester(initial_capital=capital)
        result = bt.run(df, strategy, ticker=ticker)

        price_chart = _build_price_chart(df, result)
        equity_chart = _build_equity_chart(result)
        trade_log = result.trade_log().to_dict(orient="records")

        return jsonify({
            "summary": result.summary(),
            "price_chart": price_chart,
            "equity_chart": equity_chart,
            "trades": trade_log,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def main():
    app.run(debug=True, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
