import argparse
from colorama import Fore, Style
import sys
import os
import pkg_resources
import pandas as pd

class StockInputManager:
    def __init__(self):
        self._set_stockapp_parser()

    def __del__(self):
        pass

    def _set_stockapp_parser(self):
        self.parser = argparse.ArgumentParser(description="Python Coded Stock Analysis.")
        self.parser.add_argument('--as_pdf',             action='store_true', help='Writes report in PDF format.', required=False, default=False)
        self.parser.add_argument('--change',             action='store_true', help='Display individual ticker current day change', required=False, default=False)
        self.parser.add_argument('--change_50',          action='store_true', help='Display individual ticker 50 day change', required=False, default=False)
        self.parser.add_argument('--change_200',         action='store_true', help='Display individual ticker 200 day change', required=False, default=False)
        self.parser.add_argument('--compare_Dow',        action='store_true', help='Display daily comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--compare_Nas',        action='store_true', help='Display daily comparison to Nasdaq Index', required=False, default=False)
        self.parser.add_argument('--compare_Sap',        action='store_true', help='Display daily comparison to S&P500 Index', required=False, default=False)
        self.parser.add_argument('--compare_50_Dow',     action='store_true', help='Display 50 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--compare_50_Nas',     action='store_true', help='Display 50 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--compare_50_Sap',     action='store_true', help='Display 50 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--compare_200_Dow',    action='store_true', help='Display 200 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--compare_200_Nas',    action='store_true', help='Display 200 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--compare_200_Sap',    action='store_true', help='Display 200 day average comparison to Dow Jones Index', required=False, default=False)
        self.parser.add_argument('--compare_50',         action='store_true', help='Display 50 day average comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--compare_200',        action='store_true', help='Display 200 day average comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--compare_Daily',      action='store_true', help='Display daily comparison to Dow, Nasdaq, and S&P500', required=False, default=False)
        self.parser.add_argument('--data',               nargs='+', help='Import Research Ticker Data from list of files. Default is nasdaqlisted.txt and otherlisted.txt', required=False, default=['nasdaqlisted.txt', 'otherlisted.txt'])
        self.parser.add_argument('--debug',              action='store_true', help='Debugging mode for developing', required=False, default=False)
        self.parser.add_argument('--import_model_class', nargs='+', help='Input the class name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--import_model_module',nargs='+', help='Input the module name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--input',              type=str, help='Input File Path to Read Stock Tickers', required=False)
        self.parser.add_argument('--index',              type=str, help='Index to Compare Models. Options- s&p,dow,nas. Default=s&p', required=False, default='s&p')
        self.parser.add_argument('--max_price',          type=str, help='Filter Price', required=False, default="1000.00")
        self.parser.add_argument('--models',             nargs='+', help= 'List of Models to use in the calculation. Default is a Daily calculation and CAPM model.', required=False, default=['default','capm','rsi'])
        self.parser.add_argument('--min_price',          type=str, help='Filter Price', required=False, default="1.00")
        self.parser.add_argument('--number_to_highlight',type=str, help='Number of Stocks to Highlight in report. Default is 3.', required=False, default='3')
        self.parser.add_argument('--number_to_research', type=str, help='Number of Stocks to Research. Default is 5.', required=False, default="10")
        self.parser.add_argument('--output',             type=str, help='Writes data to an output file .txt and as a word document report. Apply --as_pdf to output a PDF instead.', required=False, default=None)
        self.parser.add_argument('--price',              action='store_true', help='Display individual ticker price', required=False, default=False)
        self.parser.add_argument('--recommendations',    action='store_true', help='Display Recommendations for a given stock', required=False, default=False)
        self.parser.add_argument('--report',             action='store_true', help='Create Montly Report', required=False, default=False)
        self.parser.add_argument('--research',            action='store_true', help='Use in conjunction with --report if you want randomly selected stocks to be included in the report. Otherwise --research will execute any of the other provided functions E.g. --compare.', required=False, default=None)
        self.parser.add_argument('--summary',            action='store_true', help='Display individual ticker business summary', required=False, default=False)
        self.parser.add_argument('--ticker',             type=str, help='Use for individual ticker analysis', required=False)
        self.parser.add_argument('--time_delta',         type=str, help='Time Delta for calculating analysis. Default is 1mo', required=False, default="1mo")

        self.args = self.parser.parse_args()

    def conduct_stockapp_input_checks(self):
        # Conduct some user input checking
        if len(sys.argv) < 1:
            self.parser.print_help()
            sys.exit(0)
        # User must either have an individual ticker of file of list of tickers
        if self.args.input is not None and self.args.ticker is not None:
            print(Fore.YELLOW + "USER INPUT ERROR: Must either select from txt list or input a singular ticker." + Style.RESET_ALL)
            return False

        # If importing own finance model you MUST input a Module name and class name
        if self.args.import_model_class is not None != self.args.import_model_module is None:
            print(Fore.YELLOW + "USER INPUT ERROR: If importing own finance model must input both a module name and a class name." + Style.RESET_ALL)
            return False
        # Index input must be one of the three indexes
        if self.args.index.lower() not in ['s&p', 'dow','nas']:
            print(Fore.YELLOW + "USER INPUT ERROR: Must select index from 's&p','dow','nas'")
            return False

        # Number to Research must be at least 1 greater than number to highlight
        if int(self.args.number_to_research) < (int(self.args.number_to_highlight) + 1):
            print(Fore.YELLOW + "USER INPUT ERROR: Number to Research must be at least 1 greater than number to highlight." + Style.RESET_ALL)
            return False

        # Allowed to conduct report and read from input list during a single run
        if self.args.report:
            if self.args.ticker is not None:
                print(Fore.YELLOW + "USER ERROR: When report flag is selected Ticker flag cannot be utilized.")
                return False
            elif any([self.args.summary, self.args.change, self.args.change_50, self.args.change_200, self.args.recommendations]):
                print(Fore.YELLOW + "USER ERROR: When report flag is detected. Individual Ticket Flags cannot be utilized.")
                return False

        # Print disclaimer about report and research
        if self.args.report and self.args.research:
            print(Fore.YELLOW + "InputManager::conduct_stockapp_input_checks " \
            "WARNING --> When the flags for --report and --research are called " \
            "the report will contain randomly selected stocks from the data " \
            "files. No additional calculations will be ran on the researched" \
            "stocks even if another flag is passed since no individual stock" \
            "calculations can be conducted with the --report flag.")

        return True

    def grab_args(self):
        return self.args

    def apply_input_conditions(self):
        stocks = []
        if self.args.research:
            self.clean_import_data()
        # Check if there is an input file to read for tickers
        if self.args.input is not None:
            if(self.args.debug):
                print("InputManager::apply_input_conditions -- > Reading Input File: ", self.args.input)
            inputfile = StockInput(filename=self.args.input, debug=self.args.debug)
            self.ticker_list = inputfile.read_txt_file()
            if(self.args.debug):
                print("InputManager::apply_input_conditions --> Analysing the following Tickers: ", self.ticker_list)

            #Form the stocks only once from the List
            stocks = [yf.Ticker(symbol) for symbol in ticker_list]

        # Conduct analysis with only one stock
        if self.args.ticker is not None:
            stocks = [yf.Ticker(self.args.ticker)]

        analysis = Analysis(stocks, self.args)

        if self.args.report:
            analysis.conduct_report(output)
        else:
            analysis.execute_stock_program(output)

        # Okay now check if we are conducting Research outside of monthly report
        if self.args.research and not self.args.report:
            self.execute_research()

    def execute_research(self):
        research = Research(self.args.data, self.args.debug)
        research.get_ticker_symbols()
        all_tickers = research.list_ticker_symbols()
        chosen_tickers = research.choose_tickers(all_tickers, int(self.args.number_to_research))
        chosen_stocks = yf.Tickers(chosen_tickers)
        research_analysis = Analysis(chosen_stocks, self.args)
        research_analysis.execute_stock_program(output)

    def clean_import_data(self):
        if len(self.args.data) > 0:
            for filename in self.args.data:
                input = StockInput(filename, "data", self.args.debug)
                df = input.clean_data(output_filename=filename)


