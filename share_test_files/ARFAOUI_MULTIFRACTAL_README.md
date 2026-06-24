# Arfaoui Wavelet Multifractal Stock Test

This program applies the equations on pages 1-8 of Arfaoui and Ben Abdallah,
"Robustness and sensitivity of some wavelet multifractal models in fractal
data modelling," *Expert Systems* 42, e13268.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-arfaoui.txt
```

## Run

Analyze Ford using stationary daily log returns:

```bash
python arfaoui_multifractal_stock.py F
```

Analyze adjusted log prices, which more closely follows the paper's stated
price-series application:

```bash
python arfaoui_multifractal_stock.py F --series log-price
```

Run sensitivity checks with another wavelet and hard thresholding:

```bash
python arfaoui_multifractal_stock.py F \
  --period 10y \
  --series log-return \
  --wavelet db4 \
  --threshold hard
```

Results are written to `arfaoui_results/` unless `--output-dir` is supplied.

Customize the VaR tail levels and dollar impact basis:

```bash
python arfaoui_multifractal_stock.py F \
  --var-levels 0.01 0.05 \
  --cost-basis 1000
```

## Terminal vs JSON output

The terminal output is intentionally short for quick review. It prints:

1. The ticker, sample size, decomposition level, and epsilon.
2. Generalized `H(q)` values.
3. Reconstruction error metrics.
4. Directional accuracy tests.
5. A short ticker-specific interpretation:
   - `scaling_behavior`: `Strong` or `Weak` scaling behavior with the median
     log-log R-squared across q.
   - `multifractality`: `Strong` or `Weak` with the `H(q)` spread and
     `H(q)`-on-q slope.
   - `quasi_self_similarity`: median `|gamma|` range and scale factor.

The `*_summary.json` file keeps the full detailed writeup and all metrics,
including the longer interpretation notes, VaR quantile-loss diagnostics,
cost-basis dollar impact, directional accuracy tests, MAPE, sMAPE, WAPE, and
output file paths.

## Paper-to-code map

| Paper item | Code implementation | Output |
|---|---|---|
| Page 2, q-mean scaling law | `paper_q_mean()` and `estimate_scaling_laws()` | `*_scaling.csv` |
| Definition 1, self-similarity exponent | Log-log scaling slopes and generalized H(q) | JSON summary and scaling CSV |
| Equation (1), open-set separation | `verify_dyadic_open_set_condition()` | JSON summary |
| Equations (2)-(4), infinite self-similar series | Finite dyadic wavelet cascade | Documented modeling basis |
| Equation (5), wavelet detail expansion | `decompose_wavelet()` and `reconstruct_from_details()` | Reconstruction CSV |
| Equation (6), gamma cascade | `calculate_gamma_ratios()` and `verify_quasi_multiplicative_identity()` | Gamma and identity CSVs |
| Equation (7), empirical wavelet estimator | PyWavelets DWT of the observed series | Reconstruction CSV |
| Pages 7-8, hard/soft thresholding | `threshold_details()` | Reconstructed estimate |
| Equations (8)-(9), estimated cascade | Ratios and product identity on estimated coefficients | Gamma, identity, and diagnostic files |
| Equations (10)-(11), quasi-self-similar form | Finite scale-varying coefficient tree | Cascade-level CSV and plot |
| Additional validation diagnostics | Directional accuracy, reconstruction error, MAPE/sMAPE/WAPE, VaR quantile loss, and dollar VaR impact | `*_summary.json` |

## Output files

For ticker `F` and `--series log-return`, the default output names are:

| File | Purpose |
|---|---|
| `F_log_return_summary.json` | Full machine-readable summary and detailed interpretation notes |
| `F_log_return_scaling.csv` | q-mean and increment scaling diagnostics |
| `F_log_return_gamma_ratios.csv` | Raw gamma cascade ratios from Equation (6) |
| `F_log_return_estimated_gamma_ratios.csv` | Gamma cascade ratios after thresholding |
| `F_log_return_cascade_identity.csv` | Equation (6) product identity check |
| `F_log_return_estimated_cascade_identity.csv` | Equation (9) estimated identity check |
| `F_log_return_cascade_levels.csv` | Per-level gamma summary statistics |
| `F_log_return_reconstruction.csv` | Observed series, threshold estimator, residuals, and detail component |
| `F_log_return_diagnostics.png` | Optional plot when `--plot` is supplied |

## Plots

### Observed overlaid with estimator

Shows the observed signal `X(t)` and the thresholded wavelet estimator. For
`--series log-return`, this is daily log returns. For `--series log-price`, this
is adjusted log price.

### Scaling test using increments

Each line/color represents a different moment order `q`. The plot tests whether
the q-moment of increments follows an approximate power law across time scales.
More linear log-log behavior gives stronger evidence of scaling behavior.

### Scale-varying cascade ratios

This shows the distribution of:

```text
log10(|gamma_j,k|)
```

at each wavelet level, from coarse to fine.

Interpretation:

- Zero means `|gamma| = 1`.
- Positive means the child coefficient is larger than its parent.
- Negative means the child coefficient is smaller than its parent.
- Wide boxes indicate substantial variation within that scale.

### Pointwise estimator residual

```text
threshold estimate - observed
```

Residual spikes show where the thresholded estimator misses the observed signal
most strongly.

## Important interpretation

The paper's Equation (6) product form telescopes by construction whenever no
parent coefficient is zero. A small product error verifies the implementation;
it does not prove multifractality. The substantive diagnostics are:

1. Whether generalized H(q) changes materially with q.
2. Whether the gamma distributions change across wavelet levels.
3. Whether those findings survive changes in period, signal type, wavelet,
   threshold rule, and threshold size.

Use `--series log-return` for the primary statistical result and repeat with
`--series log-price` as a paper-literal sensitivity check. Strong persistence
in log prices can arise mechanically from their nonstationarity.

All directional accuracy and VaR results are in-sample reconstruction
diagnostics. They should not be described as forecast accuracy unless the model
is fit on an earlier training window and evaluated on unseen dates.

## Validation diagnostics

### Directional accuracy

The directional test compares whether the observed value and thresholded
estimator have the same sign on the same date. This measures reconstruction
quality, not next-day prediction.

`majority_direction_baseline` is the accuracy from always guessing whichever
direction occurred more often in the observed sample. The estimator is more
informative only if `directional_accuracy` exceeds this baseline.

### Reconstruction error

The script reports L2 norm, relative L2 norm, RMSE, MAE, maximum absolute error,
correlation, MAPE, sMAPE, and WAPE.

MAPE is included because it is intuitive, but it can be unstable for stock
returns near zero. Use sMAPE and WAPE as better-behaved companion metrics.

### Value-at-Risk quantile loss

For each lower-tail probability in `--var-levels`, the script compares:

```text
observed_return_quantile
estimated_return_quantile
```

The estimated quantile is scored against the observed series using quantile
loss, also called pinball loss. Lower loss is better.

Key JSON fields:

- `observed_var_loss_positive`: positive-dollar-style VaR return from observed data.
- `estimated_var_loss_positive`: positive-dollar-style VaR return from the estimator.
- `estimator_minus_observed_quantile`: positive means the estimator is less
  negative and may understate downside risk; negative means it is more
  conservative.
- `quantile_loss_ratio_to_observed_oracle`: values near `1` indicate closer
  VaR calibration.
- `observed_exceedance_rate_below_estimated_var`: should be close to the target
  tail probability, such as `1%` or `5%`.
- `dollar_impact_per_1000_notional`: ending value, dollar loss, and estimator
  error for the configured `--cost-basis`.

For log returns, the dollar impact converts returns with:

```text
ending value = cost basis * exp(log return)
```

## Paper notation issues handled explicitly

Equation (7) displays a coefficient estimator without multiplying by the
observed value `Z_i`. The code uses the standard empirical wavelet coefficient
of the observed signal, which corresponds to including `Z_i`.

The theorem on page 8 gives `S_i(x)=(x+i)/2` for `i=1,2`. The second map does
not remain inside `[0,1]`. The implementation uses the standard zero-based
dyadic maps `S_0(x)=x/2` and `S_1(x)=(x+1)/2`.

## Testing notes

### Epsilon

Reconstruction machinery. Recommended starting range: `0.0` to `0.02`.

As epsilon falls, accuracy will mechanically improve because more wavelet
coefficients survive thresholding. The meaningful question is whether a nonzero
epsilon can substantially simplify the signal while retaining direction, tail
risk, and important volatility patterns.

### Thresholding

Soft thresholding reduces every retained coefficient's magnitude. Hard
thresholding preserves retained coefficients exactly and only removes
coefficients whose absolute value is below epsilon.

### Wavelet

| Wavelet | Expected behavior                                   |
| ------- | --------------------------------------------------- |
| `haar`  | Best for abrupt jumps; can appear blocky            |
| `db4`   | Smoother reconstruction and good general default    |
| `sym4`  | Smoother with less phase distortion                 |
| `coif3` | Better smooth-trend representation but more complex |

Also note that longer wavelets such as db4 support fewer levels than haar. If PyWavelets reports that the requested level exceeds the maximum, either reduce --level or omit it so the program selects the maximum supported level.

### Level

Decomposition level. Recommended starting range: `4` to `7`.

| Level | Approximate variation captured |
|---|---|
| 1 | 2-day variation |
| 2 | 4-day variation |
| 3 | 8-day variation |
| 4 | 16-day variation |
| 5 | 32-day variation |
| 6 | 64-day variation |
| 7 | 128-day variation |

Example: Level 7 --> This allows the model to distinguish daily fluctuations from weekly, monthly, quarterly, and roughly six-month behavior.

### Level and epsilon work together:

- High level + large epsilon: only broad trends and extreme shocks survive.
- High level + small epsilon: detailed multiscale reconstruction.
- Low level + large epsilon: aggressively simplified short-horizon model.
- Low level + small epsilon: close reconstruction with limited long-horizon separation.
