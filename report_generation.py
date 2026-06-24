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

from Inflection import InflectionResult, predict_inflection_points_from_history
from PriceInterval import PriceIntervalResult, generate_price_interval_from_history

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
    confidence: float = 0.90
    include_empirical_analog: bool = True
    analog_period: str = "5y"
    analog_min_matches: int = 30
    include_inflection_analysis: bool = True
    inflection_horizon_days: int = 10
    inflection_move_threshold: float = 0.05
    seed: Optional[int] = None


@dataclass
class ForecastResult:
    """Container for the Monte Carlo output."""

    interval_means: np.ndarray
    interval_stds: np.ndarray
    interval_std_errors: np.ndarray
    interval_p05: np.ndarray
    interval_p95: np.ndarray
    forecast: pd.DataFrame
    summary: str
    price_interval: Optional[PriceIntervalResult] = None
    inflection_result: Optional[InflectionResult] = None


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
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is required when generate_forecast downloads history.") from exc

    history = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if history.empty:
        raise ValueError(f"No historical data returned for {ticker}.")
    history.dropna(inplace=True)
    return history


def _prepare_monte_carlo(history: pd.DataFrame, config: ForecastConfig) -> MonteCarlo:
    from MonteCarlo import MonteCarlo
    from Simulation_Analysis import Simulation_Analysis

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
                               interval_std_errors: np.ndarray,
                               interval_p05: np.ndarray,
                               interval_p95: np.ndarray,
                               interval: str,
                               sim_time: int) -> pd.DataFrame:
    from DateGenerator import DateGenerator

    date_args = SimpleNamespace(model_interval=interval, sim_time=sim_time)
    dates = DateGenerator(date_args).generate_dates_with_intervals()
    return pd.DataFrame({
        "Date": dates[:len(interval_means)],
        "ExpectedPrice": interval_means,
        "StdDev": interval_stds,
        "StdError": interval_std_errors,
        "P05": interval_p05,
        "P95": interval_p95,
    })


def _summarise_results(ticker: str,
                       interval_means: np.ndarray,
                       interval_stds: np.ndarray,
                       interval_std_errors: np.ndarray,
                       interval_p05: np.ndarray,
                       interval_p95: np.ndarray,
                       simulations: int,
                       price_interval: Optional[PriceIntervalResult] = None,
                       inflection_result: Optional[InflectionResult] = None) -> str:
    final_mean = interval_means[-1]
    final_std = interval_stds[-1]
    final_std_error = interval_std_errors[-1]
    lower_bound = final_mean - final_std
    upper_bound = final_mean + final_std
    final_p05 = interval_p05[-1]
    final_p95 = interval_p95[-1]
    summary = (
        f"SmartStocks Monte Carlo summary for {ticker}\n\n"
        f"Simulations run: {simulations}\n"
        f"Expected price after horizon: {final_mean:.2f}\n"
        f"One standard deviation range: {lower_bound:.2f} - {upper_bound:.2f}\n"
        f"Standard error of the mean: {final_std_error:.2f}\n"
        f"5th-95th percentile range: {final_p05:.2f} - {final_p95:.2f}\n"
    )
    if price_interval is not None:
        summary = f"{summary}\n{price_interval.summary()}\n"
    if inflection_result is not None:
        summary = f"{summary}\n{inflection_result.summary()}\n"
    return summary


