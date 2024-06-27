import argparse
import sys 
import logging 
from colorama import Fore, Style 
import multiprocessing as mp 

logger = logging.getLogger(__name__)

class ArgsNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, item):
        return self.__dict__.get(item, None)

    def __setattr__(self, key, value):
        self.__dict__[key] = value

class ArgsParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Argument Parser for Smart Stocks')
        self.args = None
        self.defaults = {}
        self._setup_parser()
    
    def _setup_parser(self):
        # Add arguments
        self.parser.add_argument('-c',                    action='store_true', help='Display individual ticker current day change', required=False, default=False)
        self.parser.add_argument('--c_50',                action='store_true', help='Display individual ticker 50 day change', required=False, default=False)
        self.parser.add_argument('--c_200',               action='store_true', help='Display individual ticker 200 day change', required=False, default=False)
        self.parser.add_argument('--compare_index',       action='store_true', help='Display Daily Change Comparison to Index of Chosing.', required=False, default=False)
        self.parser.add_argument('--compare_index_50',    action='store_true', help='Display 50 Day Change Comparison to Index of Choosing.', required=False, default=False)
        self.parser.add_argument('--compare_index_200',   action='store_true', help='Display 200 Day Change Comparison to Index of Choosing.', required=False, default=False)
        self.parser.add_argument('--compare_50',          action='store_true', help='Display 50 day average comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--compare_200',         action='store_true', help='Display 200 day average comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--compare_Daily',       action='store_true', help='Display daily comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--data',                nargs='+', help='Import Research Ticker Data from list of files. Default is nasdaqlisted.txt and otherlisted.txt', required=False, default=['nasdaqlisted.txt', 'otherlisted.txt'])
        self.parser.add_argument('-d',                    action='store_true', help='Debugging mode for developing', required=False, default=False)
        self.parser.add_argument('-e',                    action='store_true', help='Email Outfile to provided email.', required=False)
        self.parser.add_argument('--h_s_window',          type=int, help='Head and Shoulders Reduction method window size measured in intervals of X. Default=20', required=False, default=20)
        self.parser.add_argument('--import_model_class',  nargs='+', help='Input the class name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--import_model_module', nargs='+', help='Input the module name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--input',               type=str, help='Input File Path to Read Stock Tickers', required=False)
        self.parser.add_argument('--include_history',     action='store_true', help='Include History in Future Plots.', required=False, default=False)
        self.parser.add_argument('--incremental_steps',   type=int, help='Incremental Adjustment steps for simulations responding to MACD and head and shoulder pattern adjustments. Default is 5', required=False, default=5)
        self.parser.add_argument('--index',               type=str, choices=['^GSPC','^DJI','^IXIC'], help='Index to Compare Models. ^GSPC=S&P500, ^DJI=DOWJONES, ^IXIC=NASDAQ Default=^GSPC', required=False, default='^GSPC')
        self.parser.add_argument('--jump_parameter',      type=float, help='Number of standard deviations away from the mean that qualifies as a jump in the stock price. Range 0.001 - 5. Default=1.', required=False, default=1.)
        self.parser.add_argument('--max_price',           type=float, help='Filter Price', required=False, default="10000.00")
        self.parser.add_argument('--models',              nargs='+', help= 'List of Models to use in the calculation. Default is Fifty Day, Two Hundred Day, CAPM, FIBO, MACD, RSI, Stochastic', required=False, default=['Fifty Day','Two Hundred Day','CAPM', 'MACD', 'RSI', 'Stochastic'])
        self.parser.add_argument('--model_interval',      type=str, choices=['1m','2m','5m','15m','30m','60m','90m','1h','1d'], help='Intervals for model calculations and plots. Intraday data cannot extend past 60 days. Default is 1d.', required=False, default='1d')
        self.parser.add_argument('--model_period',        type=str, choices=['1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd'], help='Time Period for model calculation and plots. This is the amount of time prior to today the models will compare to future prices. Default is 1mo.', required=False, default="1mo")
        self.parser.add_argument('--min_price',           type=float, help='Filter Price', required=False, default="1.00")
        self.parser.add_argument('--number_to_highlight', type=int, help='Number of Stocks to Highlight in report. Default is 3.', required=False, default='3')
        self.parser.add_argument('--number_to_research',  type=int, help='Number of Stocks to Research. Default is 10.', required=False, default="10")
        self.parser.add_argument('--output',              type=str, help='Writes data to an output file .txt and as a word document report. Do not include file extension. Apply --as_pdf to output a PDF instead.', required=False, default=None)
        self.parser.add_argument('-p',                    action='store_true', help='Display individual ticker price', required=False, default=False)
        self.parser.add_argument('--price_model',         type=str, choices=['high_low','close_open'], help='Choose between high_low and close_open price processing models for the simulations. Default is close_open', required=False, default='close_open')
        self.parser.add_argument('--processes',           type=int, help='Number of CPUs to use on simulations.', required=False, default = 1)
        self.parser.add_argument('-r',                    action='store_true', help='Display Recommendations for a given stock', required=False, default=False)
        self.parser.add_argument('--report',              action='store_true', help='Create Montly Report', required=False, default=False)
        self.parser.add_argument('--research',            action='store_true', help='Use in conjunction with --report if you want randomly selected stocks to be included in the report. Otherwise --research will execute any of the other provided functions E.g. --compare.', required=False, default=None)
        self.parser.add_argument('--seed',                type=int, help='The Seed used for the simulation for recreation purposes...stock prices do change though.', required=False, default=42)
        self.parser.add_argument('--show_every_nth_errorbar', type=int, help='Show every nth errorbar in futures plot. Default is 0', required=False, default=0)
        self.parser.add_argument('--show_plot',           action='store_true', help='Choose to show plot after a simulation (without report flagged) Default is False.', required=False, default=False)
        self.parser.add_argument('--sim_market',          action='store_true', help='Choose to include market simulations for market comparison. Results may vary. Default is false.', required=False, default=False)
        self.parser.add_argument('--sim_time',            type=int, help='The number of days to calculate future prices. The default is 30.', required=False, default=30)
        self.parser.add_argument('--simulations',         type=int, help='Number of Simulations to run on each stock to predict future price. Default is 0.', required=False, default=0)
        self.parser.add_argument('--simulation_model',    type=str, choices=['gaussian','poisson-gamma'], help='Type of distribution used for simulation can either be Gaussian (normal) or Poisson-Gamma (non-normal). Default is Gaussian', required=False, default='gaussian')
        self.parser.add_argument('--ticker',              type=str, help='Comma-Separated List of tickers for analysis.', required=False, default=None)
        self.parser.add_argument('-u',                    action='store_true', help='Use the Dow Jones stocks in addition to any inputs.', required=False, default=False)
        self.parser.add_argument('--use_log_returns',     action='store_true', help='Use log returns instead of absolute price differences when modeling monte carlo. Default is False.', required=False, default=False)
        self.parser.add_argument('--weights',             type=str, help='Apply weights to models as a dictionary where the key matches the model name and the value is the weight you want to apply to that model. Weights must sum to 1.', required=False, default='{"Fifty Day":0.1, "Two Hundred Day":0.1, "CAPM":0.2, "MACD":0.05, "RSI":0.3, "Stochastic":0.25}')

        self.defaults = {
        'c': False, 'c_50':False, 'c_200':False, 'c_Dow':False, 'c_Nas':False,
        'c_Sap':False, 'c_50_Dow':False, 'c_50_Nas':False, 'c_50_Sap':False,
        'c_200_Dow':False, 'c_200_Nas':False,'c_200_Sap':False

        }

    def parse_args(self, arg_string): # this method is used in the Smart Stocks APP
        args_list = arg_string.split()  # Split the string into list of arguments
        args_dict = vars(self.parser.parse_args(args_list))
        self.args = ArgsNamespace(**args_dict)  # Assuming ArgsNamespace accepts kwargs
        
    def to_lowercase(self, value):
        return value.lower()
    
    def reset_args(self):
        # Reset args to default values
        self.args = ArgsNamespace(**self.defaults)
        return self.args

    def terminal_parse_args(self): # this method is called when using terminal 
        self.args = self.parser.parse_args()
        if(self.validate_models_and_weights()):
            return self.args 
        else:
            return None 
    
    def conduct_smartstock_input_checks(self):
        # Conduct some user input checking
        if len(sys.argv) < 1:
            self.parser.print_help()
            sys.exit(0)

        # If importing own finance model you MUST input a Module name and class name
        if self.args.import_model_class is not None != self.args.import_model_module is None:
            logger.error(Fore.YELLOW + "USER INPUT ERROR: If importing own finance model must input both a module name and a class name." + Style.RESET_ALL)
            return False

        # Number to Research must be at least 1 greater than number to highlight
        if self.args.number_to_research < (self.args.number_to_highlight + 1):
            logger.error(Fore.YELLOW + "USER INPUT ERROR: Number to Research must be at least 1 greater than number to highlight." + Style.RESET_ALL)
            return False

        if self.args.min_price > self.args.max_price:
            logger.error(Fore.YELLOW + f"USER ERROR: Minimum Price {self.args.min_price} Set Higher than Maximum Price {self.args.max_price}." + Style.RESET_ALL)
            return False 
        
        if self.args.processes > mp.cpu_count():
            logger.warning("Requested more processors than you have, defaulting to all processors.")
            self.args.processes = mp.cpu_count()

        return True
    
    # Define the custom type function
    def float_range(self, min_value, max_value):
        def checker(value):
            try:
                f_value = float(value)
            except ValueError:
                raise argparse.ArgumentTypeError(f"{value} is not a valid float")
            
            if f_value < min_value or f_value > max_value:
                raise argparse.ArgumentTypeError(f"{value} is out of range ({min_value} - {max_value})")
            return f_value
        return checker
    
    def validate_models_and_weights(self):
        import json 
        models = self.args.models
        weights_str = str(self.args.weights)
        logger.debug(f"Weights String: {weights_str}")
        try:
            weights_dict = json.loads(weights_str)
            logger.debug(f"Weights Dictionary: {weights_dict}")
        except json.JSONDecodeError:
            logger.error("FATAL ERROR With json.loads(weights)")
            logger.warning("Weights must be input in a specific manner see README.")
            return False 
        # Check if all models have corresponding weights
        for model in models:
            if model not in weights_dict:
                logger.error(f"Model {model} does not have a corresponding weight in the weights dictionary.")
                return False 
        # Check if the sum of weights is 1
        weights = [weights_dict[model] for model in models]
        if not abs(sum(weights) - 1.0) < 1e-6:
            logger.error("Weights must sum to 1.0")
            return False 
        
        self.args.weights = weights_dict 
        
        return True 