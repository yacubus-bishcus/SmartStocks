"""CLI helper to generate SmartStocks forecasts without email delivery.

USAGE: 

```python -m generate_forecast_csv --ticker --output-file OUTPUT```
```python -m generate_forecast_csv --ticker-file INPUT_PATH --output-file OUTPUT```
```python -m generate_forecast_csv -h``` for help 

"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import List

import pandas as pd

from report_generation import (ForecastConfig, generate_forecast,
                               write_forecast_workbook)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a SmartStocks forecast and save it as an Excel workbook.")
    ticker_group = parser.add_mutually_exclusive_group(required=True)
    ticker_group.add_argument("--ticker", help="Ticker symbol to analyse.")
    ticker_group.add_argument("--ticker-file", type=Path,
                              help="Path to a text file containing ticker symbols (one per line).")
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
    parser.add_argument("--output-file", type=Path, help="Explicit Excel output path. Overrides --output-dir.")
    parser.add_argument("--seed", type=int, help="Seed used for the Monte Carlo generator.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--log-file", type=Path,
                        help="Optional log file path. When provided, console output is also written to this file.")
    return parser.parse_args()


def _determine_output_path(args: argparse.Namespace, ticker: str | None = None, *, multiple: bool = False) -> Path:
    if args.output_file is not None:
        return args.output_file
    if multiple:
        return args.output_dir / "multi_ticker_forecast.xlsx"
    if ticker is None:
        raise ValueError("Ticker must be provided when generating a single forecast output path.")
    return args.output_dir / f"{ticker}_forecast.xlsx"


def _configure_logging(args: argparse.Namespace) -> None:
    log_level = logging.DEBUG if args.verbose else logging.INFO
    log_kwargs = {
        "level": log_level,
        "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        "handlers": [logging.StreamHandler()],
    }

    if args.log_file is not None:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_kwargs["handlers"].append(logging.FileHandler(args.log_file))

    logging.basicConfig(**log_kwargs)


def _load_tickers(args: argparse.Namespace) -> List[str]:
    if args.ticker is not None:
        return [args.ticker]

    if args.ticker_file is None:
        raise ValueError("Either --ticker or --ticker-file must be supplied.")

    try:
        raw_tickers = args.ticker_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read ticker file: {args.ticker_file}") from exc

    tickers = [line.strip() for line in raw_tickers.splitlines() if line.strip()]
    if not tickers:
        raise ValueError(f"No tickers found in {args.ticker_file}")
    return tickers


def _unique_sheet_name(base: str, existing: set[str]) -> str:
    name = base[:31] or "Sheet"
    candidate = name
    suffix = 1
    while candidate in existing:
        trimmed = name[: max(0, 31 - len(str(suffix)) - 1)] or "Sheet"
        candidate = f"{trimmed}_{suffix}"
        suffix += 1
    existing.add(candidate)
    return candidate


def _generate_forecast_for_ticker(args: argparse.Namespace, ticker: str) -> ForecastConfig:
    return ForecastConfig(ticker=ticker,
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


def main() -> None:
    args = parse_args()
    _configure_logging(args)

    tickers = _load_tickers(args)
    logger = logging.getLogger(__name__)

    if len(tickers) == 1:
        ticker = tickers[0]
        forecast_config = _generate_forecast_for_ticker(args, ticker)
        result = generate_forecast(forecast_config)

        output_path = _determine_output_path(args, ticker)
        write_forecast_workbook(result, output_path)
        logger.info("%s", result.summary.strip())
        return

    forecast_results = {}
    for ticker in tickers:
        forecast_config = _generate_forecast_for_ticker(args, ticker)
        result = generate_forecast(forecast_config)
        forecast_results[ticker] = result
        logger.info("%s", result.summary.strip())

    output_path = _determine_output_path(args, multiple=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    used_sheet_names: set[str] = set()
    summary_rows: list[dict[str, str]] = []
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for ticker, result in forecast_results.items():
            sheet_name = _unique_sheet_name(ticker, used_sheet_names)
            result.forecast.to_excel(writer, sheet_name=sheet_name, index=False)
            summary_rows.append({"Ticker": ticker, "Summary": result.summary.strip()})

        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summaries", index=False)

    logger.info("Saved multi-ticker forecast results to %s", output_path)


if __name__ == "__main__":
    main()
