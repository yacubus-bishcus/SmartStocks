from StockApp.stock_analysis.StockResearch import StockResearch
from datetime import datetime, timedelta
from colorama import Fore, Style
import pandas_datareader.data as web
import pandas_datareader as pdr
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sklearn.preprocessing import RobustScaler
import yfinance as yf

class Analysis:
    def __init__(self, stock_list=None, time_delta="1mo", debug=False):
        if stock_list is not None:
            self.stock_list = stock_list

        self.args_set = False
        self.risk_free_rate = None
        self.market_data = None
        self.debug = debug
        self.time_delta = time_delta
        today = datetime.today()
        # total time for fred data will be a year
        self.start_date = today - timedelta(days=30 * 12) # fred data will always start a year ago
        self.end_date = today - timedelta(days=1) # fred data will always end on yesterday

    def __del__(self):
        pass

## -----------------------------------------------------------------------------------------##
## -----------------------------FUNCTIONS FOR MONTHLY REPORT ---- --------------------------##
## -----------------------------------------------------------------------------------------##
    def return_api_key(self):
        return '229A9YWEQTI3G0O5'

    def set_args_once(self, args):
        if not self.args_set:
            self.args = args
            self.args_set = True
            if self.debug:
                print("MyAnalysis::set_args_once --> Args set.")

        else:
            if self.debug:
                print("MyAnalysis::set_args_once --> Args already set.")

    def conduct_monthly_report(self, args, output):
        self.set_args_once(args)
        # Grab Research Tickers
        research = StockResearch(args.debug)
        research.get_ticker_symbols()
        all_tickers = research.list_ticker_symbols()
        if self.debug:
            print("MyAnalysis::conduct_monthly_report::Grabbing Market Data")

        # Ensure you can grab market data and establish risk free rate or MODELS
        # Will not work and program will quit
        # Just using S&P 500 for now can look into how to intregrate multiple indexes
        self.set_market_data(args.index, args.time_delta)
        self.determine_risk_free_rate()

        if self.market_data is None:
            print(Fore.RED + "FATAL ERROR: MyAnalysis::conduct_monthly_report --> market_data is empty. Check Internet Connection." + Style.RESET_ALL)
            return
        if self.risk_free_rate is None:
            print(Fore.RED + "FATAL ERROR: MyAnalysis::conduct_monthly report::determine_risk_free_rate no return. Check Internet Connection." + Style.RESET_ALL)
            return
        # Choose Random tickers from nasdaqlisted.txt and otherlisted.txt
        chosen_tickers = research.choose_tickers(all_tickers, len(args.models))
        # Determine top performances from my input list
        performers, user_tickers = self.determine_top_performers(self.stock_list, args.models, True)
        top_performers, top_tickers = self.pull_top_performers(performers, user_tickers, int(args.number_to_highlight))
        if top_performers.empty or len(top_tickers) == 0:
            return
        # Determine top performances from my research list
        research_stocks = [yf.Ticker(symbol) for symbol in chosen_tickers]
        research_performers = self.determine_top_performers(research_stocks, args.models)
        research_top_performers, research_top_tickers = self.pull_top_performers(research_performers, chosen_tickers, int(args.number_to_highlight))
        if research_top_performers.empty or len(research_top_tickers) == 0:
            return

        if top_tickers is not None and research_top_tickers is not None:
            # write the header
            output.create_executive_summary(top_tickers, research_top_tickers)
            output.create_document_heading()
            output.create_document_tables(performers, research_stocks, top_performers, research_top_performers)
        else:
            return

    def set_market_data(self, index, time_delta):
        # Check if index_stock object already exists that way you only set indexes
        # once
        if not hasattr(self, 'index_stock'):
            self.index_stock = Index_Stocks(self.debug)  # lazy initialization
            self.index_stock.set_index_info()

        self.market_data = self.index_stock.get_history(index, time_delta)
        if self.debug:
            print("MyAnalysis::set_market_data: market data --> ", self.market_data)

        self.market_data['daily_return'] = self.market_data['Close'].pct_change()

    def determine_risk_free_rate(self):
        # use historical data for the 10 year US treasury bond yield
        # only looking at past year data
        treasury_yield_data = None
        treasury_yield_data = web.DataReader('DGS10','fred',self.start_date.date(), self.end_date.date())
        if treasury_yield_data is None:
            print(Fore.RED + "FATAL ERROR: MyAnalysis::determine_risk_free_rate --> Treasury Yield Data Missing. Check Internet Connection." + Style.RESET_ALL)
            self.risk_free_rate = None
            return
    # Get the latest risk-free rate (last available value)
        self.risk_free_rate = treasury_yield_data['DGS10'].iloc[-1] / 100  # Convert percentage to decimal

        if self.debug:
            print("MyAnalysis::determine_risk_free_rate:Risk Free Rate --> ", self.risk_free_rate)

    def determine_top_performers(self, stock_list, chosen_models=['default','capm'], need_tickers=False):
        tickers = []
        # iterating over ticker object in a list of ticker objects
        # making a list of ticker symbols
        for stock in stock_list:
            tickers.append(stock.info.get('symbol'))

        if self.debug:
            print("MyAnalysis::determine_top_performers tickers --> ", tickers)

        num_stocks = len(stock_list)
        number_of_performance_measures = len(chosen_models) + len(args.import_model_class)
        # Initialize performance array
        performance = np.zeros((num_stocks, number_of_performance_measures), dtype=float)

        if args.import_model_class != "":
            model_names = []
            for i, (module, class_name) in enumerate(zip(args.import_model_module, args.import_model_class)):
                performance[:, i], model_name = self.assign_models(module, class_name, stock_list)
                model_names.append(model_name)

        for index, model in enumerate(chosen_models):
            performance[:, index + len(args.import_model_class)] = models.add_model(model)

        columns = model_names + chosen_models
        perf_df = pd.DataFrame(performance, columns=columns, index=tickers)
        # if self.debug:
        #     perf_df.to_excel('debugging.xlsx', index=False, sheet_name='Performance')
        #     print("MyAnalysis::determine_top_performers --> Performance written to excel.")

        # here i normalize each column will return a zero column if each value
        # is the same
        #norm_df = perf_df.apply(lambda x: (x - x.min()) / (x.max() - x.min()))
        scaler = RobustScaler()
        robust_scaled_data = scaler.fit_transform(perf_df)
        norm_df = pd.DataFrame(robust_scaled_data, columns=perf_df.columns, index=perf_df.index)
        # if self.debug:
        #     book = load_workbook('debugging.xlsx')
        #     writer = pd.ExcelWriter('debugging.xlsx', engine='openpyxl')
        #     writer.book = book
        #     norm_df.to_excel(writer, index=False, sheet_name='Normalized')
        #     writer.save()

        #here I sum the models "scores" after normalizing
        row_sums = norm_df.sum(axis=1)
        norm_df['Rating'] = row_sums
        # #
        # if self.debug:
        #     norm_df.to_excel('debugging.xlsx', index=True, sheet_name='Final')
        #     print("MyAnalysis::determine_top_performers --> Final written to excel.")

        if need_tickers:
            return norm_df, tickers
        else:
            return norm_df

    def pull_top_performers(self, df, tickers, filter=2):
        if len(tickers) > filter:
            top_performers = df.nlargest(filter, 'Rating')
            top_df = pd.DataFrame(top_performers)
            top_df_tickers = top_df.iloc[:,0].tolist()
            if self.debug:
                print("MyAnalysis::pull_top_performers Top Tickers --> ", top_df_tickers)
            # if self.debug:
            #     book = load_workbook('debugging.xlsx')
            #     writer = pd.ExcelWriter('debugging.xlsx', engine='openpyxl')
            #     writer.book = book
            #     top_df.to_excel(writer, index=True, sheet_name='Top Performers')
            #     writer.save()
            #     print("MyAnalysis::pull_top_performers --> Top Performers written to excel.")
        else:
            print(Fore.YELLOW + "USER ERROR: MyAnalysis::pull_top_performers --> \
             Requesting more Performers than Researched. This could result \
             from too many of the researched stocks being filtered based on \
             your filters. Try increasing the amount of stocks researched, \
             change your filters, or decrease your --number_to_highlight and \
             try again." + Style.RESET_ALL)
            return pd.DataFrame(), []
        return top_df, top_df_tickers


