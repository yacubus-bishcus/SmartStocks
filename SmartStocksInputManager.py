import pkg_resources
import itertools
import yfinance as yf
import logging

# My Modules
from SmartStocksAnalysis import Analysis
from SmartStocksReport import Report
from SmartStocksLucky import FeelingLucky

logger = logging.getLogger(__name__)


class SmartStocksInputManager:
    def __init__(self):
        self._tickers = []
        self._stocks = []
        self.analysis = None

    def __del__(self):
        pass

    @property 
    def tickers(self):
        return self._tickers 
    
    @property 
    def stocks(self):
        return self._stocks 

    def reset_tickers(self):
        self._tickers = None
        self._stocks = []
        logger.info("Tickers and Stocks reset.")

    @tickers.setter
    def tickers(self, values):
        ticker, _input, use_dow, research = values
        if ticker is not None:
            self._tickers = ticker.split(',')
        # Check if there is an input file to read for tickers
        if _input is not None:
            self._tickers += self.read_txt_file(_input)

        if use_dow:
            # add the dow 30
            self._tickers += self.use_dow()
        # Check if including research tickers 
        if research is not None:
            self._tickers += research.tickers
        # Remove duplicates 
        self._tickers = list(set(self._tickers))

    @stocks.setter
    def stocks(self, values): 
        if values:
            self._stocks = [yf.Ticker(symbol) for symbol in values]
        else:
            logger.error("Ticker List Empty.")

    def apply_input_conditions(self, output=None, args=None):
        logger.info(f"apply input conditions tickers {self.tickers}")
        
        if self.tickers is None:
            return 
        
        if self.stocks is None:
            return 
        
        if output is not None:
            output.total_stocks = len(self.stocks)

        self.analysis = Analysis(self.stocks, args)


        if args.report and output is not None:
            report = Report(output, args)
            report.conduct_report(self.stocks, self.analysis)
            report.write_report(self.analysis)

        elif args.simulations > 0 and not args.report:
            # user is requesting a simulation only 
            figure = self.analysis.calculate_futures(self.stocks, output)
            return figure 
        
            if args.e and output is not None:
                # email the output file to given email
                email_to = input("Email Recipient: ")
                username = input("Username: ")
                password = input("Password: ")
                logger.info(f"Sending Email to {email_to}")
                output.email(email_to=email_to, smtp_username=username, smtp_password=password, email_subject="Smart Stocks Report", email_body="See attached.", filename=args.output)
                logger.info("Email sent.")
        elif args.research and args.simulations == 0 and not args.report: # conduct feeling lucky page 
            lucky_instance = FeelingLucky(args)
            results = lucky_instance.chase_greatness(self.stocks, self.analysis)
            return results 
        else:
            results = self.analysis.execute_stock_program()
            return results

    def grab_recommendations(self):
        return self.analysis.recommendations

    def use_dow(self):
        dow30_stocks = [
    'AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW',
    'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM',
    'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT'
        ]
        return dow30_stocks

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
        input_filename = pkg_resources.resource_filename('user_input', input_filename)
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
