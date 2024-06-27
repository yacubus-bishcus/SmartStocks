import numpy as np
from scipy.interpolate import interp1d
import pandas as pd 
import pkg_resources
import logging
#import odfpy 

logger = logging.getLogger(__name__)

class SmartStocksClock:
    def __init__(self):
        pass 

    def __del__(self):
        pass 
    
    @staticmethod
    def guess_etc(processors, stocks, sim_stocks, trials, sim_time, model_interval, report):
        if report:
            stock_time = 10*stocks # takes about 10 seconds per stock for report 
        else:
            stock_time = 2*stocks # takes about two seconds per stock 

        filepath = pkg_resources.resource_filename('data', 'Runtime.ods')
        sheet_name = str(processors) +"Processor"
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name)
        except:
            sheet_name = "2Processor"
            try:
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                df['Run Time (s)'] = df['Run Time (s)']*(processors/2.)
            except Exception as e:
                logger.error(f"Could not find {filepath} Error: {e}")
                return 
            
        trial_time = SmartStocksClock.interpolate_trials(df['Trials'], df['Run Time (s)'], trials)
        interval_factor = 1.
        if model_interval == "1m":
            interval_factor = 15.
        elif model_interval == "5m":
            interval_factor = 3.
        elif model_interval == "30m":
            interval_factor = 0.5
        elif model_interval == "1h" or model_interval == "60m":
            interval_factor = 0.25
        elif model_interval == "90m":
            interval_factor = 15./90.
        elif model_interval == "1d":
            interval_factor = 15./(60.*24)

        total_time = round((stock_time + trial_time)*interval_factor*sim_stocks*sim_time, 3)
        logger.info(f"Estimated Completion Time: {total_time} seconds...")

    @staticmethod
    def interpolate_trials(trials_data, runtime_data, trials):
        x = np.log10(trials_data)
        y = runtime_data 

        # Create an interpolation function using the transformed x data
        function = interp1d(x, y, kind='linear', fill_value="extrapolate")
        x_new = np.log10(trials)
        runtime = function(x_new)

        return runtime 