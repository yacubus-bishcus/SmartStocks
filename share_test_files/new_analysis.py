import argparse

import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf
from scipy.stats import levy_stable, norm
from typing import Iterable


def log_characteristic_function(t, alpha, beta, delta, scale):
    """Log characteristic function using SciPy's S1 parameterization."""
    t = np.asarray(t, dtype=float)
    abs_t = np.abs(t)
    result = np.zeros_like(t, dtype=complex)
    nonzero = abs_t > 0

    if np.isclose(alpha, 1.0):
        result[nonzero] = (
            1j * delta * t[nonzero]
            - scale * abs_t[nonzero]
            * (
                1
                + 1j
                * beta
                * (2 / np.pi)
                * np.sign(t[nonzero])
                * np.log(abs_t[nonzero])
            )
        )
    else:
        result[nonzero] = (
            1j * delta * t[nonzero]
            - (scale * abs_t[nonzero]) ** alpha
            * (
                1
                - 1j
                * beta
                * np.sign(t[nonzero])
                * np.tan(np.pi * alpha / 2)
            )
        )

    return result


def analyze_levy_stock(ticker, period="5y", interval="1d", plot=False, save=None):
    """Fit a Levy-stable distribution to the stock returns and compare to normal distribution."""
    levy_stable.parameterization = "S1"

    prices = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )["Close"].squeeze()

    if prices.empty:
        raise ValueError(f"No price data returned for {ticker}")

    returns = np.log(prices / prices.shift(1))
    r = returns.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()

    if len(r) < 100:
        raise ValueError(
            f"Only {len(r)} returns were available; at least 100 are recommended."
        )

    print(f"Fitting {len(r):,} observations. This may take some time...")

    alpha, beta, delta, scale = levy_stable.fit(r)
    gamma = scale**alpha

    print(f"\nTicker:       {ticker.upper()}")
    print(f"Observations: {len(r):,}")
    print(f"Alpha:        {alpha:.4f}")
    print(f"Beta:         {beta:.4f}")
    print(f"Delta:        {delta:.8f}")
    print(f"Scale:        {scale:.8f}")
    print(f"Gamma:        {gamma:.8g}")

    # Restrict the display range so extreme observations do not flatten the plot.
    x = np.linspace(np.percentile(r, 0.2), np.percentile(r, 99.8), 1000)

    stable_pdf = levy_stable.pdf(
        x, alpha, beta, loc=delta, scale=scale
    )
    normal_pdf = norm.pdf(
        x, loc=np.mean(r), scale=np.std(r, ddof=1)
    )

    # Use scale-adjusted frequencies for the characteristic function.
    u = np.linspace(-5, 5, 501)
    t = u / scale

    fitted_cf = np.exp(
        log_characteristic_function(
            t, alpha, beta, delta, scale
        )
    )
    empirical_cf = np.mean(
        np.exp(1j * np.outer(t, r)),
        axis=1,
    )

    if plot:
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        axes[0].hist(
            r,
            bins=100,
            density=True,
            alpha=0.45,
            color="steelblue",
            label="Observed returns",
        )
        axes[0].plot(x, stable_pdf, "r-", lw=2, label="Levy-stable PDF")
        axes[0].plot(x, normal_pdf, "g--", lw=2, label="Normal PDF")
        axes[0].set_xlabel("Daily log return")
        axes[0].set_ylabel("Density")
        axes[0].set_title(f"{ticker.upper()} Return Distribution")
        axes[0].legend()
        axes[0].grid(alpha=0.2)

        axes[1].plot(
            u, empirical_cf.real, color="black",
            label="Empirical real"
        )
        axes[1].plot(
            u, fitted_cf.real, "r--",
            label="Fitted real"
        )
        axes[1].plot(
            u, empirical_cf.imag, color="royalblue",
            label="Empirical imaginary"
        )
        axes[1].plot(
            u, fitted_cf.imag, "m--",
            label="Fitted imaginary"
        )
        axes[1].set_xlabel("Scaled frequency")
        axes[1].set_ylabel("Characteristic function")
        axes[1].set_title("Empirical vs. Fitted Characteristic Function")
        axes[1].legend()
        axes[1].grid(alpha=0.2)

        fig.suptitle(
            f"{ticker.upper()} Stable Fit: "
            f"alpha={alpha:.3f}, beta={beta:.3f}",
            fontsize=14,
        )
        fig.tight_layout()

        if save:
            fig.savefig(save, dpi=300, bbox_inches="tight")
            print(f"\nPlot saved to {save}")

        plt.show()


