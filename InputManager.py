import argparse
from colorama import Fore, Style
import sys
import os
import pkg_resources
import pandas as pd
import itertools
import yfinance as yf
from StockAnalysis import Analysis
from Research import Research
from Report import Report
import logging
import ast
import multiprocessing as mp

# My Modules
from ArgsParser import ArgsParser
from StockAnalysis import Analysis
from Research import Research
from Report import Report

logger = logging.getLogger(__name__)


class StockInputManager:
    def __init__(self, app=False):
        if not app:
            self._set_stockapp_parser()
        else:
            self.parser = ArgsParser()
            self.args = self.parser.parse_args('-a')
        self.ticker_list = []
        self.stocks = []
        self.analysis = None

    def __del__(self):
        pass

    def _set_stockapp_parser(self):
        self.parser = argparse.ArgumentParser(description="Python Coded Stock Analysis.")
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
        self.parser.add_argument('--simulations',        type=int, help='Number of Simulations to run on each stock to predict future price. Default is 1000000 (1e6)', required=False, default=1)
        self.parser.add_argument('--simulation_model',   type=str, help='Type of distribution used for simulation can either be Gaussian (normal) or Poisson-Gamma (non-normal)', required=False, default='gaussian')
        self.parser.add_argument('--summary',            action='store_true', help='Display individual ticker business summary', required=False, default=False)
        self.parser.add_argument('--ticker',             type=str, help='Comma-Separated List of tickers for analysis.', required=False)
        self.parser.add_argument('-u',                   action='store_true', help='Use the Dow Jones stocks in addition to any inputs.', required=False, default=False)
        self.parser.add_argument('--weights',            type=dict, help='Apply weights to models as a dictionary where the key matches the model name and the value is the weight you want to apply to that model. Weights must sum to 1.', required=False, default={'Fifty Day':0.1, 'Two Hundred Day':0.1, 'CAPM':0.2, 'MACD':0.05, 'RSI':0.3, 'Stochastic':0.25})
        self.args = self.parser.parse_args()

    def conduct_stockapp_input_checks(self):
        # Conduct some user input checking
        if len(sys.argv) < 1:
            self.parser.print_help()
            sys.exit(0)
        # User must either have an individual ticker of file of list of tickers
        if self.args.input is not None and self.args.ticker is not None:
            logger.error(Fore.YELLOW + "USER INPUT ERROR: Must either select from txt list or input a singular ticker." + Style.RESET_ALL)
            return False

        # If importing own finance model you MUST input a Module name and class name
        if self.args.import_model_class is not None != self.args.import_model_module is None:
            logger.error(Fore.YELLOW + "USER INPUT ERROR: If importing own finance model must input both a module name and a class name." + Style.RESET_ALL)
            return False
        # Index input must be one of the three indexes
        if self.args.index.lower() not in ['s&p', 'dow','nas']:
            logger.error(Fore.YELLOW + "USER INPUT ERROR: Must select index from 's&p','dow','nas'")
            return False

        # Number to Research must be at least 1 greater than number to highlight
        if int(self.args.number_to_research) < (int(self.args.number_to_highlight) + 1):
            logger.error(Fore.YELLOW + "USER INPUT ERROR: Number to Research must be at least 1 greater than number to highlight." + Style.RESET_ALL)
            return False

        # Allowed to conduct report and read from input list during a single run
        if self.args.report:
            if self.args.ticker is not None:
                logger.error(Fore.YELLOW + "USER ERROR: When report flag is selected Ticker flag cannot be utilized.")
                return False
            elif any([self.args.summary, self.args.c, self.args.c_50, self.args.c_200, self.args.r]):
                logger.error(Fore.YELLOW + "USER ERROR: When report flag is detected. Individual Ticket Flags cannot be utilized.")
                return False


        time_options = ['1d','5d','1mo','3mo','6mo','1y', 'ytd']
        if self.args.model_time_delta not in time_options:
            logger.warning(Fore.YELLOW + f"USER ERROR: Time Delta must be in {time_options}" + Style.RESET_ALL)
            logger.warning(Fore.YELLOW + "Time Delta defaulted to 1mo (1 month)" + Style.RESET_ALL)

        # Print disclaimer about report and research
        if self.args.report and self.args.research:
            logger.warning(Fore.YELLOW + "When the flags for --report and --research are called " \
            "the report will contain randomly selected stocks from the data " \
            "files. No additional calculations will be ran on the researched " \
            "stocks even if another flag is passed since no individual stock " \
            "calculations can be conducted with the --report flag." + Style.RESET_ALL)

        self.args.simulations = abs(self.args.simulations)
        self.args.processes = abs(self.args.processes)
        if self.args.processes > mp.cpu_count():
            logger.warning("Requested more processors than you have, defaulting to all processors.")
            self.args.processes = mp.cpu_count()

        self.args.sim_time = abs(self.args.sim_time)
        weights_sum = sum(value for value in self.args.weights.values())
        if weights_sum != 1:
            logger.error(Fore.YELLOW + "USER ERROR: Sum of Weights must be equal to 1.")
            return False

        self.args.price_processing_model = self.args.price_processing_model.lower()
        price_processing_model_options = ['high_low', 'close_open']
        if self.args.price_processing_model not in price_processing_model_options:
            logger.error(Fore.YELLOW + f"USER ERROR: Ensure you choose from {price_processing_model_options} for your price processing model." + Style.RESET_ALL)
            return False

        self.args.simulation_model = self.args.simulation_model.lower()
        simulation_model_options = ['gaussian', 'poisson-gamma']
        if self.args.simulation_model not in simulation_model_options:
            logger.error(Fore.YELLOW + f"USER ERROR: Ensure you choose from {simulation_model_options} for your simulation distribution model." + Style.RESET_ALL)
            return False

        if not 0.001 <= self.args.jump_parameter <= 5.:
            logger.error(Fore.YELLOW + f"USER ERROR: Ensure jump parameter is between 0.001 and 5. Your parameter was {self.jump_parameter}")
            return False

        return True

    def grab_args(self):
        return self.args

    def grab_stocks(self):
        return self.stocks

    def set_args(self, args):
        self.args = args

    def reset_tickers(self):
        self.args.ticker = None
        self.ticker_list = []
        self.stocks = []
        logger.info("Ticker reset.")
        logger.debug(f"Ticker: {self.args.ticker}")
        logger.debug(f"Ticker_list: {self.ticker_list}")

    def collect_tickers(self):
        if self.args.ticker is not None:
            self.ticker_list = self.args.ticker.split(',')
            # Check if there is an input file to read for tickers
        if self.args.input is not None:
            self.ticker_list += self.read_txt_file(self.args.input)
            if self.args.u:
                # add the dow 30 to any on list and then remove duplicates
                self.ticker_list += self.use_dow()

        if self.args.research:
            research = Research(self.args)
            self.ticker_list += research.grab_research_tickers()

        if self.args.ticker is None:
            if self.ticker_list is not None:
                self.ticker_list = list(set(self.ticker_list))

        return self.ticker_list

    def apply_input_conditions(self, output=None, args=None):
        self.ticker_list = self.collect_tickers()
        logger.info(f"apply input conditions tickers {self.ticker_list}")
        if self.ticker_list:
            self.stocks = [yf.Ticker(symbol) for symbol in self.ticker_list]
        else:
            logger.error("Ticker List is empty.")
            logger.warning(f"Your Ticker: {self.args.ticker}")
            return

        if output is not None:
            output.add_to_report_card('total_stocks', len(self.stocks))

        self.analysis = Analysis(self.stocks, self.args)


        if self.args.report and output is not None:
            report = Report(output, self.args)
            report.conduct_report(self.stocks, self.analysis)
            report.write_report(self.analysis)

            if self.args.e:
                # email the output file to given email
                handler = OutputHandler(args.output)
                email_to = input("Email Recipient: ")
                username = input("Username: ")
                password = input("Password: ")
                logger.info(f"Sending Email to {email_to}")
                handler.email_file(email_to=email_to, smtp_username=username, smtp_password=password)
                logger.info("Email sent.")

        else:
            if args is None:
                return self.analysis.execute_stock_program(args=self.args, output=output)
            else:
                return self.analysis.execute_stock_program(args=args, output=output)

    def grab_market_data(self, index, time_delta):
        return self.analysis.get_market_data(index, time_delta)

    def grab_summary(self):
        return self.analysis.return_summary_info()

    def grab_recommendations(self):
        return self.analysis.return_recommendations()

    def use_dow(self):
        dow30_stocks = [
    'AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW',
    'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM',
    'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT'
        ]
        return dow30_stocks

    def clean_import_data(self, filename):
        if len(self.args.data) > 0:
            for filename in self.args.data:
                input = StockInput(self.args.d)
                df = input.clean_data(filename, filename)

    def create_debugging_combination_file(self):
        # Define your arguments with their respective flags and default values
        arguments = {
            '--as_pdf': ['', '--as_pdf'],
            '--change': ['', '--change'],
            '--change_50': ['', '--change_50'],
            '--change_200': ['', '--change_200'],
            '--compare_Dow': ['', '--compare_Dow'],
            '--compare_Nas': ['', '--compare_Nas'],
            '--compare_Sap': ['', '--compare_Sap'],
            '--compare_50_Dow': ['', '--compare_50_Dow'],
            '--compare_50_Nas': ['', '--compare_50_Nas'],
            '--compare_50_Sap': ['', '--compare_50_Sap'],
            '--compare_200_Dow': ['', '--compare_200_Dow'],
            '--compare_200_Nas': ['', '--compare_200_Nas'],
            '--compare_200_Sap': ['', '--compare_200_Sap'],
            '--compare_50': ['', '--compare_50'],
            '--compare_200': ['', '--compare_200'],
            '--compare_Daily': ['', '--compare_Daily'],
            '--data': [['nasdaqlisted.txt', 'otherlisted.txt']],
            '--debug': ['', '--debug'],
            '--import_model_class': [['model1', 'model2'], None],
            '--import_model_module': [['module1', 'module2'], None],
            '--input': ['input_file.txt'],
            '--index': ['s&p'],
            '--max_price': ['1000.00'],
            '--models': [['default', 'capm', 'rsi']],
            '--min_price': ['1.00'],
            '--number_to_highlight': ['3'],
            '--number_to_research': ['10'],
            '--output': [None],
            '--price': ['', '--price'],
            '--recommendations': ['', '--recommendations'],
            '--report': ['', '--report'],
            '--research': [None],
            '--summary': ['', '--summary'],
            '--ticker': ['ticker_symbol'],
            '--time_delta': ['1mo']
        }

        # Prepare lists for itertools.product()
        arg_values = []
        for arg_key, arg_list in arguments.items():
            if isinstance(arg_list, list):
                arg_values.append(arg_list) # only append if its a list
            else:
                arg_values.append([arg_list]) # wrap non-list values in a list

        # Generate all combinations of arguments
        combinations = itertools.product(*arg_values)

        # Write each combination to a file
        with open('combinations.sh', 'w') as f:
            for combo in combinations:
                # Ensure all elements in combo are strings
                combo = [str(item) for item in combo]
                # Filter out empty values and format the output command
                command = 'python3 -m StockApp ' + ' '.join(filter(None, combo))
                f.write(command + '\n')

        logger.info("--> Combinations written to combinations.sh")

    def read_txt_file(self, input_filename):
        if not input_filename.endswith(".txt"):
            logger.warning("--> Inputed Filename not a .txt file. Converting.")
            input_filename = input_filename + ".txt"
        # Read data into a DataFrame
        input_filename = pkg_resources.resource_filename('StockApp.user_input', input_filename)
        try:
            lines = []
            with open(input_filename, 'r') as file:
                for line in file:
                # strip newline characters and skip lines starting with #
                    cleaned_line = line.strip()
                    if cleaned_line.startswith('#'):
                        continue

                    lines.append(cleaned_line)

            return lines

        except FileNotFoundError:
            logger.exception(f"Error: File '{input_filename}' not found.")
            return []
