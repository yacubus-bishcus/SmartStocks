"""Price interval forecasts built from cumulative simulated log returns."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
DEFAULT_CONFIDENCE_HORIZONS = (5,)
EPSILON = 1e-12
ANALOG_FEATURE_COLUMNS = ("volatility_percentile", "trend_20d", "drawdown_60d")
ANALOG_DISTANCE_WEIGHTS = {
    "volatility_percentile": 0.50,
    "trend_20d": 0.30,
    "drawdown_60d": 0.20,
}
ANALOG_DISTANCE_THRESHOLDS = (0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, np.inf)


@dataclass
class PriceIntervalResult:
    """Container for confidence interval and swing-risk outputs."""

    ticker: str
    current_price: float
    horizon_days: int
    confidence: float
    simulations: int
    interval_table: pd.DataFrame
    volatility_regime: str
    inflection_score: float
    annualized_volatility: float
    volatility_percentile: float
    recent_trend: str
    simulated_prices: Optional[pd.DataFrame] = None
    analog_interval_table: Optional[pd.DataFrame] = None
    analog_match_count: int = 0
    analog_quality: str = "not_requested"
    analog_state: dict = field(default_factory=dict)

    def _main_row(self) -> pd.Series:
        matches = self.interval_table[self.interval_table["HorizonDays"] == self.horizon_days]
        if matches.empty:
            return self.interval_table.iloc[-1]
        return matches.iloc[-1]

    @property
    def lower_bound(self) -> float:
        return float(self._main_row()["LowerBound"])

    @property
    def median_estimate(self) -> float:
        return float(self._main_row()["MedianEstimate"])

    @property
    def upper_bound(self) -> float:
        return float(self._main_row()["UpperBound"])

    @property
    def probability_up_5_percent(self) -> float:
        return float(self._main_row()["ProbabilityUp5Percent"])

    @property
    def probability_down_5_percent(self) -> float:
        return float(self._main_row()["ProbabilityDown5Percent"])

    @property
    def probability_up_10_percent(self) -> float:
        return float(self._main_row()["ProbabilityUp10Percent"])

    @property
    def probability_down_10_percent(self) -> float:
        return float(self._main_row()["ProbabilityDown10Percent"])

    @property
    def expected_move(self) -> float:
        return float(self._main_row()["ExpectedMovePercent"])

    def confidence_interval_for_horizon(self, horizon_days: int) -> tuple[float, float, float]:
        matches = self.interval_table[self.interval_table["HorizonDays"] == horizon_days]
        if matches.empty:
            raise ValueError(f"No interval was calculated for {horizon_days} days.")
        row = matches.iloc[-1]
        return (
            float(row["LowerBound"]),
            float(row["MedianEstimate"]),
            float(row["UpperBound"]),
        )

    def summary(self) -> str:
        five_day = self.interval_table[self.interval_table["HorizonDays"] == 5]
        main = self._main_row()
        confidence_label = f"{self.confidence * 100:.0f}%"

        lines = [
            f"Price interval summary for {self.ticker}",
            f"Current price: {self.current_price:.2f}",
        ]
        if not five_day.empty:
            row = five_day.iloc[-1]
            lines.append(
                f"{confidence_label} 5-day confidence interval: "
                f"{row['LowerBound']:.2f} - {row['UpperBound']:.2f}"
            )
        lines.extend([
            f"{confidence_label} {int(main['HorizonDays'])}-day confidence interval: "
            f"{main['LowerBound']:.2f} - {main['UpperBound']:.2f}",
            f"Probability of at least a 5% move: {main['ProbabilityAbs5Percent']:.2f}% "
            f"(up {main['ProbabilityUp5Percent']:.2f}%, down {main['ProbabilityDown5Percent']:.2f}%)",
            f"Probability of at least a 10% move: {main['ProbabilityAbs10Percent']:.2f}% "
            f"(up {main['ProbabilityUp10Percent']:.2f}%, down {main['ProbabilityDown10Percent']:.2f}%)",
            f"Expected absolute move: {main['ExpectedMovePercent']:.2f}%",
            f"Volatility regime: {self.volatility_regime} "
            f"({self.annualized_volatility:.2f}% annualized, "
            f"{self.volatility_percentile:.2f} percentile)",
            f"Inflection score: {self.inflection_score:.2f}%",
        ])

        if self.analog_quality != "not_requested":
            lines.append("")
            lines.append(f"Empirical analogs: {self.analog_quality} ({self.analog_match_count} matches)")
            if self.analog_interval_table is not None and not self.analog_interval_table.empty:
                analog_five_day = self.analog_interval_table[self.analog_interval_table["HorizonDays"] == 5]
                if not analog_five_day.empty:
                    row = analog_five_day.iloc[-1]
                    lines.append(
                        f"Analog 5-day interval: {row['LowerBound']:.2f} - {row['UpperBound']:.2f}"
                    )
                analog_main = self.analog_interval_table[self.analog_interval_table["HorizonDays"] == self.horizon_days]
                if analog_main.empty:
                    analog_main = self.analog_interval_table.tail(1)
                if not analog_main.empty:
                    row = analog_main.iloc[-1]
                    lines.append(
                        f"Analog {int(row['HorizonDays'])}-day interval: "
                        f"{row['LowerBound']:.2f} - {row['UpperBound']:.2f}"
                    )
        return "\n".join(lines)


def generate_price_interval(ticker: str,
                            horizon_days: int = 30,
                            confidence: float = 0.90,
                            period: str = "1y",
                            interval: str = "1d",
                            simulations: int = 10000,
                            seed: Optional[int] = None,
                            processes: Optional[int] = None,
                            confidence_horizons: Optional[Sequence[int]] = None,
                            include_simulation_paths: bool = False,
                            include_empirical_analog: bool = True,
                            analog_period: str = "5y",
                            analog_min_matches: int = 30) -> PriceIntervalResult:
    """Generate price intervals from simulated cumulative future log returns."""

    history = _download_history(ticker, period, interval)
    analog_history = None
    if include_empirical_analog:
        if analog_period == period:
            analog_history = history
        else:
            try:
                analog_history = _download_history(ticker, analog_period, interval)
            except Exception as exc:
                logger.warning("Unable to download analog history for %s; falling back to %s history: %s",
                               ticker,
                               period,
                               exc)
                analog_history = history
    return generate_price_interval_from_history(ticker=ticker,
                                                history=history,
                                                horizon_days=horizon_days,
                                                confidence=confidence,
                                                simulations=simulations,
                                                seed=seed,
                                                processes=processes,
                                                confidence_horizons=confidence_horizons,
                                                include_simulation_paths=include_simulation_paths,
                                                include_empirical_analog=include_empirical_analog,
                                                analog_history=analog_history,
                                                analog_min_matches=analog_min_matches)


def generate_price_interval_from_history(ticker: str,
                                         history: pd.DataFrame | pd.Series,
                                         horizon_days: int = 30,
                                         confidence: float = 0.90,
                                         simulations: int = 10000,
                                         seed: Optional[int] = None,
                                         processes: Optional[int] = None,
                                         confidence_horizons: Optional[Sequence[int]] = None,
                                         include_simulation_paths: bool = False,
                                         include_empirical_analog: bool = True,
                                         analog_history: Optional[pd.DataFrame | pd.Series] = None,
                                         analog_min_matches: int = 30) -> PriceIntervalResult:
    """Generate price intervals using already-downloaded historical prices."""

    _validate_inputs(horizon_days=horizon_days, confidence=confidence, simulations=simulations)

    close_prices = _extract_close_prices(history, ticker)
    log_returns = _calculate_log_returns(close_prices)
    if len(log_returns) < 2:
        raise ValueError(f"Not enough historical log returns to generate intervals for {ticker}.")

    horizons = _resolve_confidence_horizons(horizon_days, confidence_horizons)
    simulation_horizon = max(horizons)
    current_price = float(close_prices.iloc[-1])

    simulated_prices = _simulate_prices_with_monte_carlo_backend(log_returns=log_returns,
                                                                 current_price=current_price,
                                                                 horizon_days=simulation_horizon,
                                                                 simulations=simulations,
                                                                 seed=seed,
                                                                 processes=processes)
    cumulative_future_returns = np.log(simulated_prices / current_price)

    interval_table = _build_interval_table(simulated_prices=simulated_prices,
                                           current_price=current_price,
                                           horizons=horizons,
                                           confidence=confidence)
    volatility_regime, annualized_volatility, volatility_percentile = _classify_volatility_regime(log_returns)
    inflection_score, recent_trend = _calculate_inflection_score(log_returns=log_returns,
                                                                 cumulative_future_returns=cumulative_future_returns)
    analog_interval_table = None
    analog_match_count = 0
    analog_quality = "not_requested"
    analog_state = {}
    if include_empirical_analog:
        analog_source = analog_history if analog_history is not None else history
        analog_close_prices = _extract_close_prices(analog_source, ticker)
        analog_result = _generate_empirical_analog_table(close_prices=analog_close_prices,
                                                         current_price=current_price,
                                                         horizons=horizons,
                                                         confidence=confidence,
                                                         min_matches=analog_min_matches)
        analog_interval_table = analog_result["interval_table"]
        analog_match_count = analog_result["match_count"]
        analog_quality = analog_result["quality"]
        analog_state = analog_result["state"]

    simulated_price_frame = None
    if include_simulation_paths:
        simulated_price_frame = pd.DataFrame(
            simulated_prices,
            columns=[f"Day{day}" for day in range(1, simulation_horizon + 1)],
        )

    return PriceIntervalResult(ticker=ticker.upper(),
                               current_price=current_price,
                               horizon_days=horizon_days,
                               confidence=confidence,
                               simulations=simulations,
                               interval_table=interval_table,
                               volatility_regime=volatility_regime,
                               inflection_score=inflection_score,
                               annualized_volatility=annualized_volatility,
                               volatility_percentile=volatility_percentile,
                               recent_trend=recent_trend,
                               simulated_prices=simulated_price_frame,
                               analog_interval_table=analog_interval_table,
                               analog_match_count=analog_match_count,
                               analog_quality=analog_quality,
                               analog_state=analog_state)


def _download_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is required when generate_price_interval downloads history.") from exc

    history = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if history.empty:
        raise ValueError(f"No historical data returned for {ticker}.")
    return history


def _validate_inputs(horizon_days: int, confidence: float, simulations: int) -> None:
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1.")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1.")
    if simulations < 1:
        raise ValueError("simulations must be at least 1.")


def _extract_close_prices(history: pd.DataFrame | pd.Series, ticker: str) -> pd.Series:
    if isinstance(history, pd.Series):
        close_prices = history
    elif isinstance(history.columns, pd.MultiIndex):
        close_prices = _extract_close_from_multi_index(history, ticker)
    else:
        close_column = "Close" if "Close" in history.columns else "Adj Close"
        if close_column not in history.columns:
            raise ValueError("Historical data must contain a Close or Adj Close column.")
        close_prices = history[close_column]

    if isinstance(close_prices, pd.DataFrame):
        if ticker in close_prices.columns:
            close_prices = close_prices[ticker]
        else:
            close_prices = close_prices.iloc[:, 0]

    close_prices = pd.to_numeric(close_prices.squeeze(), errors="coerce").dropna()
    close_prices = close_prices[close_prices > 0]
    if close_prices.empty:
        raise ValueError("Historical close prices are empty after cleaning.")
    return close_prices.astype(float)


def _extract_close_from_multi_index(history: pd.DataFrame, ticker: str) -> pd.Series | pd.DataFrame:
    for column_name in ("Close", "Adj Close"):
        for level in range(history.columns.nlevels):
            level_values = history.columns.get_level_values(level)
            if column_name not in level_values:
                continue
            close_prices = history.xs(column_name, axis=1, level=level)
            if isinstance(close_prices, pd.DataFrame) and ticker in close_prices.columns:
                return close_prices[ticker]
            return close_prices
    raise ValueError("Historical data must contain a Close or Adj Close column.")


def _calculate_log_returns(close_prices: pd.Series) -> pd.Series:
    log_prices = np.log(close_prices)
    log_returns = log_prices.diff().replace([np.inf, -np.inf], np.nan).dropna()
    return log_returns.astype(float)


def _resolve_confidence_horizons(horizon_days: int,
                                 confidence_horizons: Optional[Sequence[int]]) -> tuple[int, ...]:
    requested_horizons = list(confidence_horizons or DEFAULT_CONFIDENCE_HORIZONS)
    requested_horizons.append(horizon_days)
    cleaned_horizons = sorted({int(day) for day in requested_horizons if int(day) >= 1})
    return tuple(cleaned_horizons)


def _estimate_log_return_parameters(log_returns: pd.Series) -> tuple[float, float]:
    returns = log_returns.to_numpy(dtype=float)
    long_run_mean = float(np.mean(returns))
    recent_window = returns[-min(60, len(returns)):]
    recent_mean = float(np.mean(recent_window))
    drift = (0.65 * long_run_mean) + (0.35 * recent_mean)

    historical_volatility = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0
    recent_volatility = _estimate_recent_volatility(log_returns)
    volatility = recent_volatility if recent_volatility > EPSILON else historical_volatility

    return drift, volatility


def _simulate_prices_with_monte_carlo_backend(log_returns: pd.Series,
                                              current_price: float,
                                              horizon_days: int,
                                              simulations: int,
                                              seed: Optional[int],
                                              processes: Optional[int]) -> np.ndarray:
    from MonteCarlo import MonteCarlo

    drift, volatility = _estimate_log_return_parameters(log_returns)
    monte = MonteCarlo(data=None,
                       num_simulations=simulations,
                       sim_time=horizon_days,
                       history_time=len(log_returns),
                       processes=processes or os.cpu_count() or 1,
                       use_log_returns=True)
    monte.seed = seed
    simulated_prices = monte.execute_log_return_interval_simulation(initial_price=current_price,
                                                                    drift=drift,
                                                                    volatility=volatility,
                                                                    horizon_days=horizon_days)
    if simulated_prices.shape != (simulations, horizon_days):
        raise ValueError("Monte Carlo backend returned an unexpected simulated price distribution shape.")
    return simulated_prices


def _estimate_recent_volatility(log_returns: pd.Series, span: int = 20) -> float:
    if len(log_returns) < 2:
        return 0.0
    ewm_volatility = log_returns.ewm(span=min(span, len(log_returns)), adjust=False).std(bias=False)
    recent_volatility = float(ewm_volatility.dropna().iloc[-1]) if not ewm_volatility.dropna().empty else 0.0
    if not np.isfinite(recent_volatility):
        return 0.0
    return recent_volatility


def _build_interval_row(terminal_prices: np.ndarray,
                        current_price: float,
                        horizon: int,
                        confidence: float) -> dict:
    lower_quantile = (1.0 - confidence) / 2.0
    upper_quantile = 1.0 - lower_quantile
    terminal_prices = np.asarray(terminal_prices, dtype=float)
    terminal_prices = terminal_prices[np.isfinite(terminal_prices)]
    terminal_returns = (terminal_prices / current_price) - 1.0
    expected_move_percent = float(np.mean(np.abs(terminal_returns)) * 100.0)

    return {
        "HorizonDays": int(horizon),
        "Confidence": confidence,
        "LowerBound": float(np.quantile(terminal_prices, lower_quantile)),
        "MedianEstimate": float(np.quantile(terminal_prices, 0.50)),
        "UpperBound": float(np.quantile(terminal_prices, upper_quantile)),
        "ExpectedPrice": float(np.mean(terminal_prices)),
        "ExpectedReturnPercent": float(np.mean(terminal_returns) * 100.0),
        "ExpectedMovePercent": expected_move_percent,
        "ExpectedMoveDollars": float(current_price * expected_move_percent / 100.0),
        "ProbabilityUp5Percent": float(np.mean(terminal_returns >= 0.05) * 100.0),
        "ProbabilityDown5Percent": float(np.mean(terminal_returns <= -0.05) * 100.0),
        "ProbabilityAbs5Percent": float(np.mean(np.abs(terminal_returns) >= 0.05) * 100.0),
        "ProbabilityUp10Percent": float(np.mean(terminal_returns >= 0.10) * 100.0),
        "ProbabilityDown10Percent": float(np.mean(terminal_returns <= -0.10) * 100.0),
        "ProbabilityAbs10Percent": float(np.mean(np.abs(terminal_returns) >= 0.10) * 100.0),
    }


def _build_interval_table(simulated_prices: np.ndarray,
                          current_price: float,
                          horizons: Iterable[int],
                          confidence: float) -> pd.DataFrame:
    rows = []

    for horizon in horizons:
        horizon_index = int(horizon) - 1
        terminal_prices = simulated_prices[:, horizon_index]
        rows.append(_build_interval_row(terminal_prices=terminal_prices,
                                        current_price=current_price,
                                        horizon=int(horizon),
                                        confidence=confidence))

    return pd.DataFrame(rows)


def _empty_analog_result(state: Optional[dict] = None,
                         quality: str = "insufficient",
                         match_count: int = 0) -> dict:
    columns = [
        "HorizonDays",
        "Confidence",
        "LowerBound",
        "MedianEstimate",
        "UpperBound",
        "ExpectedPrice",
        "ExpectedReturnPercent",
        "ExpectedMovePercent",
        "ExpectedMoveDollars",
        "ProbabilityUp5Percent",
        "ProbabilityDown5Percent",
        "ProbabilityAbs5Percent",
        "ProbabilityUp10Percent",
        "ProbabilityDown10Percent",
        "ProbabilityAbs10Percent",
        "MatchCount",
        "AverageDistance",
        "AnalogQuality",
    ]
    return {
        "interval_table": pd.DataFrame(columns=columns),
        "match_count": int(match_count),
        "quality": quality,
        "state": state or {},
    }


def _generate_empirical_analog_table(close_prices: pd.Series,
                                     current_price: float,
                                     horizons: Sequence[int],
                                     confidence: float,
                                     min_matches: int) -> dict:
    close_prices = close_prices.astype(float).dropna()
    close_prices = close_prices[close_prices > 0]
    max_horizon = max(horizons)
    min_matches = max(1, int(min_matches))

    if len(close_prices) <= max_horizon + 60:
        return _empty_analog_result()

    features = _build_analog_feature_frame(close_prices)
    if features.empty:
        return _empty_analog_result()

    current_feature = features.iloc[-1]
    state = _analog_state_from_feature(current_feature)
    candidate_features = _eligible_analog_candidates(features, close_prices, max_horizon)
    if candidate_features.empty:
        return _empty_analog_result(state=state)

    distances = _calculate_analog_distances(candidate_features, current_feature)
    selected = _select_analog_matches(distances, min_matches)
    if selected.empty:
        return _empty_analog_result(state=state)

    log_prices = np.log(close_prices)
    selected_positions = selected.index.to_numpy(dtype=int)
    rows = []
    average_distance = float(selected.mean())
    quality = _classify_analog_quality(match_count=len(selected),
                                       min_matches=min_matches,
                                       average_distance=average_distance)
    if quality == "insufficient":
        return _empty_analog_result(state=state, quality=quality, match_count=len(selected))

    for horizon in horizons:
        forward_returns = []
        for position in selected_positions:
            future_position = position + int(horizon)
            if future_position < len(log_prices):
                forward_returns.append(float(log_prices.iloc[future_position] - log_prices.iloc[position]))
        if not forward_returns:
            continue
        terminal_prices = current_price * np.exp(np.asarray(forward_returns, dtype=float))
        row = _build_interval_row(terminal_prices=terminal_prices,
                                  current_price=current_price,
                                  horizon=int(horizon),
                                  confidence=confidence)
        row["MatchCount"] = int(len(forward_returns))
        row["AverageDistance"] = average_distance
        row["AnalogQuality"] = quality
        rows.append(row)

    if not rows:
        return _empty_analog_result(state=state)

    return {
        "interval_table": pd.DataFrame(rows),
        "match_count": int(len(selected)),
        "quality": quality,
        "state": state,
    }


def _build_analog_feature_frame(close_prices: pd.Series) -> pd.DataFrame:
    log_prices = np.log(close_prices)
    log_returns = log_prices.diff()
    rolling_volatility = log_returns.rolling(window=20, min_periods=10).std()
    volatility_percentile = _expanding_percentile_rank(rolling_volatility)
    trend_20d = log_prices.diff(20) * 100.0
    drawdown_60d = ((close_prices / close_prices.rolling(window=60, min_periods=20).max()) - 1.0) * 100.0

    features = pd.DataFrame({
        "volatility_percentile": volatility_percentile,
        "trend_20d": trend_20d,
        "drawdown_60d": drawdown_60d,
    }, index=close_prices.index)
    features = features.replace([np.inf, -np.inf], np.nan)
    return features.dropna()


def _expanding_percentile_rank(values: pd.Series) -> pd.Series:
    ranks = []
    seen_values: list[float] = []
    for value in values:
        if not np.isfinite(value):
            ranks.append(np.nan)
            continue
        seen_values.append(float(value))
        seen_array = np.asarray(seen_values, dtype=float)
        less_than = np.mean(seen_array < value)
        tied = np.mean(np.isclose(seen_array, value))
        ranks.append(float((less_than + (0.5 * tied)) * 100.0))
    return pd.Series(ranks, index=values.index)


def _eligible_analog_candidates(features: pd.DataFrame,
                                close_prices: pd.Series,
                                max_horizon: int) -> pd.DataFrame:
    feature_positions = pd.Series(np.arange(len(close_prices)), index=close_prices.index)
    candidates = features.copy()
    candidates["Position"] = feature_positions.reindex(candidates.index)
    candidates = candidates.dropna(subset=["Position"])
    candidates["Position"] = candidates["Position"].astype(int)
    candidates = candidates[candidates["Position"] + max_horizon < len(close_prices)]
    candidates.set_index("Position", inplace=True)
    return candidates[list(ANALOG_FEATURE_COLUMNS)]


def _calculate_analog_distances(candidate_features: pd.DataFrame,
                                current_feature: pd.Series) -> pd.Series:
    distances = pd.Series(0.0, index=candidate_features.index, dtype=float)
    for column in ANALOG_FEATURE_COLUMNS:
        scale = _robust_scale(candidate_features[column])
        weighted_difference = np.abs(candidate_features[column] - current_feature[column]) / scale
        distances = distances + (ANALOG_DISTANCE_WEIGHTS[column] * weighted_difference)
    return distances.replace([np.inf, -np.inf], np.nan).dropna().sort_values()


def _robust_scale(values: pd.Series) -> float:
    clean_values = values.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
    if len(clean_values) == 0:
        return 1.0

    median = float(np.median(clean_values))
    mad = float(np.median(np.abs(clean_values - median)))
    if mad > EPSILON:
        return mad

    q75, q25 = np.percentile(clean_values, [75, 25])
    iqr_scale = float((q75 - q25) / 1.349) if q75 > q25 else 0.0
    if iqr_scale > EPSILON:
        return iqr_scale

    std = float(np.std(clean_values, ddof=1)) if len(clean_values) > 1 else 0.0
    return std if std > EPSILON else 1.0


def _select_analog_matches(distances: pd.Series, min_matches: int) -> pd.Series:
    if distances.empty:
        return distances

    selected = distances.iloc[0:0]
    for threshold in ANALOG_DISTANCE_THRESHOLDS:
        selected = distances[distances <= threshold]
        if len(selected) >= min_matches:
            return selected

    return selected if not selected.empty else distances.head(min_matches)


def _classify_analog_quality(match_count: int, min_matches: int, average_distance: float) -> str:
    if match_count < 5:
        return "insufficient"
    if match_count < min_matches:
        return "low"
    if average_distance <= 1.5:
        return "strong"
    if average_distance <= 3.0:
        return "moderate"
    return "low"


def _analog_state_from_feature(feature: pd.Series) -> dict:
    return {
        "volatility_percentile": float(feature["volatility_percentile"]),
        "trend_20d": float(feature["trend_20d"]),
        "drawdown_60d": float(feature["drawdown_60d"]),
    }


def _classify_volatility_regime(log_returns: pd.Series,
                                window: int = 20) -> tuple[str, float, float]:
    min_periods = min(2, len(log_returns))
    rolling_volatility = log_returns.rolling(window=window, min_periods=min_periods).std()
    rolling_volatility = rolling_volatility.replace([np.inf, -np.inf], np.nan).dropna()

    if rolling_volatility.empty:
        recent_volatility = float(log_returns.std(ddof=1))
        volatility_percentile = 50.0
    else:
        recent_volatility = float(rolling_volatility.iloc[-1])
        if recent_volatility <= EPSILON:
            volatility_percentile = 0.0
        else:
            rolling_values = rolling_volatility.to_numpy(dtype=float)
            less_than_recent = np.mean(rolling_values < recent_volatility)
            tied_with_recent = np.mean(np.isclose(rolling_values, recent_volatility))
            volatility_percentile = float((less_than_recent + (0.5 * tied_with_recent)) * 100.0)

    if not np.isfinite(recent_volatility):
        recent_volatility = 0.0

    annualized_volatility = float(recent_volatility * np.sqrt(TRADING_DAYS_PER_YEAR) * 100.0)
    if volatility_percentile < 25.0:
        regime = "calm"
    elif volatility_percentile < 60.0:
        regime = "normal"
    elif volatility_percentile < 85.0:
        regime = "elevated"
    else:
        regime = "extreme"

    return regime, annualized_volatility, volatility_percentile


def _calculate_inflection_score(log_returns: pd.Series,
                                cumulative_future_returns: np.ndarray,
                                lookback_days: int = 20,
                                inflection_days: int = 5) -> tuple[float, str]:
    recent_returns = log_returns.tail(min(lookback_days, len(log_returns)))
    recent_mean = float(recent_returns.mean())
    recent_volatility = float(recent_returns.std(ddof=1)) if len(recent_returns) > 1 else 0.0

    if not np.isfinite(recent_mean):
        recent_mean = 0.0
    if not np.isfinite(recent_volatility):
        recent_volatility = 0.0

    if abs(recent_mean) <= max(recent_volatility * 0.05, EPSILON):
        return 50.0, "flat"

    trend_direction = 1.0 if recent_mean > 0 else -1.0
    recent_trend = "up" if trend_direction > 0 else "down"
    horizon_index = min(inflection_days, cumulative_future_returns.shape[1]) - 1
    soon_cumulative_returns = cumulative_future_returns[:, horizon_index]
    inflection_score = float(np.mean((soon_cumulative_returns * trend_direction) < 0.0) * 100.0)
    return inflection_score, recent_trend
