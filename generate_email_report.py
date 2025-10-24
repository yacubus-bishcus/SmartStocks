"""Command line entry point to generate SmartStocks reports and email them."""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import yfinance as yf

from DateGenerator import DateGenerator
from Models import MACD
from MonteCarlo import MonteCarlo
from Simulation_Analysis import Simulation_Analysis
from email_reporter import SMTPSettings, send_email_report

logger = logging.getLogger(__name__)


PERIOD_TO_DAYS = {
    "1d": 1,
    "5d": 5,
    "1mo": 30,
    "3mo": 90,
    "6mo": 182,
    "1y": 365,
    "2y": 2 * 365,
    "5y": 5 * 365,
    "10y": 10 * 365,
    "ytd": 365,
    "max": 3650,
}

INTERVAL_TO_MINUTES = {
    "1m": 1,
    "2m": 2,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
    "90m": 90,
    "1h": 60,
    "1d": 24 * 60,
    "5d": 24 * 60 * 5,
    "1wk": 24 * 60 * 7,
    "1mo": 24 * 60 * 30,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SmartStocks Monte Carlo report and email it.")
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
    parser.add_argument("--recipient", action="append", required=True, help="Email recipient. Specify multiple times for more recipients.")
    parser.add_argument("--sender", required=True, help="Email address used as the sender.")
    parser.add_argument("--smtp-server", required=True, help="SMTP server hostname.")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP server port.")
    parser.add_argument("--smtp-username", help="SMTP username. Defaults to the sender address.")
    parser.add_argument("--smtp-password", help="SMTP password. Defaults to SMARTSTOCKS_SMTP_PASSWORD environment variable.")
    parser.add_argument("--disable-tls", action="store_true", help="Disable STARTTLS when connecting to SMTP.")
    parser.add_argument("--email-subject", default="SmartStocks Monte Carlo Report", help="Custom email subject.")
    parser.add_argument("--no-email", action="store_true", help="Generate report files without sending an email.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--seed", type=int, help="Seed used for the Monte Carlo generator.")
    return parser.parse_args()


def _resolve_interval_minutes(interval: str) -> int:
    try:
        return INTERVAL_TO_MINUTES[interval]
    except KeyError as exc:
        raise ValueError(f"Unsupported interval '{interval}'.") from exc


def _resolve_history_days(period: str) -> int:
    try:
        return PERIOD_TO_DAYS[period]
    except KeyError as exc:
        raise ValueError(f"Unsupported period '{period}'.") from exc


def _download_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    history = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if history.empty:
        raise ValueError(f"No historical data returned for {ticker}.")
    history.dropna(inplace=True)
    return history


def _prepare_monte_carlo(history: pd.DataFrame, args: argparse.Namespace) -> MonteCarlo:
    sim_analysis = Simulation_Analysis()
    apply_func = sim_analysis.stock_price_processing_close_open
    monte = MonteCarlo(data=history,
                       num_simulations=args.simulations,
                       sim_time=args.sim_time,
                       history_time=_resolve_history_days(args.period),
                       processes=args.processes,
                       jump_param=args.jump_parameter,
                       apply_function=apply_func)
    monte.calculate_initial_condition(['avg_prices', 'historical_returns'])
    monte.head_shoulders_window = args.h_s_window
    monte.seed = getattr(args, "seed", None)
    return monte


def _generate_future_dataframe(interval_means: np.ndarray,
                               interval_stds: np.ndarray,
                               args: argparse.Namespace) -> pd.DataFrame:
    date_args = SimpleNamespace(model_interval=args.interval, sim_time=args.sim_time)
    dates = DateGenerator(date_args).generate_dates_with_intervals()
    frame = pd.DataFrame({
        "Date": dates[:len(interval_means)],
        "ExpectedPrice": interval_means,
        "StdDev": interval_stds,
    })
    return frame


def _summarise_results(ticker: str, interval_means: np.ndarray, interval_stds: np.ndarray, simulations: int) -> str:
    final_mean = interval_means[-1]
    final_std = interval_stds[-1]
    lower_bound = final_mean - final_std
    upper_bound = final_mean + final_std
    return (
        f"SmartStocks Monte Carlo summary for {ticker}\n\n"
        f"Simulations run: {simulations}\n"
        f"Expected price after horizon: {final_mean:.2f}\n"
        f"One standard deviation range: {lower_bound:.2f} - {upper_bound:.2f}\n"
    )


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    history = _download_history(args.ticker, args.period, args.interval)

    sim_analysis = Simulation_Analysis()
    macd = MACD()
    avg_bull_adj, avg_bear_adj = macd.calculate_historical_adjustments(history['Close'])
    drift, volatility = sim_analysis.calculate_drift_and_volatility(history['Close'], args.use_log_returns)

    stds_6 = 6 * np.std(history['Close'])
    min_cap = history['Close'].iloc[-1] - stds_6
    max_cap = history['Close'].iloc[-1] + stds_6
    average_reduction = sim_analysis.calculate_average_reduction(prices=history['Close'], window_size=args.h_s_window)
    interval_minutes = _resolve_interval_minutes(args.interval)

    monte = _prepare_monte_carlo(history, args)

    interval_means, interval_stds = monte.execute_normal_simulation_with_mp(drift=drift,
                                                                            volatility=volatility,
                                                                            interval_minutes=interval_minutes,
                                                                            average_reduction=average_reduction,
                                                                            bull=avg_bull_adj,
                                                                            bear=avg_bear_adj,
                                                                            min_cap=min_cap,
                                                                            max_cap=max_cap,
                                                                            incremental_adjustment_steps=args.incremental_steps)

    future_df = _generate_future_dataframe(interval_means, interval_stds, args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / f"{args.ticker}_forecast.csv"
    future_df.to_csv(csv_path, index=False)
    logger.info("Saved forecast results to %s", csv_path)

    summary_body = _summarise_results(args.ticker, interval_means, interval_stds, args.simulations)

    if args.no_email:
        logger.info("Email sending skipped (--no-email provided).")
        return

    password = args.smtp_password or os.getenv("SMARTSTOCKS_SMTP_PASSWORD")
    smtp_settings = SMTPSettings(host=args.smtp_server,
                                 port=args.smtp_port,
                                 username=args.smtp_username or args.sender,
                                 password=password,
                                 use_tls=not args.disable_tls,
                                 sender=args.sender)

    if smtp_settings.use_tls and not password:
        logger.warning("No SMTP password supplied; attempting to send without authentication.")

    send_email_report(settings=smtp_settings,
                      subject=args.email_subject,
                      body=summary_body,
                      recipients=args.recipient,
                      attachments=[csv_path])


if __name__ == "__main__":
    main()