## -----------------------------------------------------------------------------------------##
## -----------------------------EXECUTE STOCK PROGRAM ----------- --------------------------##
## -----------------------------------------------------------------------------------------##

    def execute_stock_program(self, options, output):
        if len(self.stock_list) > 1:
            for item in self.stock_list:
                self.define_stock_program(item, options, output)
        else:
            self.define_stock_program(self.stock_list, options, output)

    def define_stock_program(self, item, options, output):
        index_stock = Index_Stocks(self.debug)
        if output is not None:
            stock = MyStock(item, options.debug, output)
        else:
            stock = MyStock(item, options.debug)
        ## ------------------ APPLY FILTERS HERE ------------------------##
        # filter out any penny stock tickers
        if stock.price is None:
            return
        if stock.price < float(options.min_price) or stock.price > float(options.max_price):
            print(stock.name, " is out of the price range, skipping.")
            return

        if options.recommendations:
            if output is not None:
                stock.output_recommendations()
            else:
                print(stock.recommendations)

        if options.summary:
            if output is not None:
                stock.output_summary()
            else:
                stock.print_summary()

        if options.change:
            if output is not None:
                stock.output_daily_change()
            else:
                stock.print_daily_change()

        if options.change_50:
            if output is not None:
                stock.output_50_change()
            else:
                stock.print_50_change()

        if options.change_200:
            if output is not None:
                stock.output_200_change()
            else:
                stock.print_200_change()

        if options.compare_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, options.debug), options.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock,options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock, options.debug), options.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_50_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_50_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_50_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_200_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, options.debug), options.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_200_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock, options.debug), options.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_200_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_Daily:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_daily_stocks()
            stock_compare2.compare_daily_stocks()
            stock_compare3.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
                stock_compare2.output_difference()
                stock_compare3.output_difference()
            else:
                stock_compare.print_difference()
                stock_compare2.print_difference()
                stock_compare3.print_difference()

        if options.compare_50:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_50_day_stocks()
            stock_compare2.compare_50_day_stocks()
            stock_compare3.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
                stock_compare2.output_difference()
                stock_compare3.output_difference()
            else:
                stock_compare.print_difference()
                stock_compare2.print_difference()
                stock_compare3.print_difference()

        if options.compare_200:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug, output), options.debug, output)

            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_200_day_stocks()
            stock_compare2.compare_200_day_stocks()
            stock_compare3.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(200)
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
                stock_compare2.output_difference()
                stock_compare3.output_difference()
            else:
                stock_compare.print_difference()
                stock_compare2.print_difference()
                stock_compare3.print_difference()


    """
    Very Important function. Assigns models and returns their outputs. These
    outputs will be distributed over the same time period for a given report
    that way the stocks can be compared 'apples to apples'. This function allows
    user to add models to Models.py directly or, as preferred, there own module
    and class. Any imported models must have an execute_model method for the
    model to be used properly.
    """

    def assign_models(self, module, class_name, stock_list):
        # Initiate Model_Handler class must input anything required for models
        models = Model_Handler(stock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug)

        # Check if user is importing their own model
        # User model must have two methods 'enter_inputs' and 'execute_model'
        if self.args.import_model_class != "" and self.import_model_module != "":
            try:
                imported_model = models.import_model(module, class_name)
                if hasattr(imported_model, 'execute_model') and hasattr(imported_model, 'get_name'):
                    # Provide user the option to pull from default models parameters
                    # this function with inputs has not been tested
                    if models.requires_inputs(imported_model.execute_model):
                        inputs = self.grab_useful_parameters(stock_list)
                        return imported_model.execute_model(*inputs), imported_model.get_name()
                    else:
                        return imported_model.execute_model(), imported_model.get_name()
                else:
                    print(Fore.YELLOW + "MyAnalysis::assign_models USER ERROR: USERs imported module " \
                    "must have two methods: 'execute_model' and 'get_name'"\
                    "execute_model executes the models calculations. SEE EXAMPLE "\
                    "PROVIDED RelativeStrengthIndex Module/class." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + "MyAnalysis::assign_models Error --> " + Style.RESET_ALL + "{e}")
                return None, ""
        else:
            return None, ""


    # Return parameters used by our Model_Handler class
    def grab_useful_parameters(self, stock_list):
        return stock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug

