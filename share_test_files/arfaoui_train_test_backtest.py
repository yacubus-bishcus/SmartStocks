#!/usr/bin/env python3
"""Train/test data handler for the Arfaoui wavelet stock estimator.

The default prediction method below is a wavelet-bootstrap Monte Carlo:

* The training log returns are denoised with the wavelet threshold estimator.
* The in-sample residuals are measured as observed minus denoised returns.
* Future paths are simulated by moving-block bootstrapping the denoised
  component and adding bootstrapped residual noise.

This is more defensible than pretending the wavelet reconstruction can directly
predict the next half. The Monte Carlo output gives point forecasts, prediction
intervals, and time-varying VaR forecasts.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from arfaoui_multifractal_stock import (
    decompose_wavelet,
    directional_accuracy_statistics,
    estimate_noise_threshold,
    reconstruction_statistics,
    reconstruct_threshold_estimator,
    retain_recent_dyadic_sample,
    threshold_details,
)


@dataclass(frozen=True)
class BacktestConfig:
    """User-facing configuration for the train/test experiment."""

    ticker: str
    period: str = "5y"
    interval: str = "1d"
    train_fraction: float = 0.5
    wavelet: str = "haar"
    level: int | None = 7
    threshold: str = "soft"
    epsilon: float | None = None
    simulations: int = 5000
    block_length: int = 20
    var_levels: tuple[float, ...] = (0.01, 0.05)
    cost_basis: float = 1000.0
    seed: int = 42
    output_dir: str = "arfaoui_backtest_results"
    plot: bool = True


@dataclass
class SplitHistory:
    """Chronological price split and derived train/test log returns."""

    train_prices: pd.Series
    test_prices: pd.Series
    train_returns: pd.Series
    test_returns: pd.Series


def download_adjusted_close(ticker: str, period: str, interval: str) -> pd.Series:
    """Download adjusted close prices from Yahoo Finance."""

    import yfinance as yf

    frame = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )
    if frame.empty or "Close" not in frame:
        raise ValueError(f"Yahoo Finance returned no close prices for {ticker!r}.")

    close = frame["Close"].squeeze().astype(float).dropna()
    close = close[close > 0]
    if len(close) < 128:
        raise ValueError(
            f"Only {len(close)} usable prices were returned; use a longer period."
        )
    close.name = "adjusted_close"
    return close


def split_price_history(close: pd.Series, train_fraction: float = 0.5) -> SplitHistory:
    """Split prices chronologically and build leakage-free log returns.

    The first test return is measured from the last train price to the first
    test price. This gives one test return for every test price date and avoids
    dropping the first out-of-sample movement.
    """

    if not 0.1 < train_fraction < 0.9:
        raise ValueError("train_fraction must be between 0.1 and 0.9.")

    split_index = int(len(close) * train_fraction)
    train_prices = close.iloc[:split_index].copy()
    test_prices = close.iloc[split_index:].copy()

    if len(train_prices) < 64 or len(test_prices) < 20:
        raise ValueError("Train/test split is too short for this backtest.")

    train_returns = np.log(train_prices / train_prices.shift(1)).dropna()

    test_base = pd.concat([train_prices.iloc[-1:], test_prices])
    test_returns = np.log(test_base / test_base.shift(1)).dropna()
    test_returns.index = test_prices.index
    test_returns.name = "observed_log_return"

    return SplitHistory(
        train_prices=train_prices,
        test_prices=test_prices,
        train_returns=train_returns,
        test_returns=test_returns,
    )


def fit_training_wavelet_estimator(
    train_returns: pd.Series,
    wavelet: str,
    level: int | None,
    threshold: str,
    epsilon: float | None,
) -> tuple[pd.Series, pd.Series, float, int]:
    """Fit the thresholded wavelet estimator on training returns only.

    Returns
    -------
    denoised_train:
        Thresholded wavelet reconstruction of the retained training returns.
    residual:
        Training return residual, observed minus denoised.
    epsilon_used:
        Fixed or estimated threshold.
    pywt_level:
        Actual DWT level used by PyWavelets.
    """

    retained = retain_recent_dyadic_sample(train_returns)
    values = retained.to_numpy(dtype=float)

    signal_mean = float(np.mean(values))
    centered = values - signal_mean

    model = decompose_wavelet(
        centered,
        wavelet_name=wavelet,
        requested_level=level,
    )
    epsilon_used = (
        float(epsilon)
        if epsilon is not None
        else estimate_noise_threshold(model.details[-1], len(centered))
    )
    thresholded_details = threshold_details(
        model.details,
        epsilon=epsilon_used,
        method=threshold,
    )
    denoised_centered = reconstruct_threshold_estimator(
        model,
        thresholded_details,
        len(centered),
    )
    denoised_values = denoised_centered + signal_mean

    denoised_train = pd.Series(
        denoised_values,
        index=retained.index,
        name="denoised_train_return",
    )
    residual = pd.Series(
        retained.to_numpy(dtype=float) - denoised_values,
        index=retained.index,
        name="train_residual",
    )

    return denoised_train, residual, epsilon_used, model.pywt_level


def moving_block_bootstrap(
    values: np.ndarray,
    horizon: int,
    simulations: int,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate simulated paths by sampling contiguous historical blocks."""

    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("values must be a non-empty one-dimensional array.")
    if horizon <= 0 or simulations <= 0:
        raise ValueError("horizon and simulations must be positive.")
    if block_length <= 0:
        raise ValueError("block_length must be positive.")

    block_length = min(block_length, len(values))
    max_start = len(values) - block_length
    paths = np.empty((simulations, horizon), dtype=float)

    for simulation in range(simulations):
        pieces: list[np.ndarray] = []
        remaining = horizon
        while remaining > 0:
            start = int(rng.integers(0, max_start + 1))
            block = values[start : start + min(block_length, remaining)]
            pieces.append(block)
            remaining -= len(block)
        paths[simulation] = np.concatenate(pieces)

    return paths


