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


def _build_charts(result) -> str:
    """Return Plotly JSON for the equity curve and trade markers."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=("Equity Curve", "Drawdown (%)"),
    )

    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=[str(d.date()) if hasattr(d, "date") else str(d) for d in result.equity_curve.index],
            y=result.equity_curve.values.tolist(),
            mode="lines",
            name="Equity",
            line=dict(color="#2196F3", width=2),
        ),
        row=1, col=1,
    )

    # Trade markers
    for t in result.trades:
        if t.exit_date is None:
            continue
        color = "#4CAF50" if t.pnl > 0 else "#F44336"
        fig.add_trace(
            go.Scatter(
                x=[t.entry_date, t.exit_date],
                y=[t.entry_price * t.shares, t.exit_price * t.shares],
                mode="markers",
                marker=dict(size=8, color=color, symbol=["triangle-up", "triangle-down"]),
                name=f"{'Win' if t.pnl > 0 else 'Loss'} ${t.pnl:+.0f}",
                showlegend=False,
                hoverinfo="text",
                text=[
                    f"BUY {t.entry_date}<br>${t.entry_price:.2f} x {t.shares:.0f}",
                    f"SELL {t.exit_date}<br>${t.exit_price:.2f}<br>PnL: ${t.pnl:+.2f}",
                ],
            ),
            row=1, col=1,
        )

    # Drawdown
    cummax = result.equity_curve.cummax()
    drawdown = (result.equity_curve - cummax) / cummax * 100
    fig.add_trace(
        go.Scatter(
            x=[str(d.date()) if hasattr(d, "date") else str(d) for d in drawdown.index],
            y=drawdown.values.tolist(),
            mode="lines",
            name="Drawdown",
            fill="tozeroy",
            line=dict(color="#F44336", width=1),
        ),
        row=2, col=1,
    )

    fig.update_layout(
        height=650,
        template="plotly_dark",
        paper_bgcolor="#1e1e2f",
        plot_bgcolor="#1e1e2f",
        font=dict(color="#ccc"),
        margin=dict(l=60, r=30, t=40, b=40),
        legend=dict(orientation="h", y=1.05),
    )
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="DD %", row=2, col=1)

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


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

        # Build strategy with user params
        strat_cls = STRATEGY_REGISTRY[strategy_key]
        strategy = strat_cls(**{k: float(v) if "." in str(v) else int(v) for k, v in params.items()})

        df = fetch_data(ticker, start, end)
        bt = Backtester(initial_capital=capital)
        result = bt.run(df, strategy, ticker=ticker)

        chart_json = _build_charts(result)
        trade_log = result.trade_log().to_dict(orient="records")

        return jsonify({
            "summary": result.summary(),
            "chart": json.loads(chart_json),
            "trades": trade_log,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def main():
    app.run(debug=True, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