class Index_Stocks:
    def __init__(self, debug=None):
        self.sap_ticker = '^GSPC'
        self.dow_ticker = '^DJI'
        self.nas_ticker = '^IXIC'
        self.tickers = ['^GSPC', '^DJI', '^IXIC']
        self.index_stocks = None
        self.sap_stock = None
        self.dow_stock = None
        self.nas_stock = None
        self.info_set = False
        if debug is not None:
            self.debug = debug
        else:
            self.debug = False

    def set_index_info(self):
        if not self.info_set:
            self.index_stocks = yf.Tickers(self.tickers)
            self.sap_stock = self.index_stocks.tickers[self.sap_ticker]
            self.dow_stock = self.index_stocks.tickers[self.dow_ticker]
            self.nas_stock = self.index_stocks.tickers[self.nas_ticker]

            if self.debug:
                print("Index_Stocks::set_index_info --> Stocks Set.")
                print("Index_stocks::set_index_info --> SAP STOCK: ", self.sap_stock)

            self.info_set = True
        else:
            if self.debug:
                print("Index_Stocks::set_index_info --> Info already fetched.")

    def get_history(self, index, period='1mo'):
        if index.lower() == "s&p":
            return self.sap_stock.history(period=period)
        elif index.lower() == "dow":
            return self.dow_stock.history(period=time_delta)
        elif index.lower() == "nas":
            return self.nas_stock.history(period=time_delta)
        else:
            print(Fore.YELLOW + "USER ERROR: Index_Stocks::get_history --> Index Name Not Found" + Style.RESET_ALL)
            return None