def hurst_rescaled_range(
    data,
    min_window=10,
    max_window=None,
    num_windows=12,
    shuffles=100,
    seed=42,
):
    """
    Estimate the Hurst exponent using classical rescaled-range analysis.

    A shuffled-data benchmark preserves the return distribution while
    destroying serial dependence.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]

    if max_window is None:
        # Require at least four blocks at the largest window.
        max_window = len(data) // 4

    if max_window <= min_window:
        raise ValueError("Not enough observations for Hurst analysis.")

    windows = np.unique(
        np.geomspace(
            min_window,
            max_window,
            num=num_windows,
        ).astype(int)
    )

    windows = windows[len(data) // windows >= 4]

    def mean_rescaled_range(values, window):
        number_of_blocks = len(values) // window
        trimmed = values[:number_of_blocks * window]
        blocks = trimmed.reshape(number_of_blocks, window)

        centered = blocks - np.mean(blocks, axis=1, keepdims=True)
        cumulative = np.cumsum(centered, axis=1)

        # Include the initial cumulative deviation of zero.
        cumulative = np.column_stack(
            [np.zeros(number_of_blocks), cumulative]
        )

        ranges = (
            np.max(cumulative, axis=1)
            - np.min(cumulative, axis=1)
        )
        standard_deviations = np.std(blocks, axis=1, ddof=0)

        valid = standard_deviations > 0

        if not np.any(valid):
            return np.nan

        return np.mean(
            ranges[valid] / standard_deviations[valid]
        )

    observed_rs = np.array(
        [mean_rescaled_range(data, window) for window in windows]
    )

    valid = np.isfinite(observed_rs) & (observed_rs > 0)
    windows = windows[valid]
    observed_rs = observed_rs[valid]

    if len(windows) < 3:
        raise ValueError("Too few valid window sizes to estimate H.")

    # The slope of log(R/S) against log(window) is the Hurst exponent.
    hurst, intercept = np.polyfit(
        np.log(windows),
        np.log(observed_rs),
        1,
    )

    fitted_rs = np.exp(intercept) * windows**hurst

    # Estimate the independent-data expectation by shuffling returns.
    rng = np.random.default_rng(seed)
    independent_rs = np.zeros(len(windows))

    for _ in range(shuffles):
        shuffled = rng.permutation(data)

        independent_rs += np.array(
            [
                mean_rescaled_range(shuffled, window)
                for window in windows
            ]
        )

    independent_rs /= shuffles
    dependence_ratio = observed_rs / independent_rs

    independent_hurst, _ = np.polyfit(
        np.log(windows),
        np.log(independent_rs),
        1,
    )

    return {
        "hurst": hurst,
        "independent_hurst": independent_hurst,
        "windows": windows,
        "observed_rs": observed_rs,
        "fitted_rs": fitted_rs,
        "independent_rs": independent_rs,
        "dependence_ratio": dependence_ratio,
    }

def analyze_hurst(ticker, period="5y", interval="1d", plot=False, save=None)-> None:
    prices = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False, # show progress bar 
        )["Close"].squeeze()

    if prices.empty:
        raise ValueError(f"No price data returned for {ticker}")

    returns = np.log(prices / prices.shift(1))
    r = returns.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()

    hurst_result = hurst_rescaled_range(r)
    print(f"\nTicker: {ticker.upper()}")
    print(f"Hurst exponent: {hurst_result['hurst']:.4f}")
    print(
        f"Independent-data Hurst exponent: "
        f"{hurst_result['independent_hurst']:.4f}"
    )
    if plot:
        windows = hurst_result["windows"]

        fig_hurst, axes_hurst = plt.subplots(1, 2, figsize=(14, 5))

        axes_hurst[0].loglog(
            windows,
            hurst_result["observed_rs"],
            "o-",
            label="Observed R/S",
        )
        axes_hurst[0].loglog(
            windows,
            hurst_result["fitted_rs"],
            "r--",
            label=f"Fitted H = {hurst_result['hurst']:.3f}",
        )
        axes_hurst[0].loglog(
            windows,
            hurst_result["independent_rs"],
            "k:",
            label="Shuffled independence benchmark",
        )
        axes_hurst[0].set_xlabel("Window length (trading days)")
        axes_hurst[0].set_ylabel("Mean rescaled range")
        axes_hurst[0].set_title(f"{ticker.upper()} Hurst R/S Analysis")
        axes_hurst[0].legend()
        axes_hurst[0].grid(alpha=0.2)

        axes_hurst[1].semilogx(
            windows,
            hurst_result["dependence_ratio"],
            "o-",
            color="darkred",
        )
        axes_hurst[1].axhline(1.0, color="black", linestyle="--")
        axes_hurst[1].set_xlabel("Window length (trading days)")
        axes_hurst[1].set_ylabel("Observed R/S / Independent R/S")
        axes_hurst[1].set_title("Dependence Ratio")
        axes_hurst[1].grid(alpha=0.2)

        fig_hurst.tight_layout()
        if save:
            plt.savefig(save, dpi=300, bbox_inches="tight")
            print(f"\nPlot saved to {save}")
        plt.show()
    return 

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Fit a Levy-stable distribution to stock returns."
    )
    parser.add_argument("--ticker", help="Stock ticker, such as F or AAPL")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--epsilon", type=float, default=None, help="Thresholding parameter for wavelet analysis")
    parser.add_argument(
        "--hurst",
        action="store_true",
        help="Estimate the Hurst exponent using rescaled-range analysis",
    )
    parser.add_argument(
        "--levy",
        action="store_true",
        help="Fit a Levy-stable distribution to the stock returns",
    )
    parser.add_argument(
        "--estimator",
        action="store_true",
        help="Test the multifractal wavelet equations"
    )
    parser.add_argument(
        "--series",
        choices=("log-price", "log-return"),
        default="log-return",
        help="Signal X(t) to analyze used for wavelet multifractal estimation (default: log-return)",
    )
    parser.add_argument("--plot", action="store_true", help="Show diagnostic plots")
    parser.add_argument("--threshold", choices=("soft", "hard"), default="soft", help="Thresholding method for wavelet analysis (default: soft)")
    parser.add_argument("--save", help="Optional output image filename")
    parser.add_argument("--wavelet", default="db4", 
                        help="Wavelet type for multifractal analysis (default: db4)")
    parser.add_argument("--level", type=int, default=4, 
                        help="Decomposition level for wavelet analysis (default: 4)")
    parser.add_argument(
        "--q",
        type=float,
        nargs="+",
        default=[0.5, 1.0, 2.0, 3.0, 4.0],
        help="Moment orders for the page-2 q-mean scaling law",
    )
    parser.add_argument("--max-scale", type=int, default=None, 
                        help="Maximum scale for multifractal analysis (default: None, which uses the maximum possible scale based on the data length and decomposition level)")
    parser.add_argument(
        "--var-levels",
        type=float,
        nargs="+",
        default=[0.01, 0.05],
        help="Lower-tail VaR probabilities (default: 0.01 0.05)",
    )
    parser.add_argument("--cost-basis", type=float, default=1000.0, 
                        help="Dollar amount for VaR impact calculations (default: 1000.0)")
    parser.add_argument("--verbose", action="store_true", default=False, help="Enable verbose output")
    parser.add_argument("--output-dir", default="arfaoui_results", help="Directory to save output files (default: arfaoui_results)")
    return parser.parse_args()

def main():
    
    args = parse_args()

    if args.hurst:
        analyze_hurst(
            ticker=args.ticker,
            period=args.period,
            interval=args.interval,
            plot=args.plot,
            save=args.save,
        )
    if args.levy:
        analyze_levy_stock(
            ticker=args.ticker,
            period=args.period,
            interval=args.interval,
            plot=args.plot,
            save=args.save,
        )

    if args.estimator:
       import arfaoui_multifractal_stock as mf_est
       mf_est.run_analysis(
           ticker=args.ticker,
           period=args.period,
           interval=args.interval,
           series=args.series,
           wavelet=args.wavelet,
           level=args.level,
           q=args.q,
           max_scale=args.max_scale,
           threshold=args.threshold,
           epsilon=args.epsilon,
           output_dir=args.output_dir,
           plot=args.plot,
           var_levels=args.var_levels,
           cost_basis=args.cost_basis,
           verbose=args.verbose,
       )


if __name__ == "__main__":
    main()