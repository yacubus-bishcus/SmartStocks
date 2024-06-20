import argparse


class ArgsNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, item):
        return self.__dict__.get(item, None)

    def __setattr__(self, key, value):
        self.__dict__[key] = value

class ArgsParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Argument Parser for Stock Analysis')
        self.args = None
        self.defaults = {}
        self._setup_parser()

    def _setup_parser(self):
        # Add arguments
        self.parser.add_argument('-a',                   action='store_true', help='Run Code as an application rather than from terminal.', required=False, default=False)
        self.parser.add_argument('-c',                   action='store_true', help='Display individual ticker current day change', required=False, default=False)
        self.parser.add_argument('--c_50',               action='store_true', help='Display individual ticker 50 day change', required=False, default=False)
        self.parser.add_argument('--c_200',              action='store_true', help='Display individual ticker 200 day change', required=False, default=False)
        self.parser.add_argument('--c_Dow',              action='store_true', help='Display daily comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--c_Nas',              action='store_true', help='Display daily comparison to Nasdaq Index', required=False, default=False)
        self.parser.add_argument('--c_Sap',              action='store_true', help='Display daily comparison to S&P500 Index', required=False, default=False)
        self.parser.add_argument('--c_50_Dow',           action='store_true', help='Display 50 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--c_50_Nas',           action='store_true', help='Display 50 day average comparison to Nasdaq Index', required=False, default=False)
        self.parser.add_argument('--c_50_Sap',           action='store_true', help='Display 50 day average comparison to S&P 500 Index', required=False, default=False)
        self.parser.add_argument('--c_200_Dow',          action='store_true', help='Display 200 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--c_200_Nas',          action='store_true', help='Display 200 day average comparison to Nasdaq Index', required=False, default=False)
        self.parser.add_argument('--c_200_Sap',          action='store_true', help='Display 200 day average comparison to S&P 500 Index', required=False, default=False)
        self.parser.add_argument('--co_50',              action='store_true', help='Display 50 day average comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--co_200',             action='store_true', help='Display 200 day average comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--c_Daily',            action='store_true', help='Display daily comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--data',               nargs='+', help='Import Research Ticker Data from list of files. Default is nasdaqlisted.txt and otherlisted.txt', required=False, default=['nasdaqlisted.txt', 'otherlisted.txt'])
        self.parser.add_argument('-d',                   action='store_true', help='Debugging mode for developing', required=False, default=False)
        self.parser.add_argument('-e',                   action='store_true', help='Email Outfile to provided email.', required=False)
        self.parser.add_argument('--import_model_class', nargs='+', help='Input the class name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--import_model_module',nargs='+', help='Input the module name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--input',              type=str, help='Input File Path to Read Stock Tickers', required=False)
        self.parser.add_argument('--index',              type=str, help='Index to Compare Models. Options- s&p,dow,nas. Default=s&p', required=False, default='s&p')
        self.parser.add_argument('--jump_parameter',     type=float, help='Number of standard deviations away from the mean that qualifies as a jump in the stock price. Range 0.001 - 5. Default=1.', required=False, default=1.)
        self.parser.add_argument('--max_price',          type=str, help='Filter Price', required=False, default="10000.00")
        self.parser.add_argument('--models',             nargs='+', help= 'List of Models to use in the calculation. Default is Fifty Day, Two Hundred Day, CAPM, FIBO, MACD, RSI, Stochastic', required=False, default=['Fifty Day','Two Hundred Day','CAPM', 'MACD', 'RSI', 'Stochastic'])
        self.parser.add_argument('--model_time_delta',   type=str, help='Time Delta for model plots. This is the amount of time prior to today the models will compare to future prices. Default is 1mo. Options are 1d, 5d, 1mo, 3mo, 6mo, 1y, ytd', required=False, default="1mo")
        self.parser.add_argument('--min_price',          type=str, help='Filter Price', required=False, default="1.00")
        self.parser.add_argument('--number_to_highlight',type=str, help='Number of Stocks to Highlight in report. Default is 3.', required=False, default='3')
        self.parser.add_argument('--number_to_research', type=str, help='Number of Stocks to Research. Default is 5.', required=False, default="10")
        self.parser.add_argument('--output',             type=str, help='Writes data to an output file .txt and as a word document report. Do not include file extension. Apply --as_pdf to output a PDF instead.', required=False, default=None)
        self.parser.add_argument('-p',                   action='store_true', help='Display individual ticker price', required=False, default=False)
        self.parser.add_argument('--price_processing_model', type=str, help='Choose between high_low and close_open price processing models for the simulations. Default is close_open', required=False, default='close_open')
        self.parser.add_argument('--processes',          type=int, help='Number of CPUs to use on simulations.', required=False, default = 1)
        self.parser.add_argument('-r',                   action='store_true', help='Display Recommendations for a given stock', required=False, default=False)
        self.parser.add_argument('--report',             action='store_true', help='Create Montly Report', required=False, default=False)
        self.parser.add_argument('--research',           action='store_true', help='Use in conjunction with --report if you want randomly selected stocks to be included in the report. Otherwise --research will execute any of the other provided functions E.g. --compare.', required=False, default=None)
        self.parser.add_argument('--seed',               type=int, help='The Seed used for the simulation for recreation purposes...stock prices do change though.', required=False, default=42)
        self.parser.add_argument('--sim_time',           type=int, help='The number of days to calculate future prices. The default is 30.', required=False, default=30)
        self.parser.add_argument('--simulations',        type=int, help='Number of Simulations to run on each stock to predict future price. Default is 1000000 (1e6)', required=False, default=0)
        self.parser.add_argument('--simulation_model',   type=str, help='Type of distribution used for simulation can either be Gaussian (normal) or Poisson-Gamma (non-normal)', required=False, default='gaussian')
        self.parser.add_argument('--summary',            action='store_true', help='Display individual ticker business summary', required=False, default=False)
        self.parser.add_argument('--ticker',             type=str, help='Comma-Separated List of tickers for analysis.', required=False, default=None)
        self.parser.add_argument('-u',                   action='store_true', help='Use the Dow Jones stocks in addition to any inputs.', required=False, default=False)
        self.parser.add_argument('--weights',            type=dict, help='Apply weights to models as a dictionary where the key matches the model name and the value is the weight you want to apply to that model. Weights must sum to 1.', required=False, default={'Fifty Day':0.1, 'Two Hundred Day':0.1, 'CAPM':0.2, 'MACD':0.05, 'RSI':0.3, 'Stochastic':0.25})

        self.defaults = {
        'c': False, 'c_50':False, 'c_200':False, 'c_Dow':False, 'c_Nas':False,
        'c_Sap':False, 'c_50_Dow':False, 'c_50_Nas':False, 'c_50_Sap':False,
        'c_200_Dow':False, 'c_200_Nas':False,'c_200_Sap':False

        }

    def parse_args(self, arg_string):
        args_list = arg_string.split()  # Split the string into list of arguments
        args_dict = vars(self.parser.parse_args(args_list))
        self.args = ArgsNamespace(**args_dict)  # Assuming ArgsNamespace accepts kwargs
        return self.args

    def get_args(self):
        return self.args

    def reset_args(self):
        # Reset args to default values
        self.args = ArgsNamespace(**self.defaults)
        return self.args