def simulate_wavelet_bootstrap_returns(
    denoised_train: pd.Series,
    residual: pd.Series,
    horizon: int,
    simulations: int,
    block_length: int,
    seed: int,
) -> np.ndarray:
    """Simulate future returns from denoised wavelet structure plus residual noise."""

    rng = np.random.default_rng(seed)
    structure_paths = moving_block_bootstrap(
        denoised_train.to_numpy(dtype=float),
        horizon=horizon,
        simulations=simulations,
        block_length=block_length,
        rng=rng,
    )

    # Residuals are sampled independently. This keeps the broad wavelet-scale
    # structure in blocks while still allowing pointwise noise around it.
    residual_values = residual.to_numpy(dtype=float)
    noise_indices = rng.integers(0, len(residual_values), size=(simulations, horizon))
    noise_paths = residual_values[noise_indices]

    return structure_paths + noise_paths


def pinball_loss_vector(observed: np.ndarray, forecast_quantile: np.ndarray, alpha: float) -> float:
    """Average time-varying quantile loss for a VaR forecast series."""

    error = np.asarray(observed, dtype=float) - np.asarray(forecast_quantile, dtype=float)
    return float(np.mean(np.maximum(alpha * error, (alpha - 1.0) * error)))


def summarize_simulated_returns(
    test_returns: pd.Series,
    simulated_returns: np.ndarray,
    var_levels: Iterable[float],
) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    """Create forecast CSV rows and VaR backtest metrics."""

    forecast = pd.DataFrame(index=test_returns.index)
    forecast["observed_log_return"] = test_returns.to_numpy(dtype=float)
    forecast["predicted_mean_log_return"] = np.mean(simulated_returns, axis=0)
    forecast["predicted_median_log_return"] = np.median(simulated_returns, axis=0)
    forecast["predicted_p05_log_return"] = np.quantile(simulated_returns, 0.05, axis=0)
    forecast["predicted_p95_log_return"] = np.quantile(simulated_returns, 0.95, axis=0)

    var_backtest: dict[str, dict[str, float]] = {}
    observed = test_returns.to_numpy(dtype=float)

    for alpha in var_levels:
        if not 0 < alpha < 0.5:
            raise ValueError("All VaR levels must be between 0 and 0.5.")

        quantile_path = np.quantile(simulated_returns, alpha, axis=0)
        forecast[f"predicted_var_{alpha:.4g}_log_return"] = quantile_path

        exceedance = observed < quantile_path
        var_backtest[f"{alpha:.4g}"] = {
            "tail_probability": float(alpha),
            "time_varying_quantile_loss": pinball_loss_vector(
                observed,
                quantile_path,
                alpha,
            ),
            "observed_exceedance_rate": float(np.mean(exceedance)),
            "exceedance_calibration_error": float(np.mean(exceedance) - alpha),
            "average_predicted_var_log_return": float(np.mean(quantile_path)),
            "realized_test_quantile_log_return": float(np.quantile(observed, alpha)),
        }

    return forecast, var_backtest


