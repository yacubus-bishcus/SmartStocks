"""CLI helper to generate SmartStocks forecasts without email delivery.

USAGE: 

```python -m generate_forecast --ticker --output-file OUTPUT```
```python -m generate_forecast --ticker-file INPUT_PATH --output-file OUTPUT```
```python -m generate_forecast -h``` for help 

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
    parser.add_argument("--processes", type=int, default=1, help="Desired number of CPU processes for the C++ backend.")
    parser.add_argument("--jump-parameter", type=float, default=1.0, help="Standard deviation multiplier that defines price jumps.")
    parser.add_argument("--h-s-window", type=int, default=20, help="Head-and-shoulders detection window.")
    parser.add_argument("--incremental-steps", type=int, default=5, help="Intervals over which price adjustments are applied.")
    parser.add_argument("--use-log-returns", action="store_true", help="Use log returns when estimating drift and volatility.")
    parser.add_argument("--confidence", type=float, default=0.90, help="Confidence level for price interval bands.")
    parser.add_argument("--disable-empirical-analog", action="store_true", help="Disable historical analog interval analysis.")
    parser.add_argument("--analog-period", default="5y", help="Historical period to use for empirical analog matching.")
    parser.add_argument("--analog-min-matches", type=int, default=30, help="Minimum desired empirical analog matches.")
    parser.add_argument("--disable-inflection-analysis", action="store_true", help="Disable bullish/bearish inflection probability analysis.")
    parser.add_argument("--inflection-horizon", type=int, default=10, help="Future days used for inflection probability analysis.")
    parser.add_argument("--inflection-threshold", type=float, default=0.05, help="Percent move threshold for inflection classification, expressed as a decimal.")
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
                          confidence=args.confidence,
                          include_empirical_analog=not args.disable_empirical_analog,
                          analog_period=args.analog_period,
                          analog_min_matches=args.analog_min_matches,
                          include_inflection_analysis=not args.disable_inflection_analysis,
                          inflection_horizon_days=args.inflection_horizon,
                          inflection_move_threshold=args.inflection_threshold,
                          seed=getattr(args, "seed", None))


def main() -> None:
    args = parse_args()
    _configure_logging(args)

    tickers = _load_tickers(args)
    logger = logging.getLogger(__name__)
    
    if args.processes > os.cpu_count():
        logger.warning(f"Processes requested exceeds CPU Count...defaulting to max CPU count: %s", os.cpu_count())
        args.processes = os.cpu_count()

    if args.log_file:
        # Print inputs for later reference 
        logger.info(f"Period: %s", args.period)
        logger.info(f"Interval: %s", args.interval)
        logger.info(f"Simulations: %s", args.simulations)
        logger.info(f"Sim Time: %s", args.sim_time)
        logger.info(f"Processes: %s", args.processes)
        logger.info(f"Jump Parameter: %s", args.jump_parameter)
        logger.info(f"Head and Shoulders Window: %s", args.h_s_window)
        logger.info(f"Increment Steps: %s", args.incremental_steps)
        logger.info(f"Using Log Returns: %s", args.use_log_returns)
        logger.info(f"Confidence: %s", args.confidence)
        logger.info(f"Empirical Analog Enabled: %s", not args.disable_empirical_analog)
        logger.info(f"Analog Period: %s", args.analog_period)
        logger.info(f"Analog Min Matches: %s", args.analog_min_matches)
        logger.info(f"Inflection Analysis Enabled: %s", not args.disable_inflection_analysis)
        logger.info(f"Inflection Horizon: %s", args.inflection_horizon)
        logger.info(f"Inflection Threshold: %s", args.inflection_threshold)
        if args.seed is not None:
            logger.info(f"Seed: %s", args.seed)

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
    interval_frames: list[pd.DataFrame] = []
    analog_frames: list[pd.DataFrame] = []
    inflection_frames: list[pd.DataFrame] = []
    inflection_signal_frames: list[pd.DataFrame] = []
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for ticker, result in forecast_results.items():
            sheet_name = _unique_sheet_name(ticker, used_sheet_names)
            result.forecast.to_excel(writer, sheet_name=sheet_name, index=False)
            if result.price_interval is not None:
                interval_frame = result.price_interval.interval_table.copy()
                interval_frame.insert(0, "Ticker", ticker)
                interval_frames.append(interval_frame)
                if (result.price_interval.analog_interval_table is not None and
                        not result.price_interval.analog_interval_table.empty):
                    analog_frame = result.price_interval.analog_interval_table.copy()
                    analog_frame.insert(0, "Ticker", ticker)
                    analog_frames.append(analog_frame)
            if result.inflection_result is not None:
                inflection_frame = result.inflection_result.inflection_table.copy()
                inflection_frames.append(inflection_frame)
                if not result.inflection_result.feature_table.empty:
                    signal_frame = result.inflection_result.feature_table.copy()
                    signal_frame.insert(0, "Ticker", ticker)
                    inflection_signal_frames.append(signal_frame)
            summary_rows.append({"Ticker": ticker, "Summary": result.summary.strip()})

        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summaries", index=False)
        if interval_frames:
            pd.concat(interval_frames, ignore_index=True).to_excel(writer, sheet_name="PriceIntervals", index=False)
        if analog_frames:
            pd.concat(analog_frames, ignore_index=True).to_excel(writer, sheet_name="EmpiricalAnalogs", index=False)
        if inflection_frames:
            pd.concat(inflection_frames, ignore_index=True).to_excel(writer, sheet_name="InflectionRisk", index=False)
        if inflection_signal_frames:
            pd.concat(inflection_signal_frames, ignore_index=True).to_excel(writer, sheet_name="InflectionSignals", index=False)

    logger.info("Saved multi-ticker forecast results to %s", output_path)


if __name__ == "__main__":
    main()
