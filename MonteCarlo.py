import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
import logging

# MY Modules
from Simulation_Analysis import Simulation_Analysis

logger = logging.getLogger(__name__)

CPP_EXECUTABLE_ENV = "SMARTSTOCKS_CPP_EXEC"
DEFAULT_CPP_EXECUTABLE = Path(__file__).resolve().parent / "cpp" / "build" / "smartstocks_sim"


@dataclass(frozen=True)
class SimulationConfig:
    """Typed container describing a single Monte Carlo request."""

    drift: float
    volatility: float
    interval_minutes: int
    average_reduction: float
    bull: float
    bear: float
    min_cap: float
    max_cap: float
    incremental_adjustment_steps: int


class MonteCarlo(Simulation_Analysis):
    def __init__(self,
                 data,
                 num_simulations,
                 sim_time,
                 history_time,
                 processes=1,
                 jump_param=1.,
                 apply_function=None,
                 use_log_returns=True,
                 volatility_lookback=20):
        super().__init__()
        self.data = data
        self.num_simulations = num_simulations
        self.sim_time = sim_time
        self.processes = processes
        self.apply_function = apply_function
        self.initial_condition = None
        self.jump_threshold = None
        self.jump_threshold_parameter = jump_param # amount in standard deviations that the user qualifies as a "jump"
        self.jumps = None
        self.jump_intensity = None
        self.num_days = history_time # this is the model_period typically ran at 30 days
        self.use_log_returns = use_log_returns
        self.volatility_lookback = max(1, int(volatility_lookback))
        self.calibrated_drift = None
        self.calibrated_volatility = None
        self.volatility_features = {}
        self.calibrated_jump_mean = 0.0
        self.calibrated_jump_std = 0.0
        self.jump_size_rate = 0.0

    def __del__(self):
        pass

    """ Calculating the intial condition allows for two parameters to be set to
    'fix' the data according to your simulation the function to set your
    paramaters is a method in your own code.
    jump_threshold_parameter := The standard deviations that the user qualifies as a "Jump". 
    jumps is 
    """

    def calculate_initial_condition(self, data_keys: Iterable[str]) -> None:
        if self.apply_function is None:
            raise ValueError("No preprocessing function provided for Monte Carlo data preparation.")

        processed_data = self.apply_function(self.data)
        if processed_data is None:
            raise ValueError("Preprocessing function did not return any data for calibration.")

        for key in data_keys:
            if key not in processed_data:
                raise KeyError(f"Required key '{key}' missing from preprocessing output.")

        param1, param2 = processed_data[data_keys[0]], processed_data[data_keys[1]]

        if hasattr(param1, "iloc"):
            last_value = param1.iloc[-1]
        else:
            last_value = param1[-1]
        self.initial_condition = float(last_value)

        self.jump_threshold = self.jump_threshold_parameter * np.std(param2)

        jump_mask = np.abs(param2) > self.jump_threshold
        self.jumps = np.asarray(param2[jump_mask])
        num_jumps = len(self.jumps)
        self.jump_intensity = num_jumps / self.num_days if self.num_days else 0.0  # lambda

        self.calibrated_jump_mean, self.calibrated_jump_std, self.jump_size_rate = self._calibrate_jump_distribution(self.jumps)
        logger.info("Calibrated jump frequency: %s events/day", self.jump_intensity)
        logger.info("Calibrated jump magnitude (mean/std): %s / %s", self.calibrated_jump_mean, self.calibrated_jump_std)

        drift, volatility = self.calculate_drift_and_volatility(param1, self.use_log_returns)
        self.calibrated_drift = float(drift)
        self.calibrated_volatility = float(volatility)
        logger.info("Calibrated drift: %s", self.calibrated_drift)
        logger.info("Calibrated volatility from returns: %s", self.calibrated_volatility)

        rolling_volatility = processed_data.get("rolling_volatility")
        volatility_regime = processed_data.get("volatility_regime")
        if rolling_volatility is not None:
            self.calibrated_volatility = self._current_volatility_from_cluster(rolling_volatility)
            logger.info("Adjusted volatility using recent clustering: %s", self.calibrated_volatility)
        self.volatility_features = {
            "rolling_volatility": rolling_volatility,
            "volatility_regime": volatility_regime,
        }


    def apply_function(self, func):
        try:
            result = func(self.data)
            return result
        except Exception as e:
            logger.exception(f"Error occuring while applying function: {e}")
            return None

    @staticmethod
    def _calibrate_jump_distribution(jump_returns: np.ndarray) -> Tuple[float, float, float]:
        if jump_returns is None or len(jump_returns) == 0:
            return 0.0, 0.0, 0.0

        jump_magnitudes = np.abs(jump_returns)
        mean_jump_size = float(np.mean(jump_magnitudes))
        std_jump_size = float(np.std(jump_magnitudes, ddof=1)) if len(jump_magnitudes) > 1 else 0.0
        rate = 1.0 / mean_jump_size if mean_jump_size > 0 else 0.0
        return mean_jump_size, std_jump_size, rate

    def _current_volatility_from_cluster(self, rolling_volatility) -> float:
        if rolling_volatility is None:
            return self.calibrated_volatility if self.calibrated_volatility is not None else 0.0

        try:
            import pandas as pd
            if not hasattr(rolling_volatility, "tail"):
                rolling_volatility = pd.Series(rolling_volatility)
        except Exception:
            rolling_volatility = np.asarray(rolling_volatility)
            recent_vol = float(np.nanmean(rolling_volatility[-self.volatility_lookback:]))
            return 0.0 if np.isnan(recent_vol) else recent_vol

        try:
            recent_window = rolling_volatility.tail(self.volatility_lookback)
            recent_vol = float(np.nanmean(recent_window))
        except Exception:
            recent_vol = float(np.nanmean(rolling_volatility))
        if np.isnan(recent_vol) or recent_vol == 0:
            recent_vol = float(np.nanstd(rolling_volatility))
        if np.isnan(recent_vol):
            recent_vol = 0.0
        return recent_vol

    def execute_normal_simulation_with_mp(self,
                                          interval_minutes: int,
                                          average_reduction: float,
                                          bull: float,
                                          bear: float,
                                          min_cap: float,
                                          max_cap: float,
                                          incremental_adjustment_steps: int,
                                          drift: float = None,
                                          volatility: float = None) -> Tuple[np.ndarray, np.ndarray]:
        """Execute the Monte Carlo simulation through the C++ backend."""

        if interval_minutes is None:
            raise ValueError("interval_minutes must be provided for simulation execution.")

        calibrated_drift = self.calibrated_drift if drift is None else drift
        calibrated_volatility = self.calibrated_volatility if volatility is None else volatility

        config = SimulationConfig(drift=float(calibrated_drift),
                                  volatility=float(calibrated_volatility),
                                  interval_minutes=int(interval_minutes),
                                  average_reduction=float(average_reduction),
                                  bull=float(bull),
                                  bear=float(bear),
                                  min_cap=float(min_cap),
                                  max_cap=float(max_cap),
                                  incremental_adjustment_steps=int(max(1, incremental_adjustment_steps)))
        cpp_config = self._build_cpp_config(config)
        cpp_result = self._run_cpp_simulation(cpp_config)
        interval_means = np.array(cpp_result["interval_means"])
        interval_stds = np.array(cpp_result["interval_stds"])
        return interval_means, interval_stds

    def _resolve_cpp_executable(self):
        override = os.environ.get(CPP_EXECUTABLE_ENV)
        if override:
            return Path(override)
        return DEFAULT_CPP_EXECUTABLE

    @staticmethod
    def _format_cpp_value(value):
        if isinstance(value, float):
            return f"{value:.15g}"
        return str(int(value)) if isinstance(value, (np.integer, int)) else str(value)

    @staticmethod
    def _sanitize_backend_payload(payload: str) -> str:
        """Replace non-standard JSON tokens with ``null`` so we can parse the payload."""

        # JSON produced by the C++ backend historically contained ``NaN``/``inf`` tokens when
        # numerical instabilities occurred. The simulator now tries to avoid this, but keep a
        # defensive parser in Python to preserve compatibility with older binaries and partially
        # written files. The regex matches bare tokens (i.e. not inside identifiers) so legitimate
        # substrings are untouched.
        non_finite_pattern = re.compile(r"(?<![0-9A-Za-z_])(?:NaN|nan|Infinity|-Infinity|Inf|-Inf|inf|-inf)(?![0-9A-Za-z_])")
        return non_finite_pattern.sub("null", payload)

    def _run_cpp_simulation(self, config):
        executable_path = self._resolve_cpp_executable()
        if not executable_path.exists():
            raise FileNotFoundError(
                f"C++ simulation executable not found at {executable_path}. Build it with CMake before running simulations.")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "simulation.cfg"
            output_path = Path(tmpdir) / "results.json"
            with config_path.open("w", encoding="utf-8") as cfg:
                for key, value in config.items():
                    cfg.write(f"{key}={self._format_cpp_value(value)}\n")

            try:
                completed = subprocess.run([str(executable_path),
                                            str(config_path),
                                            str(output_path)],
                                           capture_output=True,
                                           check=True,
                                           text=True)
            except subprocess.CalledProcessError as error:
                logger.error("C++ backend failed with stderr: %s", error.stderr.strip())
                raise

            logger.debug("C++ backend stdout: %s", completed.stdout.strip())

            with output_path.open("r", encoding="utf-8") as result_file:
                raw_payload = result_file.read()

            try:
                return json.loads(raw_payload)
            except json.JSONDecodeError as error:
                sanitized_payload = self._sanitize_backend_payload(raw_payload)
                if sanitized_payload == raw_payload:
                    logger.error("Unable to parse C++ backend output even after sanitisation: %s", error)
                    raise

                logger.warning("C++ backend output contained non-finite values; replaced with null before parsing.")
                return json.loads(sanitized_payload)

    def _build_cpp_config(self, config: SimulationConfig) -> Dict[str, float]:
        if self.initial_condition is None:
            raise ValueError("Initial condition has not been calculated. Call calculate_initial_condition first.")

        if self.jumps is None or self.jump_intensity is None:
            raise ValueError("Jump statistics have not been initialised. Ensure calculate_initial_condition is executed.")

        if self.calibrated_drift is None or self.calibrated_volatility is None:
            raise ValueError("Drift and volatility have not been calibrated. Run calculate_initial_condition first.")

        intervals_per_day = int(24 * 60 / config.interval_minutes)
        total_intervals = self.sim_time * intervals_per_day
        logger.info("Total Intervals to Simulate: %s", total_intervals)
        logger.info("Jump Intensity: %s", self.jump_intensity)

        jump_mean = float(self.calibrated_jump_mean)
        jump_std = float(self.calibrated_jump_std)

        threads = self.processes if self.processes and self.processes > 0 else os.cpu_count() or 1
        window_size = getattr(self, "head_shoulders_window", 20)

        config = {
            "num_simulations": int(self.num_simulations),
            "sim_time": int(self.sim_time),
            "interval_minutes": int(config.interval_minutes),
            "initial_condition": float(self.initial_condition),
            "drift": config.drift,
            "volatility": config.volatility,
            "average_reduction": config.average_reduction,
            "bull": config.bull,
            "bear": config.bear,
            "min_cap": config.min_cap,
            "max_cap": config.max_cap,
            "incremental_adjustment_steps": int(max(1, config.incremental_adjustment_steps)),
            "jump_mean": float(jump_mean),
            "jump_std": float(jump_std),
            "jump_intensity": float(self.jump_intensity),
            "threads": int(max(1, threads)),
            "window_size": int(max(1, window_size)),
            "macd_short_window": 12,
            "macd_long_window": 26,
            "macd_signal_window": 9,
        }

        seed = getattr(self, "seed", None)
        if seed is not None:
            config["seed"] = int(seed)

        return config

    def execute_normal_simulation(self,
                                  drift=None,
                                  volatility=None,
                                  interval_minutes=None,
                                  average_reduction=None,
                                  bull=None,
                                  bear=None,
                                  min_cap=None,
                                  max_cap=None,
                                  incremental_adjustment_steps=None):
        return self.execute_normal_simulation_with_mp(drift=drift,
                                                      volatility=volatility,
                                                      interval_minutes=interval_minutes,
                                                      average_reduction=average_reduction,
                                                      bull=bull,
                                                      bear=bear,
                                                      min_cap=min_cap,
                                                      max_cap=max_cap,
                                                      incremental_adjustment_steps=incremental_adjustment_steps)

    
    
    
    
    