def generate_forecast(config: ForecastConfig) -> ForecastResult:
    """Run the Monte Carlo workflow and return the computed forecast."""

    history = _download_history(config.ticker, config.period, config.interval)
    analog_history = None
    if config.include_empirical_analog:
        if config.analog_period == config.period:
            analog_history = history
        else:
            try:
                analog_history = _download_history(config.ticker, config.analog_period, config.interval)
            except Exception as exc:
                logger.warning("Unable to download analog history for %s; falling back to %s history: %s",
                               config.ticker,
                               config.period,
                               exc)
                analog_history = history
    price_interval = generate_price_interval_from_history(ticker=config.ticker,
                                                          history=history,
                                                          horizon_days=config.sim_time,
                                                          confidence=config.confidence,
                                                          simulations=max(1, config.simulations),
                                                          seed=config.seed,
                                                          processes=config.processes,
                                                          include_empirical_analog=config.include_empirical_analog,
                                                          analog_history=analog_history,
                                                          analog_min_matches=config.analog_min_matches)
    inflection_result = None
    if config.include_inflection_analysis:
        try:
            inflection_result = predict_inflection_points_from_history(ticker=config.ticker,
                                                                       history=history,
                                                                       horizon_days=config.inflection_horizon_days,
                                                                       move_threshold=config.inflection_move_threshold,
                                                                       simulations=max(1, config.simulations),
                                                                       seed=config.seed,
                                                                       processes=config.processes)
        except Exception as exc:
            logger.warning("Unable to calculate inflection analysis for %s: %s", config.ticker, exc)
    logging.debug(history['Close'])
    from Models import MACD
    from Simulation_Analysis import Simulation_Analysis

    sim_analysis = Simulation_Analysis()
    macd = MACD()
    avg_bull_adj, avg_bear_adj = macd.calculate_historical_adjustments(history['Close'])
    close_prices = history['Close'].to_numpy(copy=False)
    stds_6 = 6 * np.std(close_prices)
    min_cap = history['Close'].iloc[-1] - stds_6
    logging.debug(f"MIN CAP: %s", min_cap)
    max_cap = history['Close'].iloc[-1] + stds_6
    logging.debug(f"MAX CAP: %s", max_cap)
    average_reduction = sim_analysis.calculate_average_reduction(prices=history['Close'], window_size=config.h_s_window)
    interval_minutes = _resolve_interval_minutes(config.interval)

    monte = _prepare_monte_carlo(history, config)

    interval_means, interval_stds, interval_p05, interval_p95 = monte.execute_normal_simulation_with_mp(interval_minutes=interval_minutes,
                                                                                                        average_reduction=average_reduction,
                                                                                                        bull=avg_bull_adj,
                                                                                                        bear=avg_bear_adj,
                                                                                                        min_cap=min_cap,
                                                                                                        max_cap=max_cap,
                                                                                                        incremental_adjustment_steps=config.incremental_steps)

    interval_std_errors = interval_stds / np.sqrt(float(config.simulations))

    forecast = _generate_future_dataframe(interval_means,
                                          interval_stds,
                                          interval_std_errors,
                                          interval_p05,
                                          interval_p95,
                                          config.interval,
                                          config.sim_time)
    summary = _summarise_results(config.ticker,
                                 interval_means,
                                 interval_stds,
                                 interval_std_errors,
                                 interval_p05,
                                 interval_p95,
                                 config.simulations,
                                 price_interval=price_interval,
                                 inflection_result=inflection_result)

    return ForecastResult(interval_means=interval_means,
                          interval_stds=interval_stds,
                          interval_std_errors=interval_std_errors,
                          interval_p05=interval_p05,
                          interval_p95=interval_p95,
                          forecast=forecast,
                          summary=summary,
                          price_interval=price_interval,
                          inflection_result=inflection_result)


def write_forecast_workbook(result: ForecastResult, output_path: Path) -> Path:
    """Persist the forecast and summary to an Excel workbook at ``output_path``."""

    if output_path.suffix.lower() != ".xlsx":
        logger.warning("Forecast output changed to Excel workbooks; overriding extension to .xlsx.")
        output_path = output_path.with_suffix(".xlsx")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_lines = [line for line in result.summary.strip().splitlines() if line]
    summary_frame = pd.DataFrame({"Summary": summary_lines or [result.summary.strip()]})

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        result.forecast.to_excel(writer, sheet_name="Forecast", index=False)
        if result.price_interval is not None:
            result.price_interval.interval_table.to_excel(writer, sheet_name="PriceIntervals", index=False)
            if (result.price_interval.analog_interval_table is not None and
                    not result.price_interval.analog_interval_table.empty):
                result.price_interval.analog_interval_table.to_excel(writer, sheet_name="EmpiricalAnalogs", index=False)
        if result.inflection_result is not None:
            result.inflection_result.inflection_table.to_excel(writer, sheet_name="InflectionRisk", index=False)
            if not result.inflection_result.feature_table.empty:
                result.inflection_result.feature_table.to_excel(writer, sheet_name="InflectionSignals", index=False)
        summary_frame.to_excel(writer, sheet_name="Summary", index=False)

    logger.info("Saved forecast workbook to %s", output_path)
    return output_path
