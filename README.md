# SmartStocks Computational Toolkit

SmartStocks is now a headless analytics toolkit focused on high performance Monte Carlo simulations for equities. The Python
interface orchestrates data collection and reporting, while the heavy numerical lifting is delegated to a multithreaded C++
backend. Results can be delivered automatically via email so the entire workflow can run unattended.

## Highlights

- **C++ simulation engine** – Monte Carlo simulations, head-and-shoulders pattern detection, and MACD adjustments are executed in
  native code (`cpp/smartstocks_sim.cpp`) for consistent performance across platforms.
- **Python orchestration** – High-level logic for fetching market data, estimating parameters, and preparing reports remains in
  Python for readability and extensibility.
- **Email-ready or CSV-only workflows** – Use `generate_email_report.py` to email forecasts or
  `generate_forecast_csv.py` to simply save the prediction data locally.
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
     --sender reports@example.com \
     --smtp-server smtp.example.com \
     --smtp-port 587 \
     --smtp-username reports@example.com \
     --smtp-password yourpassword
   ```

   A CSV file containing the expected price path and standard deviation will be written to `output/`, and the summary email will be
   sent with the CSV attached. Provide `--no-email` (and omit the email arguments) to skip the SMTP step for local runs.

## Saving forecasts without email

When you only need the CSV output, the lightweight helper avoids any SMTP configuration:

```bash
python generate_forecast_csv.py \
  --ticker AAPL \
  --period 6mo \
  --interval 1d \
  --simulations 500 \
  --sim-time 30 \
  --output-file output/AAPL_forecast.csv
```

Both CLIs share the same simulation parameters and rely exclusively on the C++ backend for numerical work.

## Configuration notes

- Set `--processes` to the number of hardware threads you want the C++ engine to use.
- Provide `--jump-parameter`, `--h-s-window`, and `--incremental-steps` to tune jump detection and technical adjustments.
- To reproducibly rerun simulations, pass `--seed <int>`.
- SMTP credentials can also be provided via the `SMARTSTOCKS_SMTP_PASSWORD` environment variable.

## Legal notice

The data collection utilities rely on `yfinance`. Yahoo!, Y!Finance, and Yahoo! finance are registered trademarks of Yahoo Inc.
Market data usage is subject to Yahoo!'s terms of service and is intended for personal and educational purposes only.