def add_price_paths(
    forecast: pd.DataFrame,
    simulated_returns: np.ndarray,
    last_train_price: float,
    observed_test_prices: pd.Series,
    cost_basis: float,
) -> dict[str, float]:
    """Convert return forecasts into price paths and ending dollar outcomes."""

    median_return_path = forecast["predicted_median_log_return"].to_numpy(dtype=float)
    mean_return_path = forecast["predicted_mean_log_return"].to_numpy(dtype=float)

    forecast["observed_price"] = observed_test_prices.to_numpy(dtype=float)
    forecast["predicted_median_price"] = last_train_price * np.exp(
        np.cumsum(median_return_path)
    )
    forecast["predicted_mean_price"] = last_train_price * np.exp(
        np.cumsum(mean_return_path)
    )

    simulated_price_paths = last_train_price * np.exp(np.cumsum(simulated_returns, axis=1))
    forecast["predicted_price_p05"] = np.quantile(simulated_price_paths, 0.05, axis=0)
    forecast["predicted_price_p95"] = np.quantile(simulated_price_paths, 0.95, axis=0)

    start_price = float(last_train_price)
    observed_end_price = float(observed_test_prices.iloc[-1])
    median_end_price = float(forecast["predicted_median_price"].iloc[-1])
    mean_end_price = float(forecast["predicted_mean_price"].iloc[-1])

    observed_end_value = cost_basis * observed_end_price / start_price
    median_predicted_end_value = cost_basis * median_end_price / start_price
    mean_predicted_end_value = cost_basis * mean_end_price / start_price

    return {
        "cost_basis": float(cost_basis),
        "train_end_price": start_price,
        "observed_test_end_price": observed_end_price,
        "median_predicted_test_end_price": median_end_price,
        "mean_predicted_test_end_price": mean_end_price,
        "observed_end_value": float(observed_end_value),
        "median_predicted_end_value": float(median_predicted_end_value),
        "mean_predicted_end_value": float(mean_predicted_end_value),
        "median_prediction_value_error": float(
            median_predicted_end_value - observed_end_value
        ),
        "mean_prediction_value_error": float(
            mean_predicted_end_value - observed_end_value
        ),
    }