class CompareStocks:
    def __init__(self, stock1=None, stock2=None, debug=None, output=None):
        # Constructor with 4 arguments
        if stock1 is not None and stock2 is not None and debug is not None and output is not None:
            self.stock1 = stock1
            self.stock2 = stock2
            self.output = output
            self.debug = debug
        # Constructor with 3 arguments
        elif stock1 is not None and stock2 is not None and debug is not None:
            self.stock1 = stock1
            self.stock2 = stock2
            self.debug = debug
        # Constructor with 2 arguments defaults debug to false (minimum)
        else:
            self.stock1 = stock1
            self.stock2 = stock2
            self.debug = False

        #Initialize variables
        self.difference = 0


    def compare_daily_stocks(self):
        if self.stock1.daily_percent and self.stock2.daily_percent:
            self.difference = round(self.stock1.daily_percent - self.stock2.daily_percent, 2)

    def compare_50_day_stocks(self):
        if(self.debug):
            print(self.stock1.info)
        if self.stock1.fifty_percent and self.stock2.fifty_percent:
            self.difference = round(self.stock1.fifty_percent - self.stock2.fifty_percent, 2)
        else:
            print("DATA ERROR: compare_50_day_stocks")


    def compare_200_day_stocks(self):
        if self.stock1.twohundred_percent and self.stock2.twohundred_percent:
            self.difference = round(self.stock1.twohundred_percent - self.stock2.twohundred_percent, 2)

    def print_difference(self):
        if self.difference > 0:
            print(self.stock1.name, " is outperforming ", self.stock2.name, " by ", Fore.GREEN + str(self.difference) + Style.RESET_ALL, " percent.")
        else:
            print(self.stock1.name, " is underperforming ", self.stock2.name, " by ", Fore.RED + str(self.difference) + Style.RESET_ALL, " percent.")

    def output_stock_name(self, days=0):
        output_string = str(self.stock1.name)
        self.output.write(output_string, font_size=20, bold=True, alignment=WD_PARAGRAPH_ALIGNMENT.CENTER)
        if days > 0:
            days_string = "In the last " + str(days) + " days: "
            self.output.write(days_string)

    def output_stock_current_price(self):
        output_string = str(self.stock1.name) + " Current Price is: " + str(self.stock1.price)
        self.output.write(output_string)

    def output_difference(self):
        if self.difference > 0:
            #output_string = self.stock1.name+ " is outperforming "+ self.stock2.name, " by " + Fore.GREEN + str(self.difference) + Style.RESET_ALL + " percent."
            output_string = self.stock1.name + " is outperforming " + self.stock2.name + " by " + str(self.difference) + " percent."
            self.output.write(output_string, color=(0,128,0))
        else:
            #output_string = self.stock1.name + " is underperforming " + self.stock2.name+ " by "+ Fore.RED + str(self.difference) + Style.RESET_ALL + " percent."
            output_string = self.stock1.name + " is underperforming " + self.stock2.name + " by " + str(self.difference) + " percent."
            self.output.write(output_string, color=(128,0,0))

