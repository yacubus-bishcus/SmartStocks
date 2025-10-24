import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.stats import poisson, gamma
from scipy.optimize import minimize
from scipy.special import gammaln
import multiprocessing as mp
import logging
import pandas as pd
from tqdm import tqdm

# MY Modules
from Simulation_Analysis import Simulation_Analysis
from Models import MACD 

logger = logging.getLogger(__name__)

CPP_EXECUTABLE_ENV = "SMARTSTOCKS_CPP_EXEC"
DEFAULT_CPP_EXECUTABLE = Path(__file__).resolve().parent / "cpp" / "build" / "smartstocks_sim"

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

    def calculate_initial_condition(self, data_keys):
        processed_data = self.apply_function(self.data)
        param1, param2 = processed_data[data_keys[0]], processed_data[data_keys[1]]
        self.initial_condition = param1[-1]
        self.jump_threshold = self.jump_threshold_parameter * np.std(param1)
        self.jumps = np.abs(param1[param2 > self.jump_threshold])
        num_jumps = len(self.jumps)
        self.jump_intensity = num_jumps/self.num_days # lambda 


    def apply_function(self, func):
        try:
            result = func(self.data)
            return result
        except Exception as e:
            logger.exception(f"Error occuring while applying function: {e}")
            return None

    def execute_normal_simulation_with_mp(self,
                                          drift,
                                          volatility,
                                          interval_minutes,
                                          average_reduction,
                                          bull,
                                          bear,
                                          min_cap,
                                          max_cap,
                                          incremental_adjustment_steps):
        try:
            config = self._build_cpp_config(drift=drift,
                                            volatility=volatility,
                                            interval_minutes=interval_minutes,
                                            average_reduction=average_reduction,
                                            bull=bull,
                                            bear=bear,
                                            min_cap=min_cap,
                                            max_cap=max_cap,
                                            incremental_adjustment_steps=incremental_adjustment_steps)
            cpp_result = self._run_cpp_simulation(config)
            interval_means = np.array(cpp_result["interval_means"])
            interval_stds = np.array(cpp_result["interval_stds"])
            return interval_means, interval_stds
        except Exception:
            logger.exception("Falling back to Python implementation due to C++ backend error.")
            return self._execute_normal_simulation_python(drift=drift,
                                                          volatility=volatility,
                                                          interval_minutes=interval_minutes,
                                                          average_reduction=average_reduction,
                                                          bull=bull,
                                                          bear=bear,
                                                          min_cap=min_cap,
                                                          max_cap=max_cap,
                                                          incremental_adjustment_steps=incremental_adjustment_steps)

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

    def _build_cpp_config(self,
                          drift,
                          volatility,
                          interval_minutes,
                          average_reduction,
                          bull,
                          bear,
                          min_cap,
                          max_cap,
                          incremental_adjustment_steps):
        if self.initial_condition is None:
            raise ValueError("Initial condition has not been calculated. Call calculate_initial_condition first.")

        if self.jumps is None or self.jump_intensity is None:
            raise ValueError("Jump statistics have not been initialised. Ensure calculate_initial_condition is executed.")

        intervals_per_day = int(24 * 60 / interval_minutes)
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
            "interval_minutes": int(interval_minutes),
            "initial_condition": float(self.initial_condition),
            "drift": float(drift),
            "volatility": float(volatility),
            "average_reduction": float(average_reduction),
            "bull": float(bull),
            "bear": float(bear),
            "min_cap": float(min_cap),
            "max_cap": float(max_cap),
            "incremental_adjustment_steps": int(max(1, incremental_adjustment_steps)),
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

    def _execute_normal_simulation_python(self,
                                          drift,
                                          volatility,
                                          interval_minutes,
                                          average_reduction,
                                          bull,
                                          bear,
                                          min_cap,
                                          max_cap,
                                          incremental_adjustment_steps):
        intervals_per_day = int(24 * 60 / interval_minutes)
        total_intervals = self.sim_time * intervals_per_day
        logger.info(f"Total Intervals to Simulate: {total_intervals}")
        dt = 1 / intervals_per_day
        jump_mean = np.mean(self.jumps) if len(self.jumps) > 0 else 0.
        jump_std = np.std(self.jumps) if len(self.jumps) > 0 else 0.
        simulations = np.zeros((self.num_simulations, total_intervals))
        initial_condition = self.initial_condition
        jump_intensity = self.jump_intensity
        logger.info(f"Jump Intensity: {jump_intensity}")
        bull_increment = bull / incremental_adjustment_steps
        bear_increment = bear / incremental_adjustment_steps
        average_reduction_increment = average_reduction / incremental_adjustment_steps

        for sim in tqdm(range(self.num_simulations), desc="Trials", mininterval=120, maxinterval=3600):
            data = [initial_condition]
            pending_bull_adjustments = 0
            pending_bear_adjustments = 0
            pending_reduction_adjustments = 0
            for _ in range(total_intervals):
                normal_shock = np.random.normal(drift * dt, volatility * np.sqrt(dt))
                num_jumps = np.random.poisson(jump_intensity * dt)
                jump_shock = np.sum(np.random.normal(jump_mean, jump_std, num_jumps))
                shock = normal_shock + jump_shock
                next_result = data[-1] * np.exp(shock)
                next_result = max(min(next_result, max_cap), min_cap)
                data.append(next_result)

            patterns, _ = Simulation_Analysis.detect_head_and_shoulders(data)
            for i in range(1, len(data)):
                if pending_reduction_adjustments > 0:
                    data[i] *= (1 - average_reduction_increment)
                    pending_reduction_adjustments -= 1
                if patterns[i] == 1:
                    pending_reduction_adjustments = incremental_adjustment_steps

            data_series = pd.Series(data)
            macd_line, signal_line, _ = MACD.calculate_model(data_series)

            for i in range(1, len(data)):
                if pending_bull_adjustments > 0:
                    data[i] *= (1 + bull_increment)
                    pending_bull_adjustments -= 1
                if pending_bear_adjustments > 0:
                    data[i] *= (1 - bear_increment)
                    pending_bear_adjustments -= 1

                if macd_line[i] > signal_line[i] and macd_line[i-1] <= signal_line[i-1]:
                    pending_bull_adjustments = incremental_adjustment_steps
                elif macd_line[i] < signal_line[i] and macd_line[i-1] >= signal_line[i-1]:
                    pending_bear_adjustments = incremental_adjustment_steps

            simulations[sim, :] = data[1:]

        interval_means = np.mean(simulations, axis=0)
        interval_stds = np.std(simulations, axis=0)

        return interval_means, interval_stds

    def execute_poisson_gamma_simulation_with_mp(self):
        initial_condition = self.initial_condition
        sim_time = self.sim_time
        num_simulations = self.num_simulations
        processes = self.processes
        jumps = self.jumps

        jump_mean = np.mean(jumps) if len(jumps) > 0 else 0.
        jump_std = np.std(jumps) if len(jumps) > 0 else 0.
        jump_var = np.var(jumps) if len(jumps) > 0 else 0.

        if jump_mean != 0. and jump_std != 0. and jump_var != 0:
            initial_guess_beta = jump_var / jump_mean
            initial_guess_alpha = (jump_mean / jump_var)**2.
            if initial_guess_alpha == 0:
                initial_guess_alpha = 1.
            if initial_guess_beta == 0:
                initial_guess_beta = 0.2
        else:
            initial_guess_alpha = 1.
            initial_guess_beta = 0.2

        initial_guess = [initial_guess_alpha, initial_guess_beta]
        result = minimize(self.gamma_log_likelihood, initial_guess, args=(jumps,), method='L-BFGS-B', bounds=((0.01, None), (0.01, None)))
        alpha, beta = result.x
        # Initialize Poisson and Gamma distributions
        poisson_dist = poisson(mu=jump_mean)
        if beta <= 0:
            logger.warning("Beta must be greater than 0. Arbitrarily setting beta to 0.2.")
            beta = 0.2

        gamma_dist = gamma(a=alpha, scale=1. / beta)

        simulations = np.zeros((self.num_simulations, self.sim_time))

        pool = mp.Pool(processes=processes)
        chunk_size = num_simulations // processes
        chunks = [(simulations[i:i + chunk_size], sim_time, initial_condition, jump_mean, jump_std, poisson_dist, gamma_dist)
                  for i in range(0, num_simulations, chunk_size)]

        results = pool.starmap(self.poisson_simulation_worker, chunks)
        pool.close()
        pool.join()

        # Assemble results into the simulations array
        for i, result in enumerate(results):
            simulations[i*chunk_size:(i+1)*chunk_size, :] = result

        return simulations

    def execute_poisson_gamma_simulation(self, initial_guess_alpha, initial_guess_beta):
        jump_mean = np.mean(self.jumps) if len(self.jumps) > 0 else 0.
        jump_std = np.std(self.jumps) if len(self.jumps) > 0 else 0.
        jump_var = np.var(self.jumps) if len(self.jumps) > 0 else 0.


        if initial_guess_alpha == 0:
            initial_guess_alpha = 1.
        if initial_guess_beta == 0:
            initial_guess_beta = 0.2


        initial_guess = [initial_guess_alpha, initial_guess_beta]
        alpha = initial_guess_alpha
        beta = initial_guess_beta
        #result = minimize(self.gamma_log_likelihood, initial_guess, args=(self.jumps,), method='L-BFGS-B', bounds=((0.01, None), (0.01, None)))
        #alpha, beta = result.x
        logger.info(f"Alpha result: {alpha} Beta result: {beta}")
        # Initialize Poisson and Gamma distributions
        poisson_dist = poisson(mu=jump_mean)

        if beta <= 0:
            logger.warning("Beta must be greater than 0. Arbitrarily setting beta to 0.2.")
            beta = 0.2

        gamma_dist = gamma(a=alpha, scale=1. / beta)

        simulations = np.zeros((self.num_simulations, self.sim_time))

        for sim in range(self.num_simulations):
            data = [self.initial_condition]
            for t in range(1, self.sim_time + 1):
                poisson_rv = poisson_dist.rvs()
                gamma_rv = gamma_dist.rvs()
                result = poisson_rv * gamma_rv - 1.
                jump = np.random.normal(jump_mean, jump_std)
                shock = result + jump
                next_result = data[-1] * (1 + shock)
                data.append(next_result)

            simulations[sim, :] = data[1:]

        return simulations

    @staticmethod
    def poisson_simulation_worker(simulations_chunk, sim_time, initial_condition, jump_mean, jump_std, poisson_dist, gamma_dist):
        for sim in range(simulations_chunk.shape[0]):
            data = [initial_condition]
            for _ in range(sim_time):
                poisson_rv = poisson_dist.rvs()
                gamma_rv = gamma_dist.rvs()
                result = poisson_rv * gamma_rv - 1.
                jump = np.random.normal(jump_mean, jump_std)
                shock = result + jump
                next_result = data[-1] * (1 + shock)
                data.append(next_result)
            simulations_chunk[sim, :] = data[1:]

        return simulations_chunk

    def gamma_log_likelihood(self, params, jumps):
        alpha, beta = params
        if beta <= 0 :
            beta = 0.2
            logger.warning("Beta was found to be less than or equal to zero, setting arbitrarily to 0.2")

        log_likelihood = -alpha * np.log(beta) + (alpha - 1) * np.sum(np.log(jumps)) - np.sum(jumps / beta) - len(jumps) * gammaln(alpha)
        return -log_likelihood # minimize negative log-likelihood
