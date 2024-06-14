import argparse
from colorama import Fore, Style
import sys

class StockInputManager:
    def __init__(self):
        self._set_stockapp_parser()

    def __del__(self):
        pass

    def _set_stockapp_parser(self):
        self.parser = argparse.ArgumentParser(description="Python Coded Stock Analysis.")
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
        self.parser.add_argument('--debug',              action='store_true', help='Debugging mode for developing', required=False, default=False)
        self.parser.add_argument('--import_model_class', nargs='+', help='Input the class name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--import_model_module',nargs='+', help='Input the module name to import your own finance model. WARNING: User Code may not be compatible.', required=False)
        self.parser.add_argument('--input',              type=str, help='Input File Path to Read Stock Tickers', required=False)
        self.parser.add_argument('--index',              type=str, help='Index to Compare Models. Options- s&p,dow,nas. Default=s&p', required=False, default='s&p')
        self.parser.add_argument('--max_price',          type=str, help='Filter Price', required=False, default="1000.00")
        self.parser.add_argument('--models',             nargs='+', help= 'List of Models to use in the calculation. Default is a Daily calculation and CAPM model.', required=False, default=['default','capm'])
        self.parser.add_argument('--min_price',          type=str, help='Filter Price', required=False, default="1.00")
        self.parser.add_argument('--number_to_highlight',type=str, help='Number of Stocks to Highlight in report. Default is 3.', required=False, default='3')
        self.parser.add_argument('--number_to_research', type=str, help='Number of Stocks to Research. Default is 5.', required=False, default="5")
        self.parser.add_argument('--output',             type=str, help='Writes data to an output file as a report', required=False, default=None)
        self.parser.add_argument('--price',              action='store_true', help='Display individual ticker price', required=False, default=False)
        self.parser.add_argument('--recommendations',    action='store_true', help='Display Recommendations for a given stock', required=False, default=False)
        self.parser.add_argument('--report',             action='store_true', help='Create Montly Report', required=False, default=False)
        self.parser.add_argument('--suggest',            action='store_true', help='Suggests Tickers that are outperforming Indices. If input is provided it will read from tickers provided. Otherwise will randomly search 100 tickers.', required=False, default=None)
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
        if self.args.import_model_class is not None and self.args.import_model_module is None:
            print(Fore.YELLOW + "USER INPUT ERROR: If importing own finance model must input both a module name and a class name." + Style.RESET_ALL)
            return False
        if self.args.import_model_class is None and self.args.import_model_module is not None:
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
            elif self.args.input is None:
                print(Fore.YELLOW + "USER ERROR: When report flag is selected input flag must be given with an input filename.")
                return False
            elif self.args.suggest is not None:
                print(Fore.YELLOW + "USER ERROR: When report flag is detected. Suggest flag cannot be utilized.")
                return False
            elif self.args.summary or self.args.change or self.args.change_50 or self.args.change_200 or self.args.recommendations:
                print(Fore.YELLOW + "USER ERROR: When report flag is detected. Individual Ticket Flags cannot be utilized.")
                return False

        else:
            return True

        return True

    def grab_args(self):
        return self.args