class MyStock:
    # python only reads one __init__
    def __init__(self, stock, debug=None, output=None):
        # initialize attributes
        self.symbol = None
        self.name = None
        self.recommendations = None
        self.longBusinessSummary = None
        self.price = 0.
        self.daily_percent = 0.
        self.twohundred_percent = 0.
        self.fifty_percent = 0.
        # Constructor with 3 arguments
        if stock is not None and debug is not None and output is not None:
            if isinstance(stock, list):
                self.stock = stock[0]
            else:
                self.stock = stock
            self.symbol = self.stock.info['symbol']
            self.debug = debug
            self.output = output
        # Constructor with 2 Arguments
        elif stock is not None and debug is not None:
            if isinstance(stock, list):
                self.stock = stock[0]
            else:
                self.stock = stock

            self.symbol = self.stock.info['symbol']
            self.debug = debug
        # Constructor with 1 Argument (minimum)
        else:
            self.stock = stock
            self.debug = False

        self.is_index = False
        index_funds = ['^IXIC','^DJI','^GSPC']
        if self.symbol in index_funds:
            self.is_index = True

        # Fetch stock info from Yahoo Finance
        # handle error cases
        self._fetch_stock_info()
        self.fifty_percent = self.get_fifty_percent()
        self.twohundred_percent = self.get_twohundred_percent()

    def _fetch_stock_info(self):
        self.info = self.stock.info

        if self.info:
            self.name = self.info.get('longName')
            if self.name:
                if self.debug:
                    print(f"Stock: {self.name} ({self.symbol})")
            else:
                print(Fore.YELLOW + "ERROR: Stock name not available." + Style.RESET_ALL)
                return
        else:
            print(Fore.YELLOW + "ERROR: Unable to fetch information for the stock. Please check the symbol." + Style.RESET_ALL)
            return

        self.price = self.info.get('currentPrice')
        if self.price:
            if self.debug:
                print(f"Current Price: {self.price}")
        else:
            if self.is_index:
                self.price = self.info.get('ask')
                if self.debug:
                    print(f"Current Price: {self.price}")
            else:
                print(self.name, " current Price not available.")

        self.fiftyavg = self.info.get('fiftyDayAverage')
        if self.fiftyavg:
            if self.debug:
                print(f"Fifty Day Average: {self.fiftyavg}")
        else:
            print(self.name, " Fifty Day Average Not Available.")

        self.twohundredavg = self.info.get('twoHundredDayAverage')
        if self.twohundredavg:
            if self.debug:
                print(f"Two Hundred Day Average: {self.twohundredavg}")
        else:
            print(self.name, " Two Hundred Day Average Not Available.")

        self.open_price = self.info.get('open')
        if self.open_price:
            if self.debug:
                print(f"Open Price: {self.open_price}")
        else:
            print(Fore.Yellow + "ERROR: Open Price not available." + Style.RESET_ALL)
            if self.debug:
                print("Here is the information we have on ", self.name)
                print(self.info)

        if self.price and self.open_price:
            self.daily_percent = (self.price - self.open_price)/self.price*100
            if self.fiftyavg:
                self.fifty_percent = (self.price - self.fiftyavg)/self.price*100
            if self.twohundredavg:
                self.twohundred_percent = (self.price - self.twohundredavg)/self.price*100

        elif self.open_price:
            if self.fiftyavg:
                self.fifty_percent = (self.open_price - self.fiftyavg)/self.open_price*100
            if self.twohundredavg:
                self.twohundred_percent = (self.open_price - self.twohundredavg)/self.open_price*100
        else:
            print(Fore.YELLOW + "ERROR: Open Price and Current Price Not Available." + Style.RESET_ALL)
            if self.debug:
                print("Here is the information we have on ", self.name)
                print(self.info)
            return

        self.summary = self.info.get('longBusinessSummary')
        self.recommendations = self.stock.recommendations

    def __del__(self):
        pass

    # Define setting methods
    def get_fifty_percent(self):
        return self.fifty_percent

    def get_twohundred_percent(self):
        return self.twohundred_percent

    # Define other getter methods for encapsulation

    def print_daily_change(self):
        print(self.name, " Daily Change Percent: ", self.daily_percent)

    def print_50_change(self):
        print(self.name, " 50 Day Average Change Percent: ", self.fifty_percent)

    def print_200_change(self):
        print(self.name, " 200 Day Average Change Percent: ", self.twohundred_percent)

    def output_daily_change(self):
        self.output.write(self.name, " Daily Change Percent: ", self.daily_percent)

    def output_50_change(self):
        self.output.write(self.name, " 50 Day Average Change Percent: ", self.fifty_percent)

    def output_200_change(self):
        self.output.write(self.name, " 200 Day Average Change Percent: ", self.twohundred_percent)

    def output_recommendations(self):
        self.output.write_table(self.recommendations, 'Recommendations')

    def print_summary(self):
        print(self.name, " Summary: ", self.summary)

    def output_summary(self):
        self.output.write(self.name, " Summary: ", self.summary)
