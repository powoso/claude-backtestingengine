#!/usr/bin/env python3
"""Entry point — run the backtesting web UI or a CLI backtest."""

import argparse
import sys

from backtester.data import fetch_data
from backtester.engine import Backtester
from backtester.strategies import STRATEGY_REGISTRY


def cli_backtest(args):
    """Run a backtest from the command line and print results."""
    if args.strategy not in STRATEGY_REGISTRY:
        print(f"Unknown strategy: {args.strategy}")
        print(f"Available: {', '.join(STRATEGY_REGISTRY.keys())}")
        sys.exit(1)

    strategy = STRATEGY_REGISTRY[args.strategy]()
    print(f"Fetching {args.ticker} data from {args.start} to {args.end} ...")
    df = fetch_data(args.ticker, args.start, args.end)
    print(f"  {len(df)} bars loaded.\n")

    bt = Backtester(initial_capital=args.capital)
    result = bt.run(df, strategy, ticker=args.ticker)

    print("=" * 50)
    print("  BACKTEST RESULTS")
    print("=" * 50)
    for k, v in result.summary().items():
        print(f"  {k:>20s}: {v}")
    print("=" * 50)

    if args.trades:
        print("\nTrade Log:")
        log = result.trade_log()
        if log.empty:
            print("  No trades executed.")
        else:
            print(log.to_string(index=False))


def web_ui(args):
    """Launch the Flask web application."""
    from backtester.app import app
    print(f"Starting backtesting web UI on http://0.0.0.0:{args.port}")
    app.run(debug=True, host="0.0.0.0", port=args.port)


def main():
    parser = argparse.ArgumentParser(description="Backtesting Engine")
    sub = parser.add_subparsers(dest="command")

    # --- CLI mode ---
    cli = sub.add_parser("run", help="Run a backtest from the command line")
    cli.add_argument("--ticker", default="AAPL", help="Stock ticker (default: AAPL)")
    cli.add_argument("--start", default="2020-01-01", help="Start date (YYYY-MM-DD)")
    cli.add_argument("--end", default="2024-01-01", help="End date (YYYY-MM-DD)")
    cli.add_argument("--strategy", default="sma_crossover",
                     choices=list(STRATEGY_REGISTRY.keys()),
                     help="Strategy to use")
    cli.add_argument("--capital", type=float, default=100000, help="Initial capital")
    cli.add_argument("--trades", action="store_true", help="Print trade log")

    # --- Web UI mode ---
    web = sub.add_parser("web", help="Launch the web UI")
    web.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")

    args = parser.parse_args()
    if args.command == "run":
        cli_backtest(args)
    elif args.command == "web":
        web_ui(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