def plot_backtest(
    ticker: str,
    forecast: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot observed second-half prices against the simulated forecast band."""

    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    axes[0].plot(
        forecast.index,
        forecast["observed_price"],
        color="black",
        linewidth=1.2,
        label="Observed test price",
    )
    axes[0].plot(
        forecast.index,
        forecast["predicted_median_price"],
        color="tab:red",
        linewidth=1.1,
        label="Predicted median price",
    )
    axes[0].fill_between(
        forecast.index,
        forecast["predicted_price_p05"],
        forecast["predicted_price_p95"],
        color="tab:red",
        alpha=0.15,
        label="5%-95% simulated band",
    )
    axes[0].set_title(f"{ticker.upper()} train/test wavelet-bootstrap forecast")
    axes[0].set_ylabel("Adjusted price")
    axes[0].legend()
    axes[0].grid(alpha=0.2)

    axes[1].plot(
        forecast.index,
        forecast["observed_log_return"],
        color="black",
        linewidth=0.8,
        label="Observed test return",
    )
    axes[1].plot(
        forecast.index,
        forecast["predicted_median_log_return"],
        color="tab:red",
        linewidth=0.9,
        label="Predicted median return",
    )
    axes[1].fill_between(
        forecast.index,
        forecast["predicted_p05_log_return"],
        forecast["predicted_p95_log_return"],
        color="tab:red",
        alpha=0.15,
        label="5%-95% simulated return band",
    )
    axes[1].axhline(0.0, color="gray", linewidth=0.8)
    axes[1].set_ylabel("Log return")
    axes[1].legend()
    axes[1].grid(alpha=0.2)

    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def run_backtest(config: BacktestConfig) -> dict[str, object]:
    """Run the full train/test experiment and write CSV/JSON/PNG outputs."""

    close = download_adjusted_close(config.ticker, config.period, config.interval)
    split = split_price_history(close, config.train_fraction)

    denoised_train, residual, epsilon_used, pywt_level = fit_training_wavelet_estimator(
        split.train_returns,
        wavelet=config.wavelet,
        level=config.level,
        threshold=config.threshold,
        epsilon=config.epsilon,
    )

    simulated_returns = simulate_wavelet_bootstrap_returns(
        denoised_train=denoised_train,
        residual=residual,
        horizon=len(split.test_returns),
        simulations=config.simulations,
        block_length=config.block_length,
        seed=config.seed,
    )

    forecast, var_backtest = summarize_simulated_returns(
        test_returns=split.test_returns,
        simulated_returns=simulated_returns,
        var_levels=config.var_levels,
    )
    dollar_outcome = add_price_paths(
        forecast=forecast,
        simulated_returns=simulated_returns,
        last_train_price=float(split.train_prices.iloc[-1]),
        observed_test_prices=split.test_prices,
        cost_basis=config.cost_basis,
    )

    observed_returns = forecast["observed_log_return"].to_numpy(dtype=float)
    median_predicted_returns = forecast["predicted_median_log_return"].to_numpy(dtype=float)
    point_metrics = reconstruction_statistics(observed_returns, median_predicted_returns)
    direction_metrics = directional_accuracy_statistics(
        observed_returns,
        median_predicted_returns,
    )

    output_dir = Path(config.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{config.ticker.upper()}_train_test_backtest"
    forecast_path = output_dir / f"{stem}_forecast.csv"
    summary_path = output_dir / f"{stem}_summary.json"
    plot_path = output_dir / f"{stem}.png"

    forecast.reset_index(names="date").to_csv(forecast_path, index=False)
    if config.plot:
        plot_backtest(config.ticker, forecast, plot_path)

    summary: dict[str, object] = {
        "ticker": config.ticker.upper(),
        "config": asdict(config),
        "method": "wavelet_bootstrap_monte_carlo",
        "method_note": (
            "The wavelet estimator is fit on the first half only. Future returns "
            "are simulated by moving-block bootstrapping the denoised training "
            "component and adding bootstrapped training residuals."
        ),
        "downloaded_price_observations": int(len(close)),
        "train_price_observations": int(len(split.train_prices)),
        "test_price_observations": int(len(split.test_prices)),
        "train_start": str(split.train_prices.index[0]),
        "train_end": str(split.train_prices.index[-1]),
        "test_start": str(split.test_prices.index[0]),
        "test_end": str(split.test_prices.index[-1]),
        "epsilon_used": float(epsilon_used),
        "pywt_level_used": int(pywt_level),
        "point_forecast_metrics_on_test_returns": point_metrics,
        "directional_accuracy_on_test_returns": direction_metrics,
        "time_varying_var_backtest": var_backtest,
        "dollar_outcome": dollar_outcome,
        "output_files": {
            "forecast": str(forecast_path),
            "summary": str(summary_path),
            "plot": str(plot_path) if config.plot else None,
        },
    }

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return summary


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Split a ticker history into train/test halves and evaluate an "
            "out-of-sample wavelet-bootstrap forecast."
        )
    )
    parser.add_argument("--ticker", help="Yahoo Finance ticker, for example F or AAPL")
    parser.add_argument("--period", default="5y", help="Yahoo Finance period")
    parser.add_argument("--interval", default="1d", help="Yahoo Finance interval")
    parser.add_argument("--train-fraction", type=float, default=0.5)
    parser.add_argument("--wavelet", default="haar")
    parser.add_argument("--level", type=int, default=7)
    parser.add_argument("--threshold", choices=("hard", "soft"), default="soft")
    parser.add_argument("--epsilon", type=float)
    parser.add_argument("--simulations", type=int, default=5000)
    parser.add_argument("--block-length", type=int, default=20)
    parser.add_argument("--var-levels", type=float, nargs="+", default=[0.01, 0.05])
    parser.add_argument("--cost-basis", type=float, default=1000.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="arfaoui_backtest_results")
    parser.add_argument("--no-plot", action="store_true", help="Skip PNG plot output")
    return parser


def print_summary(summary: dict[str, object]) -> None:
    """Short terminal report for quick backtest review."""

    direction = summary["directional_accuracy_on_test_returns"]
    point = summary["point_forecast_metrics_on_test_returns"]
    dollar = summary["dollar_outcome"]

    print(f"\nCompleted train/test backtest for {summary['ticker']}")
    print(
        f"Train: {summary['train_start']} to {summary['train_end']} "
        f"({summary['train_price_observations']} prices)"
    )
    print(
        f"Test:  {summary['test_start']} to {summary['test_end']} "
        f"({summary['test_price_observations']} prices)"
    )
    print(f"Method: {summary['method']}")
    print(f"Wavelet level used: {summary['pywt_level_used']}")
    print(f"Epsilon used: {summary['epsilon_used']:.8g}")
    print("Point forecast on test returns:")
    print(f"  RMSE: {point['rmse']:.8g}")
    print(f"  MAE:  {point['mae']:.8g}")
    print(f"  Corr: {point['correlation']:.4f}")
    print("Directional test on test returns:")
    print(f"  Accuracy: {direction['directional_accuracy']:.2%}")
    print(f"  Majority baseline: {direction['majority_direction_baseline']:.2%}")
    print(f"  Above baseline: {direction['accuracy_above_baseline']:.2%}")
    print("Time-varying VaR backtest:")
    for level, results in summary["time_varying_var_backtest"].items():
        print(
            f"  alpha={level}: loss={results['time_varying_quantile_loss']:.8g}, "
            f"exceedance={results['observed_exceedance_rate']:.2%}"
        )
    print("Dollar outcome:")
    print(f"  Observed ending value: ${dollar['observed_end_value']:.2f}")
    print(f"  Median predicted ending value: ${dollar['median_predicted_end_value']:.2f}")
    print(f"  Median value error: ${dollar['median_prediction_value_error']:.2f}")
    print("Output files:")
    for name, path in summary["output_files"].items():
        if path is not None:
            print(f"  {name}: {path}")


def main() -> None:
    args = build_argument_parser().parse_args()
    config = BacktestConfig(
        ticker=args.ticker,
        period=args.period,
        interval=args.interval,
        train_fraction=args.train_fraction,
        wavelet=args.wavelet,
        level=args.level,
        threshold=args.threshold,
        epsilon=args.epsilon,
        simulations=args.simulations,
        block_length=args.block_length,
        var_levels=tuple(args.var_levels),
        cost_basis=args.cost_basis,
        seed=args.seed,
        output_dir=args.output_dir,
        plot=not args.no_plot,
    )
    summary = run_backtest(config)
    print_summary(summary)


if __name__ == "__main__":
    main()
