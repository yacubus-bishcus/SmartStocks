# from MyStock import Stock
# from CompareStocks import CompareStocks
# from Index_Stocks import Index_Stocks
# from MyStockResearch import MyStockResearch
# from datetime import datetime, timedelta
# from Model_Handler import Model_Handler

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
        research = MyStockResearch(args.debug)
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
        performance = np.zeros((num_stocks, number_of_performance_measures), dtype=float)

        if args.import_model_class != "":
            model_names = []
            performance[:, i], model_name = self.assign_models(module, class, stock_list) for i, module, class in zip(args.import_model_module, args.import_model_class)]
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
            stock = Stock(item, options.debug, output)
        else:
            stock = Stock(item, options.debug)
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
                stock_compare = CompareStocks(stock, Stock(index_stock.dow_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.dow_stock, options.debug), options.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.nas_stock,options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.nas_stock, options.debug), options.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_50_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_50_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_50_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_200_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.dow_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.dow_stock, options.debug), options.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_200_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.nas_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.nas_stock, options.debug), options.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_200_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if options.compare_Daily:
            if output is not None:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare2 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare3 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare2 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare3 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

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
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare2 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare3 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare2 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare3 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

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
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare2 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)
                stock_compare3 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug, output), options.debug, output)

            else:
                stock_compare = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare2 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)
                stock_compare3 = CompareStocks(stock, Stock(index_stock.sap_stock, options.debug), options.debug)

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

    def assign_models(self, module, class, stock_list):
        # Initiate Model_Handler class must input anything required for models
        models = Model_Handler(stock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug)

        # Check if user is importing their own model
        # User model must have two methods 'enter_inputs' and 'execute_model'
        if self.args.import_model_class != "" and self.import_model_module != "":
            try:
                imported_model = models.import_model(module, class)
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