class StockInput:
    def __init__(self, filename=None, directory=None, debug=False):
        self.filename = filename
        self.directory = directory
        self.debug = debug

    def __del(self):
        pass

    def read_txt_file(self, input_filename=None):
        # Read data into a DataFrame
        if input_filename == None:
            if self.filename != None:
                if self.directory == None or self.directory == "user_input":
                    input_filename = pkg_resources.resource_filename('StockApp.user_input', self.filename)
                elif self.directory == "data":
                    input_filename = pkg_resources.resource_filename('StockApp.data', self.filename)

        try:
            df = pd.read_csv(input_filename, delimiter='|')
        except FileNotFoundError:
            print(f"InputManager::read_txt_file --> Error: File '{input_filename}' not found.")
            exit(1)
        except pd.errors.EmptyDataError:
            print(f"InputManager::read_txt_file --> Error: File '{input_filename}' is empty or cannot be read as CSV.")
            exit(1)

        return df

    def clean_data(self, input_filename=None, output_filename=None):
        # Read data into a DataFrame
        df = self.read_txt_file(input_filename)
        before = len(df)
        # Filter rows where "ETF" column is not equal to "Y"
        filtered_df = df[df['ETF'] != 'Y']
        df_cleaned = filtered_df.dropna(subset=['ETF'])
        after = len(df_cleaned)
        # Write filtered data to a new file
        try:
            df_cleaned.to_csv(output_filename, sep='|', index=False)  # Writing as tab-delimited data
            print(f"\nInputManager::clean_data --> Filtered data has been written to '{output_filename}'.")
            print("InputManager::clean_data Total filtered Rows --> ", before-after)
        except PermissionError:
            print(f"InputManager::clean_data --> Error: Permission denied to write to '{output_filename}'.")
            exit(1)
        except Exception as e:
            print(f"InputManager::clean_data --> Error occurred while writing to '{output_filename}': {str(e)}")
            exit(1)

        return df_cleaned
