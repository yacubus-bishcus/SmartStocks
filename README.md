# SmartStocks Computational Toolkit

SmartStocks is now a headless analytics toolkit focused on high performance Monte Carlo simulations for equities. The Python
interface orchestrates data collection and reporting, while the heavy numerical lifting is delegated to a multithreaded C++
backend. Results can be delivered automatically via email so the entire workflow can run unattended.

## Highlights

- **C++ simulation engine** – Monte Carlo simulations, head-and-shoulders pattern detection, and MACD adjustments are executed in
  native code (`cpp/smartstocks_sim.cpp`) for consistent performance across platforms.
- **Python orchestration** – High-level logic for fetching market data, estimating parameters, and preparing reports remains in
  Python for readability and extensibility.
- **Email-ready or Excel-only workflows** – Use `generate_email_report.py` to email forecasts or
  `generate_forecast_csv.py` to simply save the prediction data locally as a workbook.
- **No GUI dependencies** – All graphical application code has been removed so the project can run in batch or server
  environments.

## Project layout

```
SmartStocks/
├── cpp/                    # C++ backend source and CMake build files
├── generate_email_report.py # CLI wrapper that runs simulations and optionally emails the report
├── generate_forecast_csv.py # Minimal CLI to store simulations on disk
├── email_reporter.py        # SMTP helper utilities
├── MonteCarlo.py            # Python Monte Carlo wrapper that calls the C++ backend
├── SmartStocksAnalysis.py   # Existing analysis logic updated to use the C++ engine
└── ...                      # Other supporting modules
```

## Building the C++ backend

The Python code expects the simulator executable at `cpp/build/smartstocks_sim`. Build it once before running simulations:

```bash
cd cpp
cmake -S . -B build
cmake --build build --config Release
```
Force a clean rebuild when needed. If you suspect stale objects (for example, after switching compilers or changing build flags), either delete the cpp/build/ directory before repeating the steps above or run cmake --build build --config Release --target clean followed by another build invocation. This ensures the executable is regenerated from scratch with the latest sources and configuration.

You can override the executable location at runtime with the environment variable `SMARTSTOCKS_CPP_EXEC`.

## Generating and emailing a report

1. Install dependencies. The project only relies on Python libraries now that the GUI has been removed:

   ```bash
   pip install -r requirements.txt
   ```

2. Build the C++ executable as shown above.

3. Run the report generator:

   ```bash
   python generate_email_report.py \
     --ticker AAPL \
     --period 6mo \
     --interval 1d \
     --simulations 500 \
     --sim-time 30 \
     --recipient you@example.com \
     --smtp-server smtp.example.com \
     --smtp-port 587 \
     --smtp-username reports@example.com \
     --smtp-password yourpassword
   ```

   An Excel workbook containing the expected price path, standard deviation, standard error of the mean, and 5th–95th percentile bands will be written to `output/`, and the summary email will be
   sent with the workbook attached. Provide `--no-email` (and omit the email arguments) to skip the SMTP step for local runs.

## Saving forecasts without email

When you only need the Excel output, the lightweight helper avoids any SMTP configuration:

```bash
python -m generate_forecast \
  --ticker AAPL \
  --period 6mo \
  --interval 1d \
  --simulations 500 \
  --sim-time 30 \
  --output-file output/AAPL_forecast.xlsx
```

Both CLIs share the same simulation parameters and rely exclusively on the C++ backend for numerical work.

## Configuration notes

- Set `--processes` to the number of hardware threads you want the C++ engine to use.
- Provide `--jump-parameter`, `--h-s-window`, and `--incremental-steps` to tune jump detection and technical adjustments.
- To reproducibly rerun simulations, pass `--seed <int>`.
- SMTP credentials can also be provided via the `MAIL_PASSWORD`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_SERVER`, and `MAIL_PORT`environment variables.

## How the stock prediction pipeline works

1. **Market data ingestion and preprocessing** – `SmartStocksAnalysis.calculate_futures` hydrates each requested ticker with
   historical candles pulled through `yfinance`. The data is passed to helper routines in
   `Simulation_Analysis` which build features such as an averaged OHLC price series, intraday return series, and a rolling
   volatility regime classifier that distinguishes calm and turbulent periods.
2. **Model calibration** – For every stock the `MonteCarlo` wrapper derives the initial price, drift, and volatility from the
   processed features, while also estimating jump statistics by counting return outliers over the chosen lookback window. This
   step caches the jump frequency, jump size distribution, and recent volatility cluster so the downstream simulator uses
   parameters that reflect the market’s latest state.
3. **C++ simulation engine** – The calibrated inputs are written to a temporary config file and executed by the
   multithreaded `smartstocks_sim` binary. The engine evolves each path with a geometric Brownian motion plus Poisson jump
   component, applies head-and-shoulders pattern reductions and MACD-derived bull/bear adjustments over multiple incremental
   steps, and clamps prices inside user-defined caps before aggregating interval means and standard deviations across all
   simulations.
4. **Post-processing and reporting** – The resulting interval averages, error bands, and percentile bands are reassembled into `pandas`
   structures, aligned with the future date grid, and can be rendered to charts or Excel outputs. Optional market index
   simulations go through the same pipeline so forecasts can be plotted alongside the benchmark.

## Understanding the reported statistics

SmartStocks now surfaces three complementary measures of uncertainty for every simulated interval:

- **Standard deviation (`StdDev`)** – The dispersion of simulated prices around the mean. This reflects the volatility implied by the model and stabilises as more simulations are run.
- **Standard error of the mean (`StdError`)** – The uncertainty around the estimated mean price, calculated as `StdDev / sqrt(number of simulations)`. This value tightens as additional simulations are performed.
- **5th and 95th percentiles (`P05`/`P95`)** – Non-parametric bands that capture the tails of the simulated price distribution, highlighting potential downside and upside scenarios without assuming symmetry.

Use the standard deviation to gauge overall volatility, the standard error to understand the precision of the expected-price estimate, and the percentile range to communicate likely bounds to stakeholders.

## Legal notice

The data collection utilities rely on `yfinance`. Yahoo!, Y!Finance, and Yahoo! finance are registered trademarks of Yahoo Inc.
Market data usage is subject to Yahoo!'s terms of service and is intended for personal and educational purposes only.
