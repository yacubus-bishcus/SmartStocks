import json
import os
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
    def __init__(self, data, num_simulations, sim_time, history_time, processes=1, jump_param=1., apply_function=None):
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

    def __del__(self):
        pass

    """ Calculating the intial condition allows for two parameters to be set to
    'fix' the data according to your simulation the function to set your
    paramaters is a method in your own code.
    jump_threshold_parameter := The standard deviations that the user qualifies as a "Jump". 
    jumps is 
    """

    def calculate_initial_condition(self, data_keys: Iterable[str]) -> None:
        processed_data = self.apply_function(self.data)
        param1, param2 = processed_data[data_keys[0]], processed_data[data_keys[1]]
        self.initial_condition = param1[-1]
        self.jump_threshold = self.jump_threshold_parameter * np.std(param1)
        self.jumps = np.abs(param1[param2 > self.jump_threshold])
        num_jumps = len(self.jumps)
        self.jump_intensity = num_jumps / self.num_days  # lambda


    def apply_function(self, func):
        try:
            result = func(self.data)
            return result
        except Exception as e:
            logger.exception(f"Error occuring while applying function: {e}")
            return None

    def execute_normal_simulation_with_mp(self,
                                          drift: float,
                                          volatility: float,
                                          interval_minutes: int,
                                          average_reduction: float,
                                          bull: float,
                                          bear: float,
                                          min_cap: float,
                                          max_cap: float,
                                          incremental_adjustment_steps: int) -> Tuple[np.ndarray, np.ndarray]:
        """Execute the Monte Carlo simulation through the C++ backend."""

        config = SimulationConfig(drift=float(drift),
                                  volatility=float(volatility),
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
                return json.load(result_file)

    def _build_cpp_config(self, config: SimulationConfig) -> Dict[str, float]:
        if self.initial_condition is None:
            raise ValueError("Initial condition has not been calculated. Call calculate_initial_condition first.")

        if self.jumps is None or self.jump_intensity is None:
            raise ValueError("Jump statistics have not been initialised. Ensure calculate_initial_condition is executed.")

        intervals_per_day = int(24 * 60 / config.interval_minutes)
        total_intervals = self.sim_time * intervals_per_day
        logger.info("Total Intervals to Simulate: %s", total_intervals)
        logger.info("Jump Intensity: %s", self.jump_intensity)

        jump_mean = float(np.mean(self.jumps)) if len(self.jumps) > 0 else 0.0
        jump_std = float(np.std(self.jumps)) if len(self.jumps) > 0 else 0.0

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
                                  drift,
                                  volatility,
                                  interval_minutes,
                                  average_reduction,
                                  bull,
                                  bear,
                                  min_cap,
                                  max_cap,
                                  incremental_adjustment_steps):
        return self.execute_normal_simulation_with_mp(drift=drift,
                                                      volatility=volatility,
                                                      interval_minutes=interval_minutes,
                                                      average_reduction=average_reduction,
                                                      bull=bull,
                                                      bear=bear,
                                                      min_cap=min_cap,
                                                      max_cap=max_cap,
                                                      incremental_adjustment_steps=incremental_adjustment_steps)

    
    
    
    
    