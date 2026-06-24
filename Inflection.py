"""Inflection probability forecasts from Monte Carlo paths and technical setup signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

EPSILON = 1e-12
DEFAULT_HORIZON_DAYS = 10
DEFAULT_MOVE_THRESHOLD = 0.05
DEFAULT_TECHNICAL_WEIGHT = 0.30

FEATURE_WEIGHTS = {
    "RSIDivergence": 1.20,
    "MACDHistogramSlopeChange": 1.00,
    "MovingAverageSlope": 0.80,
    "PriceTrendSecondDerivative": 0.90,
    "MovingAverageDistance": 0.80,
    "VolumeClimax": 0.80,
    "BollingerTouchReversal": 0.90,
    "SupportResistanceProximity": 0.80,
    "ReturnChangePoint": 1.00,
    "VolatilityChangePoint": 0.70,
}


@dataclass
class InflectionResult:
    """Container for bullish/bearish/no-inflection probabilities."""

    ticker: str
    current_price: float
    horizon_days: int
    move_threshold: float
    simulations: int
    probability_bullish_inflection: float
    probability_bearish_inflection: float
    probability_no_inflection: float
    monte_carlo_probabilities: dict = field(default_factory=dict)
    technical_probabilities: dict = field(default_factory=dict)
    feature_scores: dict = field(default_factory=dict)
    signal_strength: dict = field(default_factory=dict)
    inflection_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    simulated_prices: Optional[pd.DataFrame] = None

    def summary(self) -> str:
        lines = [
            f"Inflection forecast for {self.ticker}",
            f"Bullish inflection within {self.horizon_days} days: "
            f"{self.probability_bullish_inflection:.2f}%",
            f"Bearish inflection within {self.horizon_days} days: "
            f"{self.probability_bearish_inflection:.2f}%",
            f"No inflection within {self.horizon_days} days: {self.probability_no_inflection:.2f}%",
        ]

        if not self.feature_table.empty:
            ranked = self.feature_table.copy()
            ranked["MaxSignal"] = ranked[["BullishScore", "BearishScore"]].max(axis=1)
            ranked = ranked.sort_values("MaxSignal", ascending=False).head(3)
            if not ranked.empty:
                signals = [
                    f"{row.Feature} ({row.Direction})"
                    for row in ranked.itertuples(index=False)
                    if row.Direction != "neutral"
                ]
                if signals:
                    lines.append(f"Strongest technical signals: {', '.join(signals)}")

        return "\n".join(lines)


def predict_inflection_points(ticker: str,
                              horizon_days: int = DEFAULT_HORIZON_DAYS,
                              move_threshold: float = DEFAULT_MOVE_THRESHOLD,
                              period: str = "1y",
                              interval: str = "1d",
                              simulations: int = 5000,
                              seed: Optional[int] = None,
                              processes: Optional[int] = None,
                              technical_weight: float = DEFAULT_TECHNICAL_WEIGHT,
                              include_simulation_paths: bool = False) -> InflectionResult:
    """Predict bullish, bearish, and no-inflection probabilities for a ticker."""

    history = _download_history(ticker, period, interval)
    return predict_inflection_points_from_history(ticker=ticker,
                                                  history=history,
                                                  horizon_days=horizon_days,
                                                  move_threshold=move_threshold,
                                                  simulations=simulations,
                                                  seed=seed,
                                                  processes=processes,
                                                  technical_weight=technical_weight,
                                                  include_simulation_paths=include_simulation_paths)


def generate_inflection_forecast(*args, **kwargs) -> InflectionResult:
    """Alias for callers that prefer the forecast naming convention."""

    return predict_inflection_points(*args, **kwargs)


def predict_inflection_points_from_history(ticker: str,
                                           history: pd.DataFrame | pd.Series,
                                           horizon_days: int = DEFAULT_HORIZON_DAYS,
                                           move_threshold: float = DEFAULT_MOVE_THRESHOLD,
                                           simulations: int = 5000,
                                           seed: Optional[int] = None,
                                           processes: Optional[int] = None,
                                           technical_weight: float = DEFAULT_TECHNICAL_WEIGHT,
                                           include_simulation_paths: bool = False) -> InflectionResult:
    """Predict inflection probabilities from already-downloaded historical data."""

    _validate_inputs(horizon_days=horizon_days,
                     move_threshold=move_threshold,
                     simulations=simulations,
                     technical_weight=technical_weight)

    market_frame = _extract_market_frame(history, ticker)
    close_prices = market_frame["Close"]
    current_price = float(close_prices.iloc[-1])
    log_returns = _calculate_log_returns(close_prices)
    if len(log_returns) < 2:
        raise ValueError(f"Not enough historical log returns to predict inflections for {ticker}.")

    simulated_prices = _simulate_prices_with_monte_carlo_backend(log_returns=log_returns,
                                                                 current_price=current_price,
                                                                 horizon_days=horizon_days,
                                                                 simulations=simulations,
                                                                 seed=seed,
                                                                 processes=processes)
    monte_carlo_probabilities, monte_carlo_counts = _calculate_monte_carlo_inflection_probabilities(
        simulated_prices=simulated_prices,
        current_price=current_price,
        move_threshold=move_threshold,
    )

    technical_result = _calculate_technical_inflection_probabilities(market_frame)
    combined_probabilities = _blend_probabilities(monte_carlo_probabilities,
                                                  technical_result["probabilities"],
                                                  technical_weight=technical_weight)
    percent_probabilities = _as_percent_dict(combined_probabilities)
    mc_percent_probabilities = _as_percent_dict(monte_carlo_probabilities)
    technical_percent_probabilities = _as_percent_dict(technical_result["probabilities"])

    inflection_table = _build_inflection_table(ticker=ticker,
                                               current_price=current_price,
                                               horizon_days=horizon_days,
                                               move_threshold=move_threshold,
                                               simulations=simulations,
                                               combined=percent_probabilities,
                                               monte_carlo=mc_percent_probabilities,
                                               technical=technical_percent_probabilities,
                                               signal_strength=technical_result["signal_strength"],
                                               monte_carlo_counts=monte_carlo_counts)

    simulated_price_frame = None
    if include_simulation_paths:
        simulated_price_frame = pd.DataFrame(
            simulated_prices,
            columns=[f"Day{day}" for day in range(1, horizon_days + 1)],
        )

    return InflectionResult(ticker=ticker.upper(),
                            current_price=current_price,
                            horizon_days=horizon_days,
                            move_threshold=move_threshold,
                            simulations=simulations,
                            probability_bullish_inflection=percent_probabilities["bullish"],
                            probability_bearish_inflection=percent_probabilities["bearish"],
                            probability_no_inflection=percent_probabilities["no"],
                            monte_carlo_probabilities=mc_percent_probabilities,
                            technical_probabilities=technical_percent_probabilities,
                            feature_scores=technical_result["feature_scores"],
                            signal_strength=technical_result["signal_strength"],
                            inflection_table=inflection_table,
                            feature_table=technical_result["feature_table"],
                            simulated_prices=simulated_price_frame)


def _download_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is required when predict_inflection_points downloads history.") from exc

    history = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if history.empty:
        raise ValueError(f"No historical data returned for {ticker}.")
    return history


def _validate_inputs(horizon_days: int,
                     move_threshold: float,
                     simulations: int,
                     technical_weight: float) -> None:
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1.")
    if not 0.0 < move_threshold < 1.0:
        raise ValueError("move_threshold must be between 0 and 1.")
    if simulations < 1:
        raise ValueError("simulations must be at least 1.")
    if not 0.0 <= technical_weight <= 1.0:
        raise ValueError("technical_weight must be between 0 and 1.")


def _extract_market_frame(history: pd.DataFrame | pd.Series, ticker: str) -> pd.DataFrame:
    if isinstance(history, pd.Series):
        close = pd.to_numeric(history, errors="coerce")
        frame = pd.DataFrame({
            "Close": close,
            "High": close,
            "Low": close,
            "Volume": pd.Series(0.0, index=close.index),
        })
        return _clean_market_frame(frame)

    close = _extract_column(history, ticker, ("Close", "Adj Close"))
    high = _extract_column(history, ticker, ("High",), fallback=close)
    low = _extract_column(history, ticker, ("Low",), fallback=close)
    volume = _extract_column(history, ticker, ("Volume",), fallback=pd.Series(0.0, index=close.index))

    frame = pd.DataFrame({
        "Close": pd.to_numeric(close.squeeze(), errors="coerce"),
        "High": pd.to_numeric(high.squeeze(), errors="coerce"),
        "Low": pd.to_numeric(low.squeeze(), errors="coerce"),
        "Volume": pd.to_numeric(volume.squeeze(), errors="coerce"),
    })
    return _clean_market_frame(frame)


def _extract_column(history: pd.DataFrame,
                    ticker: str,
                    names: tuple[str, ...],
                    fallback: Optional[pd.Series] = None) -> pd.Series:
    if isinstance(history.columns, pd.MultiIndex):
        for name in names:
            for level in range(history.columns.nlevels):
                level_values = history.columns.get_level_values(level)
                if name not in level_values:
                    continue
                values = history.xs(name, axis=1, level=level)
                if isinstance(values, pd.DataFrame):
                    if ticker in values.columns:
                        return values[ticker]
                    return values.iloc[:, 0]
                return values
    else:
        for name in names:
            if name in history.columns:
                values = history[name]
                if isinstance(values, pd.DataFrame):
                    if ticker in values.columns:
                        return values[ticker]
                    return values.iloc[:, 0]
                return values

    if fallback is not None:
        return fallback
    joined = " or ".join(names)
    raise ValueError(f"Historical data must contain {joined}.")


def _clean_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame["Close"] = frame["Close"].astype(float)
    frame = frame.dropna(subset=["Close"])
    frame = frame[frame["Close"] > 0]
    frame["High"] = frame["High"].fillna(frame["Close"]).astype(float)
    frame["Low"] = frame["Low"].fillna(frame["Close"]).astype(float)
    frame["Volume"] = frame["Volume"].fillna(0.0).clip(lower=0.0).astype(float)
    frame["High"] = np.maximum(frame["High"], frame["Close"])
    frame["Low"] = np.minimum(frame["Low"], frame["Close"])
    if frame.empty:
        raise ValueError("Historical market data is empty after cleaning.")
    return frame


def _calculate_log_returns(close_prices: pd.Series) -> pd.Series:
    log_returns = np.log(close_prices.astype(float)).diff()
    return log_returns.replace([np.inf, -np.inf], np.nan).dropna().astype(float)


def _simulate_prices_with_monte_carlo_backend(log_returns: pd.Series,
                                              current_price: float,
                                              horizon_days: int,
                                              simulations: int,
                                              seed: Optional[int],
                                              processes: Optional[int]) -> np.ndarray:
    from PriceInterval import _simulate_prices_with_monte_carlo_backend as simulate

    return simulate(log_returns=log_returns,
                    current_price=current_price,
                    horizon_days=horizon_days,
                    simulations=simulations,
                    seed=seed,
                    processes=processes)


def _calculate_monte_carlo_inflection_probabilities(simulated_prices: np.ndarray,
                                                    current_price: float,
                                                    move_threshold: float) -> tuple[dict, dict]:
    counts = {"bullish": 0, "bearish": 0, "no": 0}

    for path in np.asarray(simulated_prices, dtype=float):
        path = path[np.isfinite(path)]
        if path.size == 0:
            counts["no"] += 1
            continue
        full_path = np.concatenate(([current_price], path))
        bullish_day = _first_bullish_inflection_day(full_path, move_threshold)
        bearish_day = _first_bearish_inflection_day(full_path, move_threshold)
        classification = _classify_path_inflection(full_path, bullish_day, bearish_day)
        counts[classification] += 1

    total = float(sum(counts.values()))
    if total <= EPSILON:
        return {"bullish": 0.0, "bearish": 0.0, "no": 1.0}, counts
    return {key: value / total for key, value in counts.items()}, counts


def _first_bullish_inflection_day(path: np.ndarray, move_threshold: float) -> Optional[int]:
    running_low = float(path[0])
    running_low_day = 0
    for day in range(1, len(path)):
        price = float(path[day])
        if not np.isfinite(price) or price <= 0:
            continue
        if price < running_low:
            running_low = price
            running_low_day = day
            continue
        if day > running_low_day and running_low > 0:
            if (price / running_low) - 1.0 >= move_threshold:
                return day
    return None


def _first_bearish_inflection_day(path: np.ndarray, move_threshold: float) -> Optional[int]:
    running_high = float(path[0])
    running_high_day = 0
    for day in range(1, len(path)):
        price = float(path[day])
        if not np.isfinite(price) or price <= 0:
            continue
        if price > running_high:
            running_high = price
            running_high_day = day
            continue
        if day > running_high_day and running_high > 0:
            if 1.0 - (price / running_high) >= move_threshold:
                return day
    return None


def _classify_path_inflection(path: np.ndarray,
                              bullish_day: Optional[int],
                              bearish_day: Optional[int]) -> str:
    if bullish_day is None and bearish_day is None:
        return "no"
    if bearish_day is None:
        return "bullish"
    if bullish_day is None:
        return "bearish"
    if bullish_day < bearish_day:
        return "bullish"
    if bearish_day < bullish_day:
        return "bearish"

    bullish_reference = np.min(path[:bullish_day + 1])
    bearish_reference = np.max(path[:bearish_day + 1])
    bullish_move = (path[bullish_day] / bullish_reference) - 1.0 if bullish_reference > 0 else 0.0
    bearish_move = 1.0 - (path[bearish_day] / bearish_reference) if bearish_reference > 0 else 0.0
    return "bullish" if bullish_move >= bearish_move else "bearish"


def _calculate_technical_inflection_probabilities(market_frame: pd.DataFrame) -> dict:
    close = market_frame["Close"].astype(float)
    feature_rows = [
        _rsi_divergence_score(close),
        _macd_histogram_slope_change_score(close),
        _moving_average_slope_score(close),
        _price_second_derivative_score(close),
        _moving_average_distance_score(close),
        _volume_climax_score(market_frame),
        _bollinger_touch_reversal_score(market_frame),
        _support_resistance_proximity_score(market_frame),
        _return_changepoint_score(close),
        _volatility_changepoint_score(close),
    ]

    feature_table = pd.DataFrame(feature_rows)
    weighted_bullish = 0.0
    weighted_bearish = 0.0
    total_weight = 0.0
    feature_scores = {}

    for row in feature_rows:
        weight = FEATURE_WEIGHTS.get(row["Feature"], 1.0)
        weighted_bullish += weight * float(row["BullishScore"])
        weighted_bearish += weight * float(row["BearishScore"])
        total_weight += weight
        feature_scores[row["Feature"]] = {
            "bullish": float(row["BullishScore"]),
            "bearish": float(row["BearishScore"]),
            "direction": row["Direction"],
            "diagnostic": row["Diagnostic"],
        }

    bullish_signal = weighted_bullish / total_weight if total_weight > EPSILON else 0.0
    bearish_signal = weighted_bearish / total_weight if total_weight > EPSILON else 0.0
    neutral_signal = max(0.05, 1.0 - max(bullish_signal, bearish_signal))
    probabilities = _softmax_probabilities({
        "bullish": 2.5 * bullish_signal,
        "bearish": 2.5 * bearish_signal,
        "no": 2.5 * neutral_signal,
    })

    return {
        "probabilities": probabilities,
        "feature_table": feature_table,
        "feature_scores": feature_scores,
        "signal_strength": {
            "bullish": float(bullish_signal),
            "bearish": float(bearish_signal),
            "neutral": float(neutral_signal),
        },
    }


def _rsi_divergence_score(close: pd.Series) -> dict:
    rsi = _calculate_rsi(close)
    if len(close) < 30 or rsi.dropna().empty:
        return _feature_row("RSIDivergence", 0.0, 0.0, "insufficient history")

    price_recent = close.iloc[-15:]
    price_previous = close.iloc[-30:-15]
    rsi_recent = rsi.reindex(price_recent.index).dropna()
    rsi_previous = rsi.reindex(price_previous.index).dropna()
    if price_previous.empty or price_recent.empty or rsi_recent.empty or rsi_previous.empty:
        return _feature_row("RSIDivergence", 0.0, 0.0, "insufficient RSI windows")

    recent_low = float(price_recent.min())
    previous_low = float(price_previous.min())
    recent_high = float(price_recent.max())
    previous_high = float(price_previous.max())
    recent_rsi_low = float(rsi_recent.min())
    previous_rsi_low = float(rsi_previous.min())
    recent_rsi_high = float(rsi_recent.max())
    previous_rsi_high = float(rsi_previous.max())
    last_rsi = float(rsi.dropna().iloc[-1])

    bullish_divergence = recent_low < previous_low * 0.995 and recent_rsi_low > previous_rsi_low + 2.0
    bearish_divergence = recent_high > previous_high * 1.005 and recent_rsi_high < previous_rsi_high - 2.0

    bullish = 1.0 if bullish_divergence else _positive_score(35.0 - last_rsi, 15.0) * 0.35
    bearish = 1.0 if bearish_divergence else _positive_score(last_rsi - 65.0, 15.0) * 0.35
    diagnostic = f"RSI={last_rsi:.2f}, bull_divergence={bullish_divergence}, bear_divergence={bearish_divergence}"
    return _feature_row("RSIDivergence", bullish, bearish, diagnostic)


def _calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0.0, 0.0)
    loss = -delta.where(delta < 0.0, 0.0)
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(~((avg_loss <= EPSILON) & (avg_gain > EPSILON)), 100.0)
    rsi = rsi.where(~((avg_gain <= EPSILON) & (avg_loss > EPSILON)), 0.0)
    rsi = rsi.where(~((avg_gain <= EPSILON) & (avg_loss <= EPSILON)), 50.0)
    return rsi.replace([np.inf, -np.inf], np.nan)


def _macd_histogram_slope_change_score(close: pd.Series) -> dict:
    _, _, histogram = _calculate_macd(close)
    if len(histogram.dropna()) < 10:
        return _feature_row("MACDHistogramSlopeChange", 0.0, 0.0, "insufficient MACD history")

    histogram = histogram.dropna()
    slopes = histogram.diff().dropna()
    recent_slope = float(slopes.tail(3).mean()) if len(slopes) >= 3 else 0.0
    previous_slope = float(slopes.iloc[-8:-3].mean()) if len(slopes) >= 8 else 0.0
    slope_scale = _safe_scale(histogram.tail(60))
    slope_change = (recent_slope - previous_slope) / slope_scale

    bullish = max(_positive_score(slope_change, 0.35),
                  0.75 if previous_slope <= 0.0 < recent_slope else 0.0)
    bearish = max(_negative_score(slope_change, 0.35),
                  0.75 if previous_slope >= 0.0 > recent_slope else 0.0)
    diagnostic = (
        f"hist={histogram.iloc[-1]:.4f}, recent_slope={recent_slope:.4f}, "
        f"previous_slope={previous_slope:.4f}"
    )
    return _feature_row("MACDHistogramSlopeChange", bullish, bearish, diagnostic)


def _calculate_macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    short_ema = close.ewm(span=12, min_periods=1, adjust=False).mean()
    long_ema = close.ewm(span=26, min_periods=1, adjust=False).mean()
    macd_line = short_ema - long_ema
    signal_line = macd_line.ewm(span=9, min_periods=1, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _moving_average_slope_score(close: pd.Series) -> dict:
    slopes = []
    for window in (20, 50, 200):
        ma = close.rolling(window=window, min_periods=min(window, max(5, window // 2))).mean()
        clean_ma = ma.dropna()
        if len(clean_ma) < 6:
            continue
        previous = float(clean_ma.iloc[-6])
        current = float(clean_ma.iloc[-1])
        if abs(previous) > EPSILON:
            slopes.append((current - previous) / abs(previous) / 5.0)

    if not slopes:
        return _feature_row("MovingAverageSlope", 0.0, 0.0, "insufficient moving-average history")

    average_slope = float(np.mean(slopes))
    bullish = _positive_score(average_slope, 0.002)
    bearish = _negative_score(average_slope, 0.002)
    return _feature_row("MovingAverageSlope", bullish, bearish, f"average_daily_slope={average_slope:.5f}")


def _price_second_derivative_score(close: pd.Series) -> dict:
    if len(close) < 12:
        return _feature_row("PriceTrendSecondDerivative", 0.0, 0.0, "insufficient trend history")

    trend = np.log(close).ewm(span=10, min_periods=3, adjust=False).mean()
    acceleration = trend.diff().diff().replace([np.inf, -np.inf], np.nan).dropna()
    if acceleration.empty:
        return _feature_row("PriceTrendSecondDerivative", 0.0, 0.0, "insufficient acceleration values")

    recent_acceleration = float(acceleration.tail(3).mean())
    return_volatility = _calculate_log_returns(close).tail(20).std(ddof=1)
    scale = max(float(return_volatility) / 5.0 if np.isfinite(return_volatility) else 0.0, 0.0005)
    bullish = _positive_score(recent_acceleration, scale)
    bearish = _negative_score(recent_acceleration, scale)
    return _feature_row("PriceTrendSecondDerivative",
                        bullish,
                        bearish,
                        f"recent_acceleration={recent_acceleration:.6f}")


def _moving_average_distance_score(close: pd.Series) -> dict:
    distances = []
    for window in (20, 50, 200):
        ma = close.rolling(window=window, min_periods=min(window, max(5, window // 2))).mean()
        clean_ma = ma.dropna()
        if clean_ma.empty:
            continue
        ma_value = float(clean_ma.iloc[-1])
        if ma_value > EPSILON:
            distances.append((float(close.iloc[-1]) / ma_value) - 1.0)

    if not distances:
        return _feature_row("MovingAverageDistance", 0.0, 0.0, "insufficient moving-average distance history")

    bullish = float(np.mean([_negative_score(distance, 0.08) for distance in distances]))
    bearish = float(np.mean([_positive_score(distance, 0.08) for distance in distances]))
    diagnostic = "distances=" + ",".join(f"{distance:.3f}" for distance in distances)
    return _feature_row("MovingAverageDistance", bullish, bearish, diagnostic)


def _volume_climax_score(market_frame: pd.DataFrame) -> dict:
    volume = market_frame["Volume"].astype(float)
    close = market_frame["Close"].astype(float)
    if len(volume) < 20 or volume.tail(20).median() <= EPSILON:
        return _feature_row("VolumeClimax", 0.0, 0.0, "insufficient volume history")

    baseline_volume = float(volume.rolling(window=20, min_periods=5).median().iloc[-1])
    volume_ratio = float(volume.iloc[-1] / baseline_volume) if baseline_volume > EPSILON else 0.0
    latest_return = float(close.pct_change().iloc[-1]) if len(close) > 1 else 0.0
    climax = _positive_score(volume_ratio - 1.5, 2.0)
    direction_strength = min(1.0, abs(latest_return) / 0.03) if np.isfinite(latest_return) else 0.0

    bullish = climax * direction_strength if latest_return < 0.0 else climax * 0.20
    bearish = climax * direction_strength if latest_return > 0.0 else climax * 0.20
    return _feature_row("VolumeClimax",
                        bullish,
                        bearish,
                        f"volume_ratio={volume_ratio:.2f}, latest_return={latest_return:.3f}")


def _bollinger_touch_reversal_score(market_frame: pd.DataFrame) -> dict:
    close = market_frame["Close"].astype(float)
    high = market_frame["High"].astype(float)
    low = market_frame["Low"].astype(float)
    if len(close) < 20:
        return _feature_row("BollingerTouchReversal", 0.0, 0.0, "insufficient Bollinger history")

    middle = close.rolling(window=20, min_periods=10).mean()
    band_std = close.rolling(window=20, min_periods=10).std()
    upper = middle + (2.0 * band_std)
    lower = middle - (2.0 * band_std)
    if not np.isfinite(upper.iloc[-1]) or not np.isfinite(lower.iloc[-1]):
        return _feature_row("BollingerTouchReversal", 0.0, 0.0, "invalid Bollinger bands")
    band_width = float((upper.iloc[-1] - lower.iloc[-1]) / close.iloc[-1])
    if band_width <= 0.002:
        return _feature_row("BollingerTouchReversal", 0.0, 0.0, "flat Bollinger bands")

    latest_return = float(close.pct_change().iloc[-1]) if len(close) > 1 else 0.0
    recent_low_touch = float(low.tail(3).min()) <= float(lower.tail(3).min())
    recent_high_touch = float(high.tail(3).max()) >= float(upper.tail(3).max())
    bullish = (0.85 if recent_low_touch and latest_return > 0.0 else
               0.45 if recent_low_touch else 0.0)
    bearish = (0.85 if recent_high_touch and latest_return < 0.0 else
               0.45 if recent_high_touch else 0.0)
    diagnostic = (
        f"lower_touch={recent_low_touch}, upper_touch={recent_high_touch}, "
        f"latest_return={latest_return:.3f}"
    )
    return _feature_row("BollingerTouchReversal", bullish, bearish, diagnostic)


def _support_resistance_proximity_score(market_frame: pd.DataFrame) -> dict:
    close = market_frame["Close"].astype(float)
    high = market_frame["High"].astype(float)
    low = market_frame["Low"].astype(float)
    if len(close) < 20:
        return _feature_row("SupportResistanceProximity", 0.0, 0.0, "insufficient support/resistance history")

    current_price = float(close.iloc[-1])
    window = min(60, len(close))
    support = float(low.tail(window).min())
    resistance = float(high.tail(window).max())
    range_width = (resistance - support) / current_price if current_price > EPSILON else np.nan
    if not np.isfinite(range_width) or range_width <= 0.005:
        return _feature_row("SupportResistanceProximity", 0.0, 0.0, "flat support/resistance range")

    support_distance = (current_price - support) / current_price if current_price > EPSILON else np.nan
    resistance_distance = (resistance - current_price) / current_price if current_price > EPSILON else np.nan

    bullish = _positive_score(0.03 - support_distance, 0.03)
    bearish = _positive_score(0.03 - resistance_distance, 0.03)
    diagnostic = f"support_distance={support_distance:.3f}, resistance_distance={resistance_distance:.3f}"
    return _feature_row("SupportResistanceProximity", bullish, bearish, diagnostic)


def _return_changepoint_score(close: pd.Series) -> dict:
    returns = _calculate_log_returns(close)
    if len(returns) < 25:
        return _feature_row("ReturnChangePoint", 0.0, 0.0, "insufficient return history")

    recent = returns.tail(5)
    previous = returns.iloc[-25:-5]
    previous_volatility = float(previous.std(ddof=1)) if len(previous) > 1 else 0.0
    if previous_volatility <= EPSILON:
        previous_volatility = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    if previous_volatility <= EPSILON:
        return _feature_row("ReturnChangePoint", 0.0, 0.0, "flat returns")

    mean_shift = float(recent.mean() - previous.mean())
    z_score = mean_shift / previous_volatility
    bullish = _positive_score(z_score, 1.0)
    bearish = _negative_score(z_score, 1.0)
    return _feature_row("ReturnChangePoint", bullish, bearish, f"mean_shift_z={z_score:.3f}")


def _volatility_changepoint_score(close: pd.Series) -> dict:
    returns = _calculate_log_returns(close)
    if len(returns) < 25:
        return _feature_row("VolatilityChangePoint", 0.0, 0.0, "insufficient volatility history")

    recent = returns.tail(5)
    previous = returns.iloc[-25:-5]
    recent_volatility = float(recent.std(ddof=1)) if len(recent) > 1 else 0.0
    previous_volatility = float(previous.std(ddof=1)) if len(previous) > 1 else 0.0
    if previous_volatility <= EPSILON:
        return _feature_row("VolatilityChangePoint", 0.0, 0.0, "flat prior volatility")

    volatility_ratio = recent_volatility / previous_volatility
    latest_bias = float(recent.mean())
    change_score = _positive_score(volatility_ratio - 1.2, 1.5)
    directional_strength = min(1.0, abs(latest_bias) / max(recent_volatility, EPSILON))

    bullish = change_score * directional_strength if latest_bias < 0.0 else change_score * 0.25
    bearish = change_score * directional_strength if latest_bias > 0.0 else change_score * 0.25
    diagnostic = f"volatility_ratio={volatility_ratio:.2f}, recent_return_bias={latest_bias:.4f}"
    return _feature_row("VolatilityChangePoint", bullish, bearish, diagnostic)


def _feature_row(feature: str, bullish: float, bearish: float, diagnostic: str) -> dict:
    bullish = _clip01(bullish)
    bearish = _clip01(bearish)
    if bullish > bearish and bullish >= 0.10:
        direction = "bullish"
    elif bearish > bullish and bearish >= 0.10:
        direction = "bearish"
    else:
        direction = "neutral"
    return {
        "Feature": feature,
        "BullishScore": bullish,
        "BearishScore": bearish,
        "Direction": direction,
        "Diagnostic": diagnostic,
    }


def _safe_scale(values: pd.Series) -> float:
    clean = values.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
    if clean.size == 0:
        return 1.0
    std = float(np.std(clean, ddof=1)) if clean.size > 1 else 0.0
    if std > EPSILON:
        return std
    mad = float(np.median(np.abs(clean - np.median(clean))))
    return mad if mad > EPSILON else 1.0


def _positive_score(value: float, scale: float) -> float:
    if not np.isfinite(value) or scale <= EPSILON:
        return 0.0
    return _clip01(value / scale)


def _negative_score(value: float, scale: float) -> float:
    if not np.isfinite(value) or scale <= EPSILON:
        return 0.0
    return _clip01(-value / scale)


def _clip01(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return max(0.0, float(np.clip(value, 0.0, 1.0)))


def _softmax_probabilities(scores: dict) -> dict:
    keys = ("bullish", "bearish", "no")
    values = np.asarray([float(scores.get(key, 0.0)) for key in keys], dtype=float)
    values = np.where(np.isfinite(values), values, 0.0)
    values = values - np.max(values)
    exp_values = np.exp(values)
    total = float(np.sum(exp_values))
    if total <= EPSILON:
        return {"bullish": 0.0, "bearish": 0.0, "no": 1.0}
    return {key: float(exp_values[index] / total) for index, key in enumerate(keys)}


def _blend_probabilities(monte_carlo: dict, technical: dict, technical_weight: float) -> dict:
    monte_carlo_weight = 1.0 - technical_weight
    blended = {
        key: (monte_carlo_weight * float(monte_carlo.get(key, 0.0))) +
        (technical_weight * float(technical.get(key, 0.0)))
        for key in ("bullish", "bearish", "no")
    }
    total = sum(blended.values())
    if total <= EPSILON:
        return {"bullish": 0.0, "bearish": 0.0, "no": 1.0}
    return {key: value / total for key, value in blended.items()}


def _as_percent_dict(probabilities: dict) -> dict:
    return {key: float(value) * 100.0 for key, value in probabilities.items()}


def _build_inflection_table(ticker: str,
                            current_price: float,
                            horizon_days: int,
                            move_threshold: float,
                            simulations: int,
                            combined: dict,
                            monte_carlo: dict,
                            technical: dict,
                            signal_strength: dict,
                            monte_carlo_counts: dict) -> pd.DataFrame:
    bullish = float(combined["bullish"])
    bearish = float(combined["bearish"])
    if bullish > bearish:
        dominant_bias = "bullish"
    elif bearish > bullish:
        dominant_bias = "bearish"
    else:
        dominant_bias = "neutral"

    return pd.DataFrame([{
        "Ticker": ticker.upper(),
        "HorizonDays": int(horizon_days),
        "MoveThresholdPercent": float(move_threshold * 100.0),
        "CurrentPrice": float(current_price),
        "ProbabilityBullishInflection": bullish,
        "ProbabilityBearishInflection": bearish,
        "ProbabilityNoInflection": float(combined["no"]),
        "MonteCarloBullishInflection": float(monte_carlo["bullish"]),
        "MonteCarloBearishInflection": float(monte_carlo["bearish"]),
        "MonteCarloNoInflection": float(monte_carlo["no"]),
        "TechnicalBullishInflection": float(technical["bullish"]),
        "TechnicalBearishInflection": float(technical["bearish"]),
        "TechnicalNoInflection": float(technical["no"]),
        "BullishSignalStrength": float(signal_strength.get("bullish", 0.0)),
        "BearishSignalStrength": float(signal_strength.get("bearish", 0.0)),
        "NeutralSignalStrength": float(signal_strength.get("neutral", 0.0)),
        "MonteCarloBullishPaths": int(monte_carlo_counts.get("bullish", 0)),
        "MonteCarloBearishPaths": int(monte_carlo_counts.get("bearish", 0)),
        "MonteCarloNoInflectionPaths": int(monte_carlo_counts.get("no", 0)),
        "DominantInflectionBias": dominant_bias,
        "Simulations": int(simulations),
    }])
