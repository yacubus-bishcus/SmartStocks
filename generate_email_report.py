"""Command line entry point to generate SmartStocks reports and email them."""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Iterable, Optional

from email_reporter import SMTPSettings, send_email_report
from report_generation import (ForecastConfig, generate_forecast,
                               write_forecast_csv)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SmartStocks Monte Carlo report and email it.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol to analyse.")
    parser.add_argument("--period", default="6mo", help="Historical period to download (yfinance format).")
    parser.add_argument("--interval", default="1d", help="Historical data interval (yfinance format).")
    parser.add_argument("--simulations", type=int, default=500, help="Number of Monte Carlo trials to run.")
    parser.add_argument("--sim-time", type=int, default=30, help="Number of future days to simulate.")
    parser.add_argument("--processes", type=int, default=os.cpu_count() or 1, help="Desired number of CPU processes for the C++ backend.")
    parser.add_argument("--jump-parameter", type=float, default=1.0, help="Standard deviation multiplier that defines price jumps.")
    parser.add_argument("--h-s-window", type=int, default=20, help="Head-and-shoulders detection window.")
    parser.add_argument("--incremental-steps", type=int, default=5, help="Intervals over which price adjustments are applied.")
    parser.add_argument("--use-log-returns", action="store_true", help="Use log returns when estimating drift and volatility.")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Directory to store generated report files.")
    parser.add_argument("--output-file", type=Path, help="Explicit CSV output path. Overrides --output-dir.")
    parser.add_argument("--recipient", action="append", help="Email recipient. Specify multiple times for more recipients.")
    parser.add_argument("--sender", help="Email address used as the sender.")
    parser.add_argument("--smtp-server", help="SMTP server hostname.")
    parser.add_argument("--smtp-port", type=int, help="SMTP server port. Defaults to MAIL_PORT environment variable")
    parser.add_argument("--smtp-username", help="SMTP username. Defaults to the sender address.")
    parser.add_argument("--smtp-password", help="SMTP password. Defaults to MAIL_PASSWORD environment variable.")
    parser.add_argument("--disable-tls", action="store_true", help="Disable STARTTLS when connecting to SMTP. Defaults to MAIL_USE_TLS environment variable.")
    parser.add_argument("--email-subject", default="SmartStocks Monte Carlo Report", help="Custom email subject.")
    parser.add_argument("--no-email", action="store_true", help="Generate report files without sending an email.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--seed", type=int, help="Seed used for the Monte Carlo generator.")
    return parser.parse_args()


def _determine_output_path(args: argparse.Namespace) -> Path:
    if args.output_file is not None:
        return args.output_file
    return args.output_dir / f"{args.ticker}_forecast.csv"

def _normalise_recipients(recipients: Optional[Iterable[str]]) -> list[str]:
    return list(recipients or [])

def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    forecast_config = ForecastConfig(ticker=args.ticker,
                                     period=args.period,
                                     interval=args.interval,
                                     simulations=args.simulations,
                                     sim_time=args.sim_time,
                                     processes=args.processes,
                                     jump_parameter=args.jump_parameter,
                                     h_s_window=args.h_s_window,
                                     incremental_steps=args.incremental_steps,
                                     use_log_returns=args.use_log_returns,
                                     seed=getattr(args, "seed", None))

    result = generate_forecast(forecast_config)

    output_path = _determine_output_path(args)
    write_forecast_csv(result, output_path)
    logger.info("%s", result.summary.strip())

    if args.no_email:
        logger.info("Email sending skipped (--no-email provided).");
        return

    recipients = _normalise_recipients(args.recipient)
    password = args.smtp_password or os.getenv("MAIL_PASSWORD")
    smtp_port = args.smtp_port or os.getenv("MAIL_PORT")
    use_tls = args.disable_tls or os.getenv("MAIL_USE_TLS")
    smtp_settings = SMTPSettings(host=args.smtp_server,
                                 port=args.smtp_port,
                                 username=args.smtp_username or args.sender,
                                 password=password,
                                 use_tls=not args.disable_tls,
                                 sender=args.sender)

    if smtp_settings.use_tls and not password:
        logger.warning("No SMTP password supplied; attempting to send without authentication.")

    send_email_report(settings=smtp_settings,
                      subject=args.email_subject,
                      body=result.summary,
                      recipients=recipients,
                      attachments=[output_path])


if __name__ == "__main__":
    main()
