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
        self.jump_threshold_parameter = jump_param
        self.jumps = None
        self.jump_intensity = None 
        self.num_days = history_time 

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
                                          max_cap):
        # Multiprocessing only works with static methods/properties 
        macd = MACD()
        initial_condition = self.initial_condition
        sim_time = self.sim_time
        num_simulations = self.num_simulations
        processes = self.processes
        jumps = self.jumps 
        jump_intensity = self.jump_intensity
         # Define the number of intervals per day
        intervals_per_day = int(24 * 60 / interval_minutes)
        total_intervals = sim_time * intervals_per_day
        # assign the small time difference 
        dt = 1 / intervals_per_day
        # Calculate jump mean and std
        jump_mean = np.mean(jumps) if len(jumps) > 0 else 0.
        jump_std = np.std(jumps) if len(jumps) > 0 else 0.
        
        # Initialize the simulations array
        simulations_chunk = np.zeros((self.num_simulations, total_intervals))
        pool = mp.Pool(processes=processes)
        chunk_size = (num_simulations + processes - 1) // processes  # Ensure all chunks are the same size
        # Create a list of arguments for each chunk
        chunks = [(min(chunk_size, num_simulations - i * chunk_size), jump_intensity, dt, total_intervals, initial_condition, drift, volatility, jump_mean, jump_std, average_reduction, bull, bear, min_cap, max_cap)
                  for i in range(processes)]
        results = pool.starmap(self.normal_simulation_worker, chunks)
        pool.close()
        pool.join()

        # Assemble results into the simulations array
        start_index = 0
        for result in results:
            end_index = start_index + result.shape[0]
            simulations_chunk[start_index:end_index, :] = result
            start_index = end_index

        # Calculate mean and standard deviation for each interval
        interval_means = np.mean(simulations_chunk, axis=0)
        interval_stds = np.std(simulations_chunk, axis=0)

        return interval_means, interval_stds


    @staticmethod
    def normal_simulation_worker(chunk_size, 
                                 jump_intensity, 
                                 dt, 
                                 total_intervals, 
                                 initial_condition, 
                                 drift, volatility, 
                                 jump_mean, 
                                 jump_std, 
                                 average_reduction, 
                                 bull, 
                                 bear, 
                                 min_cap, 
                                 max_cap):
        simulations_chunk = np.zeros((chunk_size, total_intervals))
        for sim in tqdm(range(chunk_size), desc="Trials",mininterval=120, maxinterval=3600):
            data = [initial_condition]
            for _ in range(total_intervals):
                # Standard GBM component
                normal_shock = np.random.normal(drift * dt, volatility * np.sqrt(dt))
                
                # Jump component
                num_jumps = np.random.poisson(jump_intensity * dt)
                jump_shock = np.sum(np.random.normal(jump_mean, jump_std, num_jumps))
                
                # Combine both components
                shock = normal_shock + jump_shock
                next_result = data[-1] * np.exp(shock)
                next_result = max(min(next_result, max_cap), min_cap)
                data.append(next_result)
            # HEAD AND SHOULDERS ADJUSTMENT     
            # Detect Head and Shoulders pattern in the simulated data
            patterns, _ = Simulation_Analysis.detect_head_and_shoulders(data)
            # Adjust prices based on detected patterns
            for i in range(1, len(data)):
                if patterns[i] == 1:
                    data[i] *= (1 - average_reduction) # Adjust based on average reduction
            # MACD ADJUSTMENT 
            # Convert data to pandas Series for MACD calculation
            data_series = pd.Series(data)
            macd_line, signal_line, _ = MACD.calculate_model(data_series)

            # Adjust prices based on MACD signals
            for i in range(1, len(data)):
                if macd_line[i] > signal_line[i] and macd_line[i-1] <= signal_line[i-1]:
                    # Bullish MACD crossover
                    data[i] *= (1 + bull)
                elif macd_line[i] < signal_line[i] and macd_line[i-1] >= signal_line[i-1]:
                    # Bearish MACD crossover
                    data[i] *= (1 - bear)
            
            simulations_chunk[sim, :] = data[1:]


        return simulations_chunk

    def execute_normal_simulation(self, 
                                  drift, 
                                  volatility, 
                                  interval_minutes, 
                                  average_reduction, 
                                  bull, 
                                  bear, 
                                  min_cap, 
                                  max_cap):
        # Define the number of intervals per day
        intervals_per_day = int(24 * 60 / interval_minutes)
        total_intervals = self.sim_time * intervals_per_day
        # assign the small time difference 
        dt = 1 / intervals_per_day
        # Calculate jump mean and std
        jump_mean = np.mean(self.jumps) if len(self.jumps) > 0 else 0.
        jump_std = np.std(self.jumps) if len(self.jumps) > 0 else 0.
        # Initialize the simulations array
        simulations = np.zeros((self.num_simulations, total_intervals))
        # for debugging easier to work with local variables 
        initial_condition = self.initial_condition 

        for sim in tqdm(range(self.num_simulations), desc="Trials", mininterval=120, maxinterval=3600):
            data = [initial_condition]
            for _ in range(total_intervals):
                # Standard GBM component
                normal_shock = np.random.normal(drift * dt, volatility * np.sqrt(dt))
                
                # Jump component
                num_jumps = np.random.poisson(self.jump_intensity * dt)
                jump_shock = np.sum(np.random.normal(jump_mean, jump_std, num_jumps))
                
                # Combine both components
                shock = normal_shock + jump_shock
                next_result = data[-1] * np.exp(shock)
                # Apply min and max cap
                next_result = max(min(next_result, max_cap), min_cap)
                data.append(next_result)
            # HEAD AND SHOULDERS ADJUSTMENT     
            # Detect Head and Shoulders pattern in the simulated data
            patterns, _ = Simulation_Analysis.detect_head_and_shoulders(data)
            # Adjust prices based on detected patterns
            for i in range(1, len(data)):
                if patterns[i] == 1:
                    data[i] *= (1 - average_reduction) # Adjust based on average reduction
            # MACD ADJUSTMENT 
            # Convert data to pandas Series for MACD calculation
            data_series = pd.Series(data)
            macd_line, signal_line, _ = MACD.calculate_model(data_series)

            # Adjust prices based on MACD signals
            for i in range(1, len(data)):
                if macd_line[i] > signal_line[i] and macd_line[i-1] <= signal_line[i-1]:
                    # Bullish MACD crossover
                    data[i] *= (1 + bull)
                elif macd_line[i] < signal_line[i] and macd_line[i-1] >= signal_line[i-1]:
                    # Bearish MACD crossover
                    data[i] *= (1 - bear)
            
            simulations[sim, :] = data[1:]
        # Calculate mean and standard deviation for each interval
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
