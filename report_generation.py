"""Shared helpers for building SmartStocks forecasts."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from DateGenerator import DateGenerator
from Models import MACD
from MonteCarlo import MonteCarlo
from Simulation_Analysis import Simulation_Analysis

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


@dataclass
class ForecastConfig:
    """Input parameters required to run a Monte Carlo forecast."""

    ticker: str
    period: str = "6mo"
    interval: str = "1d"
    simulations: int = 500
    sim_time: int = 30
    processes: Optional[int] = None
    jump_parameter: float = 1.0
    h_s_window: int = 20
    incremental_steps: int = 5
    use_log_returns: bool = False
    seed: Optional[int] = None


@dataclass
class ForecastResult:
    """Container for the Monte Carlo output."""

    interval_means: np.ndarray
    interval_stds: np.ndarray
    forecast: pd.DataFrame
    summary: str


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


def _prepare_monte_carlo(history: pd.DataFrame, config: ForecastConfig) -> MonteCarlo:
    processes = config.processes or os.cpu_count() or 1
    sim_analysis = Simulation_Analysis()
    monte = MonteCarlo(data=history,
                       num_simulations=config.simulations,
                       sim_time=config.sim_time,
                       history_time=_resolve_history_days(config.period),
                       processes=processes,
                       jump_param=config.jump_parameter,
                       apply_function=sim_analysis.stock_price_processing_close_open,
                       use_log_returns=config.use_log_returns)
    monte.calculate_initial_condition(['avg_prices', 'historical_returns'])
    monte.head_shoulders_window = config.h_s_window
    monte.seed = config.seed
    return monte


def _generate_future_dataframe(interval_means: np.ndarray,
                               interval_stds: np.ndarray,
                               interval: str,
                               sim_time: int) -> pd.DataFrame:
    date_args = SimpleNamespace(model_interval=interval, sim_time=sim_time)
    dates = DateGenerator(date_args).generate_dates_with_intervals()
    return pd.DataFrame({
        "Date": dates[:len(interval_means)],
        "ExpectedPrice": interval_means,
        "StdDev": interval_stds,
    })


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


def generate_forecast(config: ForecastConfig) -> ForecastResult:
    """Run the Monte Carlo workflow and return the computed forecast."""

    history = _download_history(config.ticker, config.period, config.interval)

    sim_analysis = Simulation_Analysis()
    macd = MACD()
    avg_bull_adj, avg_bear_adj = macd.calculate_historical_adjustments(history['Close'])
    stds_6 = 6 * np.std(history['Close'])
    min_cap = history['Close'].iloc[-1] - stds_6
    max_cap = history['Close'].iloc[-1] + stds_6
    average_reduction = sim_analysis.calculate_average_reduction(prices=history['Close'], window_size=config.h_s_window)
    interval_minutes = _resolve_interval_minutes(config.interval)

    monte = _prepare_monte_carlo(history, config)

    interval_means, interval_stds = monte.execute_normal_simulation_with_mp(interval_minutes=interval_minutes,
                                                                            average_reduction=average_reduction,
                                                                            bull=avg_bull_adj,
                                                                            bear=avg_bear_adj,
                                                                            min_cap=min_cap,
                                                                            max_cap=max_cap,
                                                                            incremental_adjustment_steps=config.incremental_steps)

    forecast = _generate_future_dataframe(interval_means, interval_stds, config.interval, config.sim_time)
    summary = _summarise_results(config.ticker, interval_means, interval_stds, config.simulations)

    return ForecastResult(interval_means=interval_means,
                          interval_stds=interval_stds,
                          forecast=forecast,
                          summary=summary)


def write_forecast_csv(result: ForecastResult, output_path: Path) -> Path:
    """Persist the forecast dataframe to ``output_path`` and return the path."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.forecast.to_csv(output_path, index=False)
    logger.info("Saved forecast results to %s", output_path)
    return output_path
