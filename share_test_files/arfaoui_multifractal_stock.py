#!/usr/bin/env python3
"""Test the multifractal wavelet equations from Arfaoui and Ben Abdallah.

This script operationalizes the equations appearing on pages 1-8 of:

    Arfaoui, S. and Ben Abdallah, N. (2025), "Robustness and sensitivity
    of some wavelet multifractal models in fractal data modelling",
    Expert Systems 42, e13268. DOI: 10.1111/exsy.13268.

The paper is written in continuous/function notation and contains infinite
series. A finite stock history requires several explicit numerical choices:

1. Yahoo Finance adjusted closes are converted to either log prices or log
   returns. Log price is the closest analogue to the paper's price signal
   X(t); log return is usually the more defensible stationary input.
2. The most recent 2**J observations are retained so that each coefficient
   has an unambiguous dyadic parent, as required by Equations (5)-(9).
3. PyWavelets supplies the finite orthonormal DWT analogue of Equation (5).
4. The paper's infinite sums are truncated at the largest supported DWT level.
5. Equation (7) appears to omit the observed value Z_i in its displayed
   coefficient estimator. This script uses the standard empirical wavelet
   coefficient of the observed signal, equivalent to including Z_i.
6. Theorem 1 writes S_i(x)=(x+i)/2 for i=1,2, although S_2([0,1]) is not
   contained in [0,1]. The standard zero-based dyadic maps S_0(x)=x/2 and
   S_1(x)=(x+1)/2 are used when checking Equation (1).

The program does not claim that a visually good wavelet reconstruction proves
multifractality. It produces diagnostics with which the paper's scaling and
scale-varying cascade claims can be evaluated for a selected stock.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import numpy as np
import pandas as pd


PAPER_REFERENCE = (
    "Arfaoui and Ben Abdallah (2025), Expert Systems 42:e13268, "
    "DOI 10.1111/exsy.13268"
)


@dataclass
class WaveletModel:
    """Finite numerical counterpart of Equations (5)-(9).

    Attributes
    ----------
    approximation:
        Coarsest scaling coefficients returned by the DWT.
    details:
        Detail arrays ordered in the paper's direction: ``details[0]`` is
        paper level j=0 (coarsest, normally one coefficient for Haar), and
        increasing j moves toward finer scales.
    pywt_level:
        Number of wavelet decomposition levels.
    """

    approximation: np.ndarray
    details: list[np.ndarray]
    wavelet: str
    mode: str
    pywt_level: int


def download_stock_series(
    ticker: str,
    period: str,
    interval: str,
    series_kind: str,
) -> pd.Series:
    """Download adjusted closes and construct the signal X(t).

    The article discusses financial price series but its scaling arguments
    concern fluctuations. Therefore both interpretations are exposed:

    * ``log-price``: X(t)=log(P_t), closest to the paper's price-series setup.
    * ``log-return``: X(t)=log(P_t/P_{t-1}), preferable for stationarity.
    """
    import yfinance as yf
    frame = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )

    if frame.empty or "Close" not in frame: # pyright: ignore[reportOperatorIssue, reportOptionalMemberAccess]
        raise ValueError(f"Yahoo Finance returned no close prices for {ticker!r}.")

    close = frame["Close"].squeeze().astype(float).dropna() # pyright: ignore[reportAttributeAccessIssue]
    close = close[close > 0]

    if series_kind == "log-price":
        signal = np.log(close)
    elif series_kind == "log-return":
        signal = np.log(close / close.shift(1)).dropna() # pyright: ignore[reportAttributeAccessIssue]
    else:  # Protected by argparse, retained for programmatic use.
        raise ValueError(f"Unknown series kind: {series_kind}")

    signal.name = series_kind
    if len(signal) < 64:
        raise ValueError(
            f"Only {len(signal)} usable observations were returned; at least 64 "
            "are required for a meaningful multiscale calculation."
        )
    return signal


def retain_recent_dyadic_sample(series: pd.Series) -> pd.Series:
    """Retain the most recent power-of-two sample for the dyadic cascade.

    Equations (5)-(9) use exactly 2**j children at paper level j and map child
    k to parent floor(k/2). Using a 2**J sample with periodized DWT boundaries
    preserves this binary tree in a finite calculation.
    """

    length = 2 ** int(math.floor(math.log2(len(series))))
    return series.iloc[-length:].copy()


def verify_dyadic_open_set_condition() -> dict[str, object]:
    """Numerically document Equation (1) for standard dyadic contractions.

    For the open interval I=(0,1), S_0(I)=(0,1/2) and S_1(I)=(1/2,1), so the
    images are contained in I and disjoint. Their closures touch at one point;
    this is allowed by the usual open-set condition.
    """

    return {
        "equation": 1,
        "maps": {"S0(x)": "x/2", "S1(x)": "(x+1)/2"},
        "S0_open_image": "(0, 0.5)",
        "S1_open_image": "(0.5, 1)",
        "contained_in_open_unit_interval": True,
        "open_images_disjoint": True,
    }


def paper_q_mean(signal: np.ndarray, scales: Iterable[int], q: float) -> np.ndarray:
    """Calculate the q-mean M_q(t) displayed on page 2.

        M_q(t) = (t/N) * sum_{j=1}^{floor(N/t)} |X(jt)|**q.

    With zero-based Python arrays, the paper's X(jt), j=1,...,floor(N/t), is
    represented by indices t-1, 2t-1, ..., floor(N/t)t-1. This function is a
    literal implementation of the displayed equation, not an increment-based
    structure function.
    """

    values = np.asarray(signal, dtype=float)
    n = len(values)
    moments: list[float] = []

    for scale in scales:
        sampled = values[scale - 1 : n : scale]
        moments.append((scale / n) * np.sum(np.abs(sampled) ** q))

    return np.asarray(moments)


def increment_q_mean(signal: np.ndarray, scales: Iterable[int], q: float) -> np.ndarray:
    """Companion diagnostic using scale-t increments |X(s+t)-X(s)|**q.

    The paper's displayed q-mean samples X(jt) directly. In empirical finance,
    generalized Hurst/multifractal analysis more commonly studies increments.
    Reporting both prevents an apparent scaling result from being driven only
    by a nonstationary price level.
    """

    values = np.asarray(signal, dtype=float)
    moments: list[float] = []
    for scale in scales:
        increments = values[scale:] - values[:-scale]
        moments.append(float(np.mean(np.abs(increments) ** q)))
    return np.asarray(moments)


def log_log_r_squared(
    scales: np.ndarray,
    moments: np.ndarray,
    slope: float,
    intercept: float,
) -> float:
    """Return R-squared for a power-law fit in log-log coordinates."""

    observed = np.log(moments)
    fitted = intercept + slope * np.log(scales)
    residual_sum_squares = float(np.sum((observed - fitted) ** 2))
    total_sum_squares = float(np.sum((observed - np.mean(observed)) ** 2))
    if total_sum_squares <= np.finfo(float).eps:
        return 1.0 if residual_sum_squares <= np.finfo(float).eps else 0.0
    return float(1.0 - residual_sum_squares / total_sum_squares)


def estimate_scaling_laws(
    signal: np.ndarray,
    q_values: Iterable[float],
    max_scale: int,
) -> pd.DataFrame:
    """Estimate page-2 scaling exponents over dyadic time scales.

    The paper writes M_q(t) approximately t**(h_q(t)+1). If h_q is treated as
    constant over the fitted range, the log-log slope tau(q) satisfies
    h_q = tau(q)-1. We report that literal-paper value.

    For the increment diagnostic, the conventional relationship is
    E|X(s+t)-X(s)|**q approximately t**tau(q), with generalized Hurst exponent
    H(q)=tau(q)/q. Nonlinearity of tau(q) in q is evidence consistent with
    multifractality; it is not by itself a definitive causal test.
    """

    scales = 2 ** np.arange(0, int(math.floor(math.log2(max_scale))) + 1)
    rows: list[dict[str, float | int | str]] = []

    for q in q_values:
        literal = paper_q_mean(signal, scales, q)
        increments = increment_q_mean(signal, scales, q)

        valid_literal = np.isfinite(literal) & (literal > 0)
        valid_increment = np.isfinite(increments) & (increments > 0)

        literal_slope, literal_intercept = np.polyfit(
            np.log(scales[valid_literal]), np.log(literal[valid_literal]), 1
        )
        increment_slope, increment_intercept = np.polyfit(
            np.log(scales[valid_increment]), np.log(increments[valid_increment]), 1
        )
        literal_r_squared = log_log_r_squared(
            scales[valid_literal], literal[valid_literal], literal_slope, literal_intercept
        )
        increment_r_squared = log_log_r_squared(
            scales[valid_increment],
            increments[valid_increment],
            increment_slope,
            increment_intercept,
        )

        for scale, literal_value, increment_value in zip(
            scales, literal, increments, strict=True
        ):
            rows.append(
                {
                    "q": float(q),
                    "scale": int(scale),
                    "paper_Mq": float(literal_value),
                    "paper_tau_q": float(literal_slope),
                    "paper_log_log_r_squared": literal_r_squared,
                    "paper_h_q_equals_tau_minus_1": float(literal_slope - 1.0),
                    "paper_fitted_Mq": float(
                        np.exp(literal_intercept) * scale**literal_slope
                    ),
                    "increment_Mq": float(increment_value),
                    "increment_tau_q": float(increment_slope),
                    "generalized_H_q": float(increment_slope / q),
                    "increment_log_log_r_squared": increment_r_squared,
                    "increment_fitted_Mq": float(
                        np.exp(increment_intercept) * scale**increment_slope
                    ),
                }
            )

    return pd.DataFrame(rows)


def decompose_wavelet(
    signal: np.ndarray,
    wavelet_name: str,
    requested_level: int | None,
) -> WaveletModel:
    """Compute the finite DWT representation corresponding to Equation (5).

    PyWavelets returns [cA_J, cD_J, cD_(J-1), ..., cD_1]. The paper indexes
    detail coefficients from coarse to fine as j=0,1,..., so ``details`` keeps
    PyWavelets' returned detail order and relabels cD_J as paper level zero.

    ``periodization`` is used because it preserves dyadic coefficient counts
    and is appropriate for the paper's parent index floor(k/2). Haar is the
    default CLI wavelet because its compact support makes that tree exact;
    other orthogonal wavelets can be requested for sensitivity analysis.
    """
    import pywt
    wavelet = pywt.Wavelet(wavelet_name) # pyright: ignore[reportAttributeAccessIssue]
    maximum_level = pywt.dwt_max_level(len(signal), wavelet.dec_len)
    level = maximum_level if requested_level is None else requested_level

    if not 1 <= level <= maximum_level:
        raise ValueError(
            f"Wavelet {wavelet_name!r} supports levels 1-{maximum_level} for "
            f"{len(signal)} observations, but level {level} was requested."
        )

    coefficients = pywt.wavedec(
        signal,
        wavelet=wavelet,
        mode="periodization",
        level=level,
    )
    return WaveletModel(
        approximation=np.asarray(coefficients[0]),
        details=[np.asarray(detail) for detail in coefficients[1:]],
        wavelet=wavelet_name,
        mode="periodization",
        pywt_level=level,
    )


def reconstruct_from_details(model: WaveletModel, sample_length: int) -> np.ndarray:
    """Reconstruct D_X,psi(t), the detail component in Equation (5)."""
    import pywt
    coefficient_list = [np.zeros_like(model.approximation), *model.details]
    result = pywt.waverec(
        coefficient_list,
        wavelet=model.wavelet,
        mode=model.mode,
    )
    return np.asarray(result[:sample_length])


def calculate_gamma_ratios(
    details: list[np.ndarray],
    zero_tolerance: float,
) -> pd.DataFrame:
    """Calculate gamma_j^k=d_j,k/d_(j-1,floor(k/2)) from page 7.

    Ratios with a numerically vanishing parent are recorded as NaN rather than
    infinity. This explicitly exposes the drawback discussed immediately after
    Equation (6): a tiny parent can create an arbitrarily large cascade ratio.
    """

    rows: list[dict[str, float | int | bool]] = []
    for paper_level in range(1, len(details)):
        children = details[paper_level]
        parents = details[paper_level - 1]

        for child_k, child in enumerate(children):
            parent_k = child_k // 2
            parent = parents[parent_k]
            parent_vanishing = bool(abs(parent) <= zero_tolerance)
            gamma = np.nan if parent_vanishing else child / parent

            rows.append(
                {
                    "paper_level_j": paper_level,
                    "child_k": child_k,
                    "parent_k_floor_k_over_2": parent_k,
                    "d_j_k": float(child),
                    "d_parent": float(parent),
                    "parent_vanishing": parent_vanishing,
                    "gamma_j_k": float(gamma) if np.isfinite(gamma) else np.nan,
                    "abs_gamma_j_k": (
                        float(abs(gamma)) if np.isfinite(gamma) else np.nan
                    ),
                }
            )

    return pd.DataFrame(rows)


def verify_quasi_multiplicative_identity(
    details: list[np.ndarray],
    zero_tolerance: float,
) -> pd.DataFrame:
    """Verify the coefficient-product identity underlying Equation (6).

    Along the dyadic ancestry of coefficient d_j,k,

        d_j,k = d_0,0 * product_{p=1..j} gamma_p^{floor(k/2**(j-p))}.

    This is an algebraic identity whenever no ancestor denominator vanishes.
    The useful empirical question is therefore not whether it telescopes, but
    whether gamma is stable across scales (exact self-similarity) or changes
    substantially (the paper's quasi-self-similar/dynamic case).
    """

    rows: list[dict[str, float | int | bool]] = []

    for level, coefficients in enumerate(details):
        for k, actual in enumerate(coefficients):
            # Equation (6) begins at a single d_0,0. A full Haar decomposition
            # has exactly that topology. Longer filters or a user-selected
            # shallower decomposition may leave several coarsest roots. The
            # same telescoping identity then holds independently in each tree.
            root_index = k // (2**level)
            root = float(details[0][root_index])
            reconstructed = root
            valid_path = abs(root) > zero_tolerance

            if level == 0:
                reconstructed = root
            else:
                for p in range(1, level + 1):
                    descendant_index = k // (2 ** (level - p))
                    parent_index = descendant_index // 2
                    parent = details[p - 1][parent_index]
                    child = details[p][descendant_index]

                    if abs(parent) <= zero_tolerance:
                        valid_path = False
                        reconstructed = np.nan
                        break
                    reconstructed *= child / parent

            error = reconstructed - actual if valid_path else np.nan
            rows.append(
                {
                    "paper_level_j": level,
                    "k": k,
                    "coarsest_root_k": root_index,
                    "actual_d_j_k": float(actual),
                    "cascade_product_d_j_k": (
                        float(reconstructed) if np.isfinite(reconstructed) else np.nan
                    ),
                    "valid_ancestry": valid_path,
                    "absolute_identity_error": (
                        float(abs(error)) if np.isfinite(error) else np.nan
                    ),
                }
            )

    return pd.DataFrame(rows)


def estimate_noise_threshold(finest_details: np.ndarray, sample_length: int) -> float:
    """Choose epsilon when the paper leaves epsilon fixed but unspecified.

    The robust noise estimate sigma_hat=median(|d|)/0.67448975 and universal
    threshold epsilon=sigma_hat*sqrt(2 log N) are standard practical choices.
    A user-supplied ``--epsilon`` overrides this estimate.
    """

    sigma_hat = np.median(np.abs(finest_details)) / 0.6744897501960817
    return float(sigma_hat * np.sqrt(2.0 * np.log(sample_length)))


def threshold_details(
    details: list[np.ndarray],
    epsilon: float,
    method: str,
) -> list[np.ndarray]:
    """Apply the hard or soft wavelet estimator displayed on pages 7-8.

    Hard: d_tilde = d * 1{|d| > epsilon}.
    Soft: d_tilde = sign(d) * max(|d|-epsilon, 0).

    The PDF's soft-threshold typography is compact; the second expression is
    the standard meaning of (|d|-epsilon)_+ sign(d).
    """

    thresholded: list[np.ndarray] = []
    for detail in details:
        if method == "hard":
            estimate = detail * (np.abs(detail) > epsilon)
        elif method == "soft":
            estimate = np.sign(detail) * np.maximum(np.abs(detail) - epsilon, 0.0)
        else:
            raise ValueError(f"Unknown threshold method: {method}")
        thresholded.append(estimate)
    return thresholded


def reconstruct_threshold_estimator(
    model: WaveletModel,
    thresholded_details: list[np.ndarray],
    sample_length: int,
) -> np.ndarray:
    """Finite implementation of the estimator in Equations (7), (9), and (11)."""
    import pywt
    coefficients = [model.approximation, *thresholded_details]
    reconstruction = pywt.waverec(
        coefficients,
        wavelet=model.wavelet,
        mode=model.mode,
    )
    return np.asarray(reconstruction[:sample_length])


def cascade_level_summary(gamma_frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize whether cascade ratios vary from one scale to another."""

    finite = gamma_frame[np.isfinite(gamma_frame["gamma_j_k"])].copy()
    if finite.empty:
        return pd.DataFrame()

    return (
        finite.groupby("paper_level_j")["abs_gamma_j_k"]
        .agg(
            coefficient_count="count",
            mean_abs_gamma="mean",
            median_abs_gamma="median",
            std_abs_gamma="std",
            min_abs_gamma="min",
            max_abs_gamma="max",
        )
        .reset_index()
    )


def reconstruction_statistics(observed: np.ndarray, estimated: np.ndarray) -> dict[str, float]:
    """Report global and percentage reconstruction errors.

    MAPE is included as requested, but it is unstable for returns near zero.
    The function therefore reports how many zero observations were excluded
    and also supplies sMAPE and WAPE as better-behaved companions.
    """

    residual = estimated - observed
    denominator = np.linalg.norm(observed)
    percentage_tolerance = 1e-12
    mape_valid = np.abs(observed) > percentage_tolerance
    smape_denominator = np.abs(observed) + np.abs(estimated)
    smape_valid = smape_denominator > percentage_tolerance

    return {
        "l2_norm": float(np.linalg.norm(residual)),
        "relative_l2_norm": float(
            np.linalg.norm(residual) / denominator if denominator > 0 else np.nan
        ),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "mae": float(np.mean(np.abs(residual))),
        "mean_absolute_percentage_error_percent": float(
            100.0 * np.mean(np.abs(residual[mape_valid] / observed[mape_valid]))
            if np.any(mape_valid)
            else np.nan
        ),
        "mape_observations_used": int(np.sum(mape_valid)),
        "mape_zero_observations_excluded": int(np.sum(~mape_valid)),
        "symmetric_mape_percent": float(
            200.0
            * np.mean(
                np.abs(residual[smape_valid]) / smape_denominator[smape_valid]
            )
            if np.any(smape_valid)
            else np.nan
        ),
        "weighted_absolute_percentage_error_percent": float(
            100.0 * np.sum(np.abs(residual)) / np.sum(np.abs(observed))
            if np.sum(np.abs(observed)) > percentage_tolerance
            else np.nan
        ),
        "maximum_absolute_error": float(np.max(np.abs(residual))),
        "correlation": float(np.corrcoef(observed, estimated)[0, 1]),
    }


def binomial_upper_tail_probability(
    successes: int,
    trials: int,
    null_probability: float,
) -> float:
    """Exact one-sided P(X >= successes) for a Binomial null model."""

    if trials <= 0:
        return np.nan
    if null_probability <= 0:
        return 0.0 if successes > 0 else 1.0
    if null_probability >= 1:
        return 1.0

    log_p = math.log(null_probability)
    log_one_minus_p = math.log1p(-null_probability)
    probabilities = []
    for k in range(successes, trials + 1):
        log_probability = (
            math.lgamma(trials + 1)
            - math.lgamma(k + 1)
            - math.lgamma(trials - k + 1)
            + k * log_p
            + (trials - k) * log_one_minus_p
        )
        probabilities.append(math.exp(log_probability))
    return float(min(1.0, math.fsum(probabilities)))


def directional_accuracy_statistics(
    observed: np.ndarray,
    estimated: np.ndarray,
    zero_tolerance: float = 1e-12,
) -> dict[str, float | int]:
    """Evaluate same-date directional agreement of estimator and observation.

    These scores assess reconstruction, not forecasting: the wavelet estimate
    uses the full observed sample. Observed zeros are excluded; estimated zeros
    remain in the test and count as misses because they express no direction.
    """

    observed = np.asarray(observed, dtype=float)
    estimated = np.asarray(estimated, dtype=float)
    valid = np.isfinite(observed) & np.isfinite(estimated) & (
        np.abs(observed) > zero_tolerance
    )
    observed_valid = observed[valid]
    estimated_valid = estimated[valid]

    if len(observed_valid) == 0:
        return {
            "observations_tested": 0,
            "directional_hits": 0,
            "directional_accuracy": np.nan,
            "up_direction_accuracy": np.nan,
            "down_direction_accuracy": np.nan,
            "balanced_directional_accuracy": np.nan,
            "majority_direction_baseline": np.nan,
            "accuracy_above_baseline": np.nan,
            "binomial_test_p_value_vs_majority_baseline": np.nan,
            "estimated_zero_direction_count": 0,
        }

    observed_up = observed_valid > 0
    observed_down = observed_valid < 0
    estimated_up = estimated_valid > zero_tolerance
    estimated_down = estimated_valid < -zero_tolerance
    hits = (observed_up & estimated_up) | (observed_down & estimated_down)

    up_accuracy = float(np.mean(estimated_up[observed_up])) if np.any(observed_up) else np.nan
    down_accuracy = (
        float(np.mean(estimated_down[observed_down])) if np.any(observed_down) else np.nan
    )
    class_accuracies = [x for x in (up_accuracy, down_accuracy) if np.isfinite(x)]
    balanced_accuracy = float(np.mean(class_accuracies)) if class_accuracies else np.nan
    majority_baseline = float(max(np.mean(observed_up), np.mean(observed_down)))
    hit_count = int(np.sum(hits))
    accuracy = float(np.mean(hits))

    return {
        "observations_tested": int(len(observed_valid)),
        "directional_hits": hit_count,
        "directional_accuracy": accuracy,
        "up_direction_accuracy": up_accuracy,
        "down_direction_accuracy": down_accuracy,
        "balanced_directional_accuracy": balanced_accuracy,
        "majority_direction_baseline": majority_baseline,
        "accuracy_above_baseline": float(accuracy - majority_baseline),
        "binomial_test_p_value_vs_majority_baseline": (
            binomial_upper_tail_probability(
                hit_count, len(observed_valid), majority_baseline
            )
        ),
        "estimated_zero_direction_count": int(
            np.sum(np.abs(estimated_valid) <= zero_tolerance)
        ),
    }


def pinball_loss(observed: np.ndarray, quantile: float, alpha: float) -> float:
    """Return quantile (pinball) loss for a constant lower-tail forecast."""

    error = np.asarray(observed, dtype=float) - quantile
    return float(np.mean(np.maximum(alpha * error, (alpha - 1.0) * error)))


def value_at_risk_statistics(
    observed: np.ndarray,
    estimated: np.ndarray,
    levels: Iterable[float] = (0.01, 0.05),
    cost_basis: float = 1000.0,
    returns_are_log: bool = True,
) -> dict[str, dict[str, float]]:
    """Compare estimator-implied VaR quantiles with the observed distribution.

    For each lower-tail probability alpha, the estimator's empirical alpha
    quantile is treated as a constant in-sample VaR estimate and scored against
    observed X(t). The observed empirical quantile is also scored as an oracle
    benchmark. This is calibration/reconstruction analysis, not backtesting of
    an ex-ante VaR forecast.
    """

    observed = np.asarray(observed, dtype=float)
    estimated = np.asarray(estimated, dtype=float)
    results: dict[str, dict[str, float]] = {}

    for alpha in levels:
        if not 0 < alpha < 0.5:
            raise ValueError("VaR levels must be between 0 and 0.5.")

        observed_quantile = float(np.quantile(observed, alpha))
        estimated_quantile = float(np.quantile(estimated, alpha))
        dollar_impact = var_dollar_impact(observed_quantile, 
                                          estimated_quantile,
                                          cost_basis,
                                          returns_are_log,
                                          )
        benchmark_loss = pinball_loss(observed, observed_quantile, alpha)
        estimator_loss = pinball_loss(observed, estimated_quantile, alpha)
        exceedance_rate = float(np.mean(observed < estimated_quantile))

        results[f"{alpha:.4g}"] = {
            "tail_probability": float(alpha),
            "observed_return_quantile": observed_quantile,
            "estimated_return_quantile": estimated_quantile,
            "observed_var_loss_positive": float(-observed_quantile),
            "estimated_var_loss_positive": float(-estimated_quantile),
            "estimator_minus_observed_quantile": float(
                estimated_quantile - observed_quantile
            ),
            "observed_oracle_quantile_loss": benchmark_loss,
            "estimator_quantile_loss": estimator_loss,
            "quantile_loss_ratio_to_observed_oracle": float(
                estimator_loss / benchmark_loss if benchmark_loss > 0 else np.nan
            ),
            "observed_exceedance_rate_below_estimated_var": exceedance_rate,
            "exceedance_calibration_error": float(exceedance_rate - alpha),
            "dollar_impact_notional": dollar_impact,
        }

    return results


def build_ticker_interpretation_notes(
    ticker: str,
    series_kind: str,
    validation_basis: str,
    scaling: pd.DataFrame,
    level_summary: pd.DataFrame,
    reconstruction_metrics: dict[str, float | int],
    directional_metrics: dict[str, float | int],
    var_metrics: dict[str, dict[str, float]],
) -> dict[str, str]:
    """Create result-specific interpretations for the current ticker run.

    Classification cutoffs below are transparent diagnostic heuristics, not
    formal hypothesis-test thresholds. The numerical values are included so a
    reader can assess the conclusion rather than relying on a generic label.
    """

    ticker = ticker.upper()
    q_summary = (
        scaling[
            [
                "q",
                "increment_tau_q",
                "generalized_H_q",
                "increment_log_log_r_squared",
            ]
        ]
        .drop_duplicates()
        .sort_values("q")
    )
    q_values = q_summary["q"].to_numpy(dtype=float)
    tau_values = q_summary["increment_tau_q"].to_numpy(dtype=float)
    hurst_values = q_summary["generalized_H_q"].to_numpy(dtype=float)
    r_squared_values = q_summary["increment_log_log_r_squared"].to_numpy(
        dtype=float
    )

    median_r_squared = float(np.median(r_squared_values))
    minimum_r_squared = float(np.min(r_squared_values))
    tau_min = float(np.min(tau_values))
    tau_max = float(np.max(tau_values))

    if median_r_squared >= 0.95:
        scaling_strength = "strong"
    elif median_r_squared >= 0.80:
        scaling_strength = "moderate"
    else:
        scaling_strength = "weak"

    input_detail = (
        "Because this run uses log returns, the plotted increment is a difference "
        "of returns rather than a multi-day price return."
        if series_kind == "log-return"
        else "Because this run uses log prices, its increments are multi-period log returns."
    )
    scaling_note = (
        f"{ticker}'s fitted increment power laws have {scaling_strength} log-log "
        f"linearity: median R-squared={median_r_squared:.3f} and minimum "
        f"R-squared={minimum_r_squared:.3f} across q. The fitted tau(q) values "
        f"range from {tau_min:.4f} to {tau_max:.4f}. {input_detail}"
    )

    hurst_spread = float(np.max(hurst_values) - np.min(hurst_values))
    hurst_q_slope = (
        float(np.polyfit(q_values, hurst_values, 1)[0])
        if len(q_values) > 1
        else 0.0
    )
    if hurst_spread < 0.05:
        multifractal_label = "little separation in H(q), so this run provides weak evidence of multifractality"
    elif hurst_spread < 0.15:
        multifractal_label = "modest separation in H(q), so this run provides tentative evidence of multifractality"
    else:
        multifractal_label = "substantial separation in H(q), so this run provides notable evidence consistent with multifractality"

    if median_r_squared < 0.80:
        reliability_clause = (
            " The weak power-law fits materially limit that interpretation."
        )
    else:
        reliability_clause = (
            " The power-law fits are sufficiently linear for this to be a useful "
            "diagnostic, although surrogate and bootstrap tests are still needed."
        )
    multifractal_note = (
        f"For {ticker}, H(q) ranges from {np.min(hurst_values):.4f} to "
        f"{np.max(hurst_values):.4f} (spread={hurst_spread:.4f}), with an H(q)-on-q "
        f"slope of {hurst_q_slope:.4f}. This is {multifractal_label}."
        f"{reliability_clause}"
    )

    if level_summary.empty:
        quasi_note = (
            f"No finite gamma ratios were available for {ticker}, so "
            "quasi-self-similarity could not be evaluated in this run."
        )
    else:
        medians = level_summary["median_abs_gamma"].to_numpy(dtype=float)
        positive_medians = medians[medians > 0]
        if len(positive_medians) == 0:
            quasi_note = (
                f"All level-median absolute gamma ratios were zero for {ticker}; "
                "the cascade comparison is inconclusive."
            )
        else:
            gamma_factor = float(np.max(positive_medians) / np.min(positive_medians))
            if gamma_factor < 1.25:
                quasi_label = "very similar across levels, favoring an approximately scale-stable cascade"
            elif gamma_factor < 2.0:
                quasi_label = "moderately different across levels, giving tentative support to quasi-self-similarity"
            else:
                quasi_label = "materially different across levels, supporting a dynamic quasi-self-similar cascade"
            quasi_note = (
                f"{ticker}'s median |gamma| ranges from {np.min(positive_medians):.4g} "
                f"to {np.max(positive_medians):.4g}, a {gamma_factor:.2f}x scale-level "
                f"factor. The medians are {quasi_label}. Large ratios can still be "
                "caused by near-zero parent coefficients, so this is evidence rather "
                "than proof."
            )

    directional_accuracy = float(directional_metrics["directional_accuracy"])
    directional_baseline = float(
        directional_metrics["majority_direction_baseline"]
    )
    directional_p_value = float(
        directional_metrics["binomial_test_p_value_vs_majority_baseline"]
    )
    validation_note = (
        f"Using {validation_basis}, the {ticker} wavelet reconstruction matches "
        f"the observed same-date sign "
        f"{directional_accuracy:.1%} of the time versus a {directional_baseline:.1%} "
        f"majority-direction baseline (one-sided binomial p={directional_p_value:.4g}). "
        f"MAE={float(reconstruction_metrics['mae']):.6g}, "
        f"MAPE={float(reconstruction_metrics['mean_absolute_percentage_error_percent']):.2f}%, "
        f"and sMAPE={float(reconstruction_metrics['symmetric_mape_percent']):.2f}%. "
        "MAPE should be treated cautiously whenever observed values are close to zero."
    )

    highest_var_level = max(var_metrics, key=lambda key: var_metrics[key]["tail_probability"])
    selected_var = var_metrics[highest_var_level]
    risk_note = (
        f"At the {selected_var['tail_probability']:.1%} lower-tail level, {ticker}'s "
        f"observed return quantile is {selected_var['observed_return_quantile']:.4%} "
        f"and the estimator-implied quantile is "
        f"{selected_var['estimated_return_quantile']:.4%}. Its observed exceedance "
        f"rate is {selected_var['observed_exceedance_rate_below_estimated_var']:.2%}, "
        f"with quantile-loss ratio "
        f"{selected_var['quantile_loss_ratio_to_observed_oracle']:.3f} relative to "
        "the in-sample observed-quantile benchmark. Values near the target exceedance "
        "rate and a loss ratio near 1 indicate closer VaR calibration."
    )

    return {
        "scaling_behavior": scaling_note,
        "multifractality": multifractal_note,
        "quasi_self_similarity": quasi_note,
        "estimator_direction_and_error": validation_note,
        "value_at_risk_quantile_loss": risk_note,
        "scope_warning": (
            "All accuracy and VaR results are in-sample reconstruction diagnostics. "
            "They must not be described as forecast accuracy unless the wavelet model "
            "is fitted on an earlier training window and evaluated on unseen dates."
        ),
    }


def make_diagnostic_plot(
    ticker: str,
    dates: pd.Index,
    signal: np.ndarray,
    reconstructed: np.ndarray,
    scaling: pd.DataFrame,
    gamma_frame: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot the page-2 scaling law and Equations (5)-(9) diagnostics."""
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(2, 2, figsize=(15, 10))

    axes[0, 0].plot(dates, signal, color="black", linewidth=1, label="Observed X(t)")
    axes[0, 0].plot(
        dates,
        reconstructed,
        color="crimson",
        linewidth=1,
        alpha=0.85,
        label="Threshold wavelet estimator",
    )
    axes[0, 0].set_title("Observed and Equation (7)/(9) estimator")
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.2)

    for q, group in scaling.groupby("q"):
        axes[0, 1].loglog(
            group["scale"],
            group["increment_Mq"],
            "o",
            markersize=4,
            label=f"q={q:g} observed",
        )
        axes[0, 1].loglog(
            group["scale"],
            group["increment_fitted_Mq"],
            "--",
            linewidth=1,
        )
    axes[0, 1].set_title("Page-2 scaling test using increments")
    axes[0, 1].set_xlabel("Scale t (observations)")
    axes[0, 1].set_ylabel("Increment q-mean")
    axes[0, 1].legend(ncol=2, fontsize=8)
    axes[0, 1].grid(alpha=0.2, which="both")

    finite_gamma = gamma_frame[
        np.isfinite(gamma_frame["gamma_j_k"])
        & (gamma_frame["abs_gamma_j_k"] > 0)
    ]
    levels = sorted(finite_gamma["paper_level_j"].unique())
    box_data = [
        np.log10(
            finite_gamma.loc[
                finite_gamma["paper_level_j"] == level, "abs_gamma_j_k"
            ]
        )
        for level in levels
    ]
    if box_data:
        axes[1, 0].boxplot(box_data, tick_labels=levels, showfliers=False)
    axes[1, 0].set_title("Scale-varying cascade ratios, Equation (6)")
    axes[1, 0].set_xlabel("Paper wavelet level j (coarse to fine)")
    axes[1, 0].set_ylabel("log10 |gamma_j^k|")
    axes[1, 0].grid(alpha=0.2)

    residual = reconstructed - signal
    axes[1, 1].plot(dates, residual, color="darkblue", linewidth=0.8)
    axes[1, 1].axhline(0.0, color="black", linestyle="--", linewidth=1)
    axes[1, 1].set_title("Pointwise estimator residual")
    axes[1, 1].set_ylabel("Estimated - observed")
    axes[1, 1].grid(alpha=0.2)

    figure.suptitle(f"{ticker.upper()} - Arfaoui wavelet multifractal diagnostics")
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)

def analyze_stock_program(
    ticker: str,
    period: str = "5y",
    interval: str = "1d",
    series: str = "log-return",
    wavelet: str = "haar",
    level: int = 7,
    q: Iterable[float] = (1.0, 2.0, 3.0),
    max_scale: int | None = None,
    threshold: str = "soft",
    epsilon: float | None = None,
    output_dir: str = "arfaoui_results",
    plot: bool = True,
    var_levels: Iterable[float] = (0.01, 0.05),
    cost_basis: float = 1000.0,
) -> dict[str, object]:
    """Run all finite, empirically testable equations from pages 1-8.

    This function is the main entry point for programmatic use. The CLI entry
    point is ``main()`` below, which parses arguments and calls this function.
    """

    args = argparse.Namespace(
        ticker=ticker,
        period=period,
        interval=interval,
        series=series,
        wavelet=wavelet,
        level=level,
        q=q,
        max_scale=max_scale,
        threshold=threshold,
        epsilon=epsilon,
        output_dir=output_dir,
        plot=plot,
        var_levels=tuple(var_levels),
        cost_basis=cost_basis
    )
    return analyze_stock(args)

def analyze_stock(args: argparse.Namespace) -> dict[str, object]:
    """Run all finite, empirically testable equations from pages 1-8."""

    original = download_stock_series(
        ticker=args.ticker,
        period=args.period,
        interval=args.interval,
        series_kind=args.series,
    )
    series = retain_recent_dyadic_sample(original)
    values = series.to_numpy(dtype=float)

    if any(q <= 0 for q in args.q):
        raise ValueError("All q moment orders must be greater than zero.")

    # Centering removes an arbitrary level before the DWT. The mean is restored
    # after reconstruction. This does not change detail coefficients for Haar
    # and reduces boundary leakage for longer wavelets.
    signal_mean = float(np.mean(values))
    centered = values - signal_mean

    default_max_scale = max(2, min(128, len(values) // 8))
    max_scale = min(args.max_scale or default_max_scale, len(values) // 4)
    if max_scale < 2:
        raise ValueError("The selected sample is too short for scaling analysis.")

    # Use the uncentered X(t) for a literal reading of the paper's q-mean.
    # The increment companion is invariant to this level shift. Centering is
    # used only for the wavelet calculation below.
    scaling = estimate_scaling_laws(values, args.q, max_scale=max_scale)

    model = decompose_wavelet(centered, args.wavelet, args.level)
    detail_component = reconstruct_from_details(model, len(centered))

    coefficient_scale = max(
        float(np.max(np.abs(detail))) for detail in model.details if len(detail)
    )
    zero_tolerance = max(np.finfo(float).eps * coefficient_scale * 100.0, 1e-15)

    gamma_frame = calculate_gamma_ratios(model.details, zero_tolerance)
    identity_frame = verify_quasi_multiplicative_identity(
        model.details, zero_tolerance
    )

    epsilon = (
        float(args.epsilon)
        if args.epsilon is not None
        else estimate_noise_threshold(model.details[-1], len(centered))
    )
    thresholded_details = threshold_details(
        model.details,
        epsilon=epsilon,
        method=args.threshold,
    )
    # Equations (8)-(9) repeat the cascade construction with estimated
    # coefficients. Calculate that second tree explicitly; thresholding can
    # create zero parents, which is precisely the stability issue discussed by
    # the authors.
    threshold_gamma_frame = calculate_gamma_ratios(
        thresholded_details, zero_tolerance
    )
    threshold_identity_frame = verify_quasi_multiplicative_identity(
        thresholded_details, zero_tolerance
    )
    reconstructed_centered = reconstruct_threshold_estimator(
        model,
        thresholded_details,
        len(centered),
    )
    reconstructed = reconstructed_centered + signal_mean

    metrics = reconstruction_statistics(values, reconstructed)
    if args.series == "log-price":
        validation_observed = np.diff(values)
        validation_estimated = np.diff(reconstructed)
        validation_basis = "first differences of log price"
    else:
        validation_observed = values
        validation_estimated = reconstructed
        validation_basis = "daily log returns"

    directional_metrics = directional_accuracy_statistics(
        validation_observed, validation_estimated
    )
    var_metrics = value_at_risk_statistics(
        validation_observed,
        validation_estimated,
        levels=getattr(args, "var_levels", (0.01, 0.05)),
        cost_basis=args.cost_basis,
        returns_are_log=(args.series == "log-return"),
    )
    level_summary = cascade_level_summary(gamma_frame)
    interpretation_notes = build_ticker_interpretation_notes(
        ticker=args.ticker,
        series_kind=args.series,
        validation_basis=validation_basis,
        scaling=scaling,
        level_summary=level_summary,
        reconstruction_metrics=metrics,
        directional_metrics=directional_metrics,
        var_metrics=var_metrics,
    )

    output_directory = Path(args.output_dir).expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"{args.ticker.upper()}_{args.series.replace('-', '_')}"

    scaling_path = output_directory / f"{stem}_scaling.csv"
    gamma_path = output_directory / f"{stem}_gamma_ratios.csv"
    threshold_gamma_path = output_directory / f"{stem}_estimated_gamma_ratios.csv"
    identity_path = output_directory / f"{stem}_cascade_identity.csv"
    threshold_identity_path = (
        output_directory / f"{stem}_estimated_cascade_identity.csv"
    )
    level_path = output_directory / f"{stem}_cascade_levels.csv"
    reconstruction_path = output_directory / f"{stem}_reconstruction.csv"
    plot_path = output_directory / f"{stem}_diagnostics.png"
    summary_path = output_directory / f"{stem}_summary.json"

    scaling.to_csv(scaling_path, index=False)
    gamma_frame.to_csv(gamma_path, index=False)
    threshold_gamma_frame.to_csv(threshold_gamma_path, index=False)
    identity_frame.to_csv(identity_path, index=False)
    threshold_identity_frame.to_csv(threshold_identity_path, index=False)
    level_summary.to_csv(level_path, index=False)
    pd.DataFrame(
        {
            "date": series.index,
            "observed": values,
            "threshold_estimate": reconstructed,
            "residual": reconstructed - values,
            "detail_component_equation_5": detail_component,
        }
    ).to_csv(reconstruction_path, index=False)

    valid_identity = identity_frame["absolute_identity_error"].dropna()
    valid_threshold_identity = threshold_identity_frame[
        "absolute_identity_error"
    ].dropna()
    generalized_h = (
        scaling[["q", "generalized_H_q"]].drop_duplicates().set_index("q")[
            "generalized_H_q"
        ]
    )
    paper_h = (
        scaling[["q", "paper_h_q_equals_tau_minus_1"]]
        .drop_duplicates()
        .set_index("q")["paper_h_q_equals_tau_minus_1"]
    )
    scaling_fit_r_squared = (
        scaling[["q", "increment_log_log_r_squared"]]
        .drop_duplicates()
        .set_index("q")["increment_log_log_r_squared"]
    )

    summary: dict[str, object] = {
        "ticker": args.ticker.upper(),
        "period_requested": args.period,
        "interval": args.interval,
        "series_kind": args.series,
        "downloaded_observations": len(original),
        "dyadic_observations_used": len(series),
        "start": str(series.index[0]),
        "end": str(series.index[-1]),
        "equation_1_open_set_check": verify_dyadic_open_set_condition(),
        "page_2_literal_h_q": {str(q): float(h) for q, h in paper_h.items()},
        "increment_generalized_H_q": {
            str(q): float(h) for q, h in generalized_h.items()
        },
        "increment_scaling_fit_r_squared": {
            str(q): float(value) for q, value in scaling_fit_r_squared.items()
        },
        "wavelet": args.wavelet,
        "boundary_mode": model.mode,
        "decomposition_levels": model.pywt_level,
        "threshold_method": args.threshold,
        "epsilon": epsilon,
        "vanishing_parent_ratio_count": int(gamma_frame["parent_vanishing"].sum()),
        "finite_gamma_count": int(gamma_frame["gamma_j_k"].notna().sum()),
        "maximum_equation_6_identity_error": (
            float(valid_identity.max()) if not valid_identity.empty else None
        ),
        "estimated_vanishing_parent_ratio_count_equations_8_9": int(
            threshold_gamma_frame["parent_vanishing"].sum()
        ),
        "estimated_finite_gamma_count_equations_8_9": int(
            threshold_gamma_frame["gamma_j_k"].notna().sum()
        ),
        "maximum_equation_9_identity_error": (
            float(valid_threshold_identity.max())
            if not valid_threshold_identity.empty
            else None
        ),
        "reconstruction_metrics": metrics,
        "directional_accuracy_tests": directional_metrics,
        "directional_and_var_evaluation_basis": validation_basis,
        "value_at_risk_quantile_loss": var_metrics,
        "interpretation_notes": interpretation_notes,
    }

    if args.plot:
        make_diagnostic_plot(
            ticker=args.ticker,
            dates=series.index,
            signal=values,
            reconstructed=reconstructed,
            scaling=scaling,
            gamma_frame=gamma_frame,
            output_path=plot_path,
        )

    
    summary["output_files"] = {
        "summary": str(summary_path),
        "plot": str(plot_path),
        "scaling": str(scaling_path),
        "gamma_ratios": str(gamma_path),
        "estimated_gamma_ratios": str(threshold_gamma_path),
        "cascade_identity": str(identity_path),
        "estimated_cascade_identity": str(threshold_identity_path),
        "cascade_level_summary": str(level_path),
        "reconstruction": str(reconstruction_path),
    }

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return summary

def var_dollar_impact(
    observed_quantile: float,
    estimated_quantile: float,
    cost_basis: float = 1000.0,
    returns_are_log: bool = True,
) -> dict[str, float]:
    """
    Dollar impact of estimator VaR error for a fixed investment amount.

    If returns are log returns:
        ending_value = cost_basis * exp(return)

    If returns are simple returns:
        ending_value = cost_basis * (1 + return)

    Positive estimator_loss_error_dollars means the estimator understated
    the dollar loss. Negative means it overstated the dollar loss.
    """

    if returns_are_log:
        observed_simple_return = float(np.expm1(observed_quantile))
        estimated_simple_return = float(np.expm1(estimated_quantile))
    else:
        observed_simple_return = float(observed_quantile)
        estimated_simple_return = float(estimated_quantile)

    observed_ending_value = cost_basis * (1.0 + observed_simple_return)
    estimated_ending_value = cost_basis * (1.0 + estimated_simple_return)

    observed_loss_dollars = cost_basis - observed_ending_value
    estimated_loss_dollars = cost_basis - estimated_ending_value

    return {
        "cost_basis": float(cost_basis),
        "observed_ending_value": float(observed_ending_value),
        "estimated_ending_value": float(estimated_ending_value),
        "observed_loss_dollars": float(observed_loss_dollars),
        "estimated_loss_dollars": float(estimated_loss_dollars),
        "estimator_loss_error_dollars": float(
            observed_loss_dollars - estimated_loss_dollars
        ),
        "ending_value_difference_dollars": float(
            estimated_ending_value - observed_ending_value
        ),
    }

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the equations on pages 1-8 of Arfaoui and Ben Abdallah's "
            "wavelet multifractal paper to a Yahoo Finance stock series."
        )
    )
    parser.add_argument("ticker", help="Yahoo Finance ticker, for example F or AAPL")
    parser.add_argument("--period", default="5y", help="Yahoo Finance period (default: 5y)")
    parser.add_argument("--interval", default="1d", help="Yahoo Finance interval (default: 1d)")
    parser.add_argument(
        "--series",
        choices=("log-price", "log-return"),
        default="log-return",
        help="Signal X(t) to analyze (default: log-return)",
    )
    parser.add_argument(
        "--wavelet",
        default="haar",
        help="Orthogonal PyWavelets wavelet (default: haar)",
    )
    parser.add_argument(
        "--level",
        type=int,
        help="DWT level; default uses the maximum supported level",
    )
    parser.add_argument(
        "--q",
        type=float,
        nargs="+",
        default=[0.5, 1.0, 2.0, 3.0, 4.0],
        help="Moment orders for the page-2 q-mean scaling law",
    )
    parser.add_argument(
        "--max-scale",
        type=int,
        help="Largest approximate time scale; default is min(128, N/8)",
    )
    parser.add_argument(
        "--threshold",
        choices=("hard", "soft"),
        default="soft",
        help="Paper's wavelet threshold estimator (default: soft)",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        help="Fixed threshold epsilon; default estimates a universal threshold",
    )
    parser.add_argument(
        "--output-dir",
        default="arfaoui_results",
        help="Directory for CSV, JSON, and PNG outputs",
    )
    parser.add_argument(
        "--var-levels",
        type=float,
        nargs="+",
        default=[0.01, 0.05],
        help="Lower-tail VaR probabilities (default: 0.01 0.05)",
    )
    parser.add_argument(
        "--cost-basis",
        type=float,
        default=1000.0,
        help="Dollar amount for VaR impact calculations (default: 1000.0)",
    )
    parser.add_argument("--plot", action="store_true", 
                        help="Generate diagnostic plot (default: False)")
    parser.add_argument("--verbose", action="store_true", help="Print detailed output (default: False)")
    return parser

def print_summary(summary: dict[str, object], verbose: bool) -> None:
    """Print a human-readable summary of the analysis results."""
    print(f"\nCompleted analysis for {summary['ticker']}")
    print(f"Observations used: {summary['dyadic_observations_used']}")
    print(f"Wavelet levels:    {summary['decomposition_levels']}")
    print(f"Threshold epsilon: {summary['epsilon']:.8g}")
    print("Generalized H(q):")
    for q, value in summary["increment_generalized_H_q"].items(): # pyright: ignore[reportAttributeAccessIssue]
        print(f"  q={q:>4}: {value:.6f}")
    print("Reconstruction metrics:")
    for name, value in summary["reconstruction_metrics"].items(): # pyright: ignore[reportAttributeAccessIssue]
        print(f"  {name}: {value:.8g}")
    print("Directional accuracy tests:")
    for name, value in summary["directional_accuracy_tests"].items(): # type: ignore
        if isinstance(value, float):
            print(f"  {name}: {value:.8g}")
        else:
            print(f"  {name}: {value}")
    print("Ticker-specific interpretation:")
    scaling_r_squared = np.array(
        list(summary["increment_scaling_fit_r_squared"].values()),
        dtype=float,
    )
    median_r_squared = float(np.median(scaling_r_squared))
    scaling_label = "Strong" if median_r_squared >= 0.80 else "Weak"
    print(
        f"  scaling_behavior: {scaling_label} Scaling Behavior "
        f"(median R-squared across q={median_r_squared:.3f})"
    )

    hq_items = sorted(
        (float(q), float(value))
        for q, value in summary["increment_generalized_H_q"].items()
    )
    q_values = np.array([item[0] for item in hq_items], dtype=float)
    hq_values = np.array([item[1] for item in hq_items], dtype=float)
    hq_spread = float(np.max(hq_values) - np.min(hq_values))
    hq_slope = float(np.polyfit(q_values, hq_values, 1)[0]) if len(hq_items) > 1 else 0.0
    multifractal_label = "Strong" if hq_spread >= 0.05 else "Weak"
    print(
        f"  multifractality: {multifractal_label} "
        f"(H(q) spread={hq_spread:.4f}, H(q)-on-q slope={hq_slope:.4f})"
    )

    level_summary_path = Path(summary["output_files"]["cascade_level_summary"])
    level_summary = pd.read_csv(level_summary_path)
    median_gamma = level_summary["median_abs_gamma"].dropna().to_numpy(dtype=float)
    positive_median_gamma = median_gamma[median_gamma > 0]
    if len(positive_median_gamma) == 0:
        print("  quasi_self_similarity: no positive median |gamma| values available")
    else:
        min_gamma = float(np.min(positive_median_gamma))
        max_gamma = float(np.max(positive_median_gamma))
        gamma_scale_factor = float(max_gamma / min_gamma)
        print(
            f"  quasi_self_similarity: median |gamma| range="
            f"{min_gamma:.4g} to {max_gamma:.4g}, "
            f"scale factor={gamma_scale_factor:.2f}x"
        )
    
    if verbose:
        print("Output files:")
        for name, path in summary["output_files"].items():
            print(f"  {name}: {path}")

def run_analysis(ticker, period="5y", interval="1d", series="log-return", 
                 wavelet="haar", level=7, q: Iterable[float] = (1.0, 2.0, 3.0),
                 max_scale=None, threshold="soft", epsilon=None, 
                 output_dir="arfaoui_results", plot=False,
                 var_levels: Iterable[float] = (0.01, 0.05),
                 cost_basis=1000.0, 
                 verbose=False) -> None:
    """Run the analysis called from another python script or notebook."""
    summary = analyze_stock_program(
        ticker=ticker,
        period=period,
        interval=interval,
        series=series,
        wavelet=wavelet,
        level=level,
        q=q,
        max_scale=max_scale,
        threshold=threshold,
        epsilon=epsilon,
        output_dir=output_dir,
        plot=plot,
        var_levels=var_levels,
        cost_basis=cost_basis,
    )
    print_summary(summary, verbose=verbose)

def main() -> None:
    args = build_argument_parser().parse_args()
    summary = analyze_stock(args)
    print_summary(summary, verbose=args.verbose)


if __name__ == "__main__":
    main()
