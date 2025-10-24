"""CLI helper to generate SmartStocks forecasts without email delivery."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from report_generation import ForecastConfig, generate_forecast, write_forecast_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a SmartStocks forecast and save it as CSV.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol to analyse.")
    parser.add_argument("--period", default="6mo", help="Historical period to download (yfinance format).")
    parser.add_argument("--interval", default="1d", help="Historical data interval (yfinance format).")
    parser.add_argument("--simulations", type=int, default=500, help="Number of Monte Carlo trials to run.")
    parser.add_argument("--sim-time", type=int, default=30, help="Number of future days to simulate.")
    parser.add_argument("--processes", type=int, default=os.cpu_count() or 1, help="Desired number of CPU processes for the C++ backend.")
    parser.add_argument("--jump-parameter", type=float, default=1.0, help="Standard deviation multiplier that defines price jumps.")
    parser.add_argument("--h-s-window", type=int, default=20, help="Head-and-shoulders detection window.")
    parser.add_argument("--incremental-steps", type=int, default=5, help="Intervals over which price adjustments are applied.")
    parser.add_argument("--use-log-returns", action="store_true", help="Use log returns when estimating drift and volatility.")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Directory to store generated report files.")
    parser.add_argument("--output-file", type=Path, help="Explicit CSV output path. Overrides --output-dir.")
    parser.add_argument("--seed", type=int, help="Seed used for the Monte Carlo generator.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    return parser.parse_args()


def _determine_output_path(args: argparse.Namespace) -> Path:
    if args.output_file is not None:
        return args.output_file
    return args.output_dir / f"{args.ticker}_forecast.csv"


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    forecast_config = ForecastConfig(ticker=args.ticker,
                                     period=args.period,
                                     interval=args.interval,
                                     simulations=args.simulations,
                                     sim_time=args.sim_time,
                                     processes=args.processes,
                                     jump_parameter=args.jump_parameter,
                                     h_s_window=args.h_s_window,
                                     incremental_steps=args.incremental_steps,
                                     use_log_returns=args.use_log_returns,
                                     seed=getattr(args, "seed", None))

    result = generate_forecast(forecast_config)

    output_path = _determine_output_path(args)
    write_forecast_csv(result, output_path)

    logging.getLogger(__name__).info("%s", result.summary.strip())


if __name__ == "__main__":
    main()
