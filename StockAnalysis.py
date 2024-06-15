from StockApp.Model_Handler import Model_Handler
from datetime import datetime, timedelta
from colorama import Fore, Style
import pandas_datareader.data as web
import pandas_datareader as pdr
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sklearn.preprocessing import RobustScaler
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import ftplib
import os
import sys
import random
from selenium import webdriver
import pkg_resources


class Analysis:
    def __init__(self, stock_list=None, args=None):
        self.stock_list = stock_list
        #self.args_set = False
        self.risk_free_rate = None
        self.market_data = None
        self.args = args
        self.today = datetime.today()
        # total time for fred data will be a year
        self.start_date = self.today - timedelta(days=30 * 12) # fred data will always start a year ago
        self.end_date = self.today - timedelta(days=1) # fred data will always end on yesterday

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
                print("StockAnalysis::Analysis::set_args_once --> Args set.")

        else:
            if self.debug:
                print("StockAnalysis::Analysis::set_args_once --> Args already set.")

    def conduct_report(self, output):
        # Grab Research Tickers
        if self.args.research:
            research = Research(self.args.data, self.args.debug)
            research.get_ticker_symbols()
            all_tickers = research.list_ticker_symbols()
        if self.debug:
            print("StockAnalysis::Analysis::conduct_monthly_report::Grabbing Market Data")

        # Ensure you can grab market data and establish risk free rate or MODELS
        # Will not work and program will quit
        # Just using S&P 500 for now can look into how to intregrate multiple indexes
        self.set_market_data(self.args.index, self.args.time_delta)
        self.determine_risk_free_rate()

        if self.market_data is None:
            print(Fore.RED + "FATAL ERROR: StockAnalysis::Analysis::conduct_monthly_report --> market_data is empty. Check Internet Connection." + Style.RESET_ALL)
            return
        if self.risk_free_rate is None:
            print(Fore.RED + "FATAL ERROR: StockAnalysis::Analysis::conduct_monthly report::determine_risk_free_rate no return. Check Internet Connection." + Style.RESET_ALL)
            return
        # Determine top performances from my input list
        # apply cuts on inputed research list
        if len(self.stock_list) > 0:
            filtered_stocks = []
            filtered_tickers = []
            for stock in self.stock_list:
                stock = MyStock(stock)
                if not self.apply_cuts(stock):
                    filtered_stocks.append(stock)
                    filtered_tickers.append(stock.symbol)

            performers = self.determine_top_performers(filtered_stocks, self.args.models)
            top_performers, top_tickers = self.pull_top_performers(performers, filtered_tickers, int(self.args.number_to_highlight))
            if top_performers.empty or len(top_tickers) == 0:
                return
        ########################################################################
        ########## Determine top performances from my research list ############
        ########################################################################
        # Choose Random tickers from nasdaqlisted.txt and otherlisted.txt
        if self.args.research:
            chosen_tickers = research.choose_tickers(all_tickers, int(self.args.number_to_research))
            research_stocks = [yf.Ticker(symbol) for symbol in chosen_tickers]

            # Apply cuts to researched stocks here
            filtered_research_stocks = []
            filtered_research_tickers = []
            for stock in research_stocks:
                stock = MyStock(stock)
                if not self.apply_cuts(stock):
                    filtered_research_stocks.append(stock)
                    filtered_research_tickers.append(stock.symbol)

            research_performers = self.determine_top_performers(filtered_research_stocks, self.args.models, "Researched")
            research_top_performers, research_top_tickers = self.pull_top_performers(research_performers, filtered_research_tickers, int(self.args.number_to_highlight))

            if research_top_performers.empty or len(research_top_tickers) == 0:
                return

        ########################################################################
        ########## Top Performance gets a Model Graphical Page #################
        ########################################################################
        if len(self.self.stock_list) > 0:
            the_number_one, the_number_one_ticker = self.pull_top_performers(performers, filtered_tickers, 1)
            target_stock = None
            for myStock in filtered_stocks:
                if myStock.symbol == the_number_one_ticker:
                    target_stock = myStock
            number_one_model = Model_Handler(target_stock, self.market_data, self.risk_free_rate, self.time_delta, self.debug)
            number_one_model.add_all_plotting_models()
            plot1 = number_one_model.plot_catcher()

        if self.args.research:
            the_number_one_researched, the_number_one_researched_ticker = self.pull_top_performers(research_performers, filtered_research_tickers, 1)

            target_stock2 = None
            for myStock in filtered_research_stocks:
                if myStock.symbol == the_number_one_researched_ticker:
                    target_stock2 = myStock
            number_one_research_model = Model_Handler(target_stock2, self.market_data, self.risk_free_rate, self.time_delta, self.debug)
            number_one_research_model.add_all_plotting_models()
            plot2 = number_one_research_model.plot_catcher()

        ########################################################################
        ##################### Write Results to Output File #####################
        ########################################################################
        if top_tickers is not None and research_top_tickers is not None:
            # write the header
            if self.args.output and not self.args.debug:
                output.create_executive_summary(top_tickers, research_top_tickers)
                output.create_document_heading()
                output.create_document_tables(performers, research_stocks, top_performers, research_top_performers, 4)
                output.add_plots_to_word([plot1, plot2])
        elif top_tickers is not None and research_top_tickers is None:
            if self.args.output and not self.args.debug:
                output.create_executive_summary(top_tickers)
                output.create_document_heading()
                output.create_document_tables(user_list=performers, top_perf=top_performers, table_count=2)
                output.add_plots_to_word([plot1])
        elif top_tickers is None and research_top_tickers is not None:
            if self.args.output and not self.args.debug:
                output.create_executive_summary(research_top_tickers)
                output.create_document_heading()
                output.create_document_tables(research_list=research_stocks, research_top=research_top_performers, table_count=2)
                output.add_plots_to_word([plot2])
        else:
            if self.debug:
                print(Fore.RED + "StockAnalysis::conduct_report --> FATAL ERROR: Tickers not found." + Style.RESET_ALL)

            return

    def set_market_data(self, index, time_delta):
        # Check if index_stock object already exists that way you only set indexes
        # once
        if not hasattr(self, 'index_stock'):
            self.index_stock = Index_Stocks(self.debug)  # lazy initialization
            self.index_stock.set_index_info()

        self.market_data = self.index_stock.get_history(index, time_delta)
        if self.debug:
            print("StockAnalysis::Analysis::set_market_data: market data --> ")
            print(self.market_data.head(3))

        self.market_data['daily_return'] = self.market_data['Close'].pct_change()

    def determine_risk_free_rate(self):
        # use historical data for the 10 year US treasury bond yield
        # only looking at past year data
        treasury_yield_data = None
        treasury_yield_data = web.DataReader('DGS10','fred',self.start_date.date(), self.end_date.date())
        if treasury_yield_data is None:
            print(Fore.RED + "FATAL ERROR: StockAnalysis::Analysis::determine_risk_free_rate --> Treasury Yield Data Missing. Check Internet Connection." + Style.RESET_ALL)
            self.risk_free_rate = None
            return
    # Get the latest risk-free rate (last available value)
        self.risk_free_rate = treasury_yield_data['DGS10'].iloc[-1] / 100  # Convert percentage to decimal

        if self.debug:
            print("StockAnalysis::Analysis::determine_risk_free_rate:Risk Free Rate --> ", self.risk_free_rate)

    """
    Outputs a pandas DataFrame containing the normalized sums of each chosen
    models outputs. In essense create an order of merit rating system for each
    stock. Input includes a list of MyStock objects and chosen_models to perform.
    """
    def determine_top_performers(self, myStock_list, chosen_models=['50 Day','200 Day','capm'], sheet_name="From_List"):
        tickers = []
        # iterating over ticker object in a list of ticker objects
        # making a list of ticker symbols
        for stock in myStock_list:
            tickers.append(stock.symbol)
            prices.append(stock.price)

        if self.debug:
            print("StockAnalysis::Analysis::determine_top_performers tickers --> ", tickers)
        # Initate Model Handler to add models as necessary
        models = Model_Handler(myStock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug)

        # Determine the total number of models to be applied to the stock
        if self.args.import_model_class is not None:
            number_of_performance_measures = len(chosen_models) + len(self.args.import_model_class)
        else:
            number_of_performance_measures = len(chosen_models)

        # Initialize performance array based on the number of stocks and the
        # total number of models to be applied to the stock
        performance = np.zeros((len(myStock_list), number_of_performance_measures), dtype=float)

        # IF THE USER is assigning their own model to the stock this code will
        # execute the model using execute_model method and place the output in
        # the performance array assign models also outputs the model name from
        # get_name method.
        if self.args.import_model_class != "" and self.args.import_model_class is not None:
            model_names = []
            for i, (module, class_name) in enumerate(zip(self.args.import_model_module, self.args.import_model_class)):
                performance[:, i], model_name = self.assign_models(module, class_name, myStock_list)
                model_names.append(model_name)

        # IF THE USER is assigned their own model AND they want the program
        # internal models to be used this code executes the program internal
        # models and adds their outputs to the performance array. Again the
        # performance array here contains each models output for each given
        # stock. the data here is yet to be normalized or labled.
        for index, model in enumerate(chosen_models):
            if self.args.import_model_class is not None:
                if models.add_model(model) is not None:
                    performance[:, index + len(self.args.import_model_class)] = models.add_model(model)
            else:
                if models.add_model(model) is not None:
                    performance[:, index] = models.add_model(model)

        # Assign column names based on the models used names
        if self.args.import_model_class is not None:
            columns = model_names + chosen_models
        else:
            columns = chosen_models

        # create a pandas DataFrame given the performance array and apply labels
        perf_df = pd.DataFrame(performance, columns=columns, index=tickers)
        # if self.debug:
        #     perf_df.to_excel('debugging.xlsx', index=False, sheet_name='Performance')
        #     print("StockAnalysis::Analysis::determine_top_performers --> Performance written to excel.")

        # here i normalize each column will return a zero column if each value
        # is the same
        #norm_df = perf_df.apply(lambda x: (x - x.min()) / (x.max() - x.min()))
        """
        The fit_transform method calculates the scaling parameters
        (e.g., median, IQR) based on the data and then applies the scaling to
        the data, returning the scaled data as robust_scaled_data. this code
        snippet scales the data in perf_df using robust scaling, ensuring that
        the scaling is less influenced by outliers compared to standard scaling
        methods like MinMaxScaler or StandardScaler. The scaled data is then
        stored in the DataFrame norm_df for further analysis.
        """
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
        norm_df['Price'] = prices
        # Write to excel file for historic comparison
        the_sheet_name_string = sheet_name + self.today
        norm_df.to_excel('Historicals.xlsx', index=True, sheet_name=the_sheet_name_string)
        print("StockAnalysis::Analysis::determine_top_performers --> Final written to excel.")

        return norm_df

    def pull_top_performers(self, df, tickers, filter=2):
        if len(tickers) > filter:
            top_performers = df.nlargest(filter, 'Rating')
            top_df = pd.DataFrame(top_performers)
            top_df_tickers = top_df.iloc[:,0].tolist()

            if self.debug:
                print("StockAnalysis::Analysis::pull_top_performers Top Tickers --> ", top_df_tickers)
            # if self.debug:
            #     book = load_workbook('debugging.xlsx')
            #     writer = pd.ExcelWriter('debugging.xlsx', engine='openpyxl')
            #     writer.book = book
            #     top_df.to_excel(writer, index=True, sheet_name='Top Performers')
            #     writer.save()
            #     print("StockAnalysis::Analysis::pull_top_performers --> Top Performers written to excel.")
        else:
            print(Fore.YELLOW + "USER ERROR: StockAnalysis::Analysis::pull_top_performers -->" \
             "Requesting more Performers than Researched. This could result " \
             "from too many of the researched stocks being filtered based on "\
             "your filters. Try increasing the amount of stocks researched, "\
             "change your filters, or decrease your --number_to_highlight and "\
             "try again." + Style.RESET_ALL)
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
                    print(Fore.YELLOW + "StockAnalysis::Analysis::assign_models USER ERROR: USERs imported module " \
                    "must have two methods: 'execute_model' and 'get_name'"\
                    "execute_model executes the models calculations. SEE EXAMPLE "\
                    "PROVIDED RelativeStrengthIndex Module/class." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + "StockAnalysis::Analysis::assign_models Error --> " + Style.RESET_ALL + "{e}")
                return None, ""
        else:
            return None, ""


    # Return parameters used by our Model_Handler class
    def grab_useful_parameters(self, stock_list):
        return stock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug

    # Apply Cuts method called in conduct_monthly_report input is a MyStock object
    def apply_cuts(self, myStock):
        # filter out any penny stock tickers
        if myStock.price is None:
            return True
        if myStock.price < float(self.args.min_price) or myStock.price > float(self.args.max_price):
            print(myStock.name, " is out of the price range, skipping.")
            return True
        # Filter out any ETFs
        if myStock.is_etf:
            return True
        # Ensure fifty percent is not none
        if myStock.fifty_percent is None:
            return True

## -----------------------------------------------------------------------------------------##
## ----------------------------- INDEX_STOCKS CLASS    ----------- -------------------------##
## -----------------------------------------------------------------------------------------##
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

## -----------------------------------------------------------------------------------------##
## ----------------------------- CompareStocks CLASS    ----------- ------------------------##
## -----------------------------------------------------------------------------------------##

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


## -----------------------------------------------------------------------------------------##
## ----------------------------- MyStock CLASS    ----------- ------------------------------##
## -----------------------------------------------------------------------------------------##

class MyStock:
    # python only reads one __init__
    def __init__(self, stock, debug=None, output=None):
        # initialize attributes
        self.symbol = None
        self.name = None
        self.the_recommendations = None
        self.the_summary = None
        self.price = 0.
        self.daily_percent = 0.
        self.twohundred_percent = 0.
        self.fifty_percent = 0.
        self.is_etf = False
        self.the_history = None

        if isinstance(stock, list):
            self.stock = stock[0]
        else:
            self.stock = stock

        self.symbol = self.stock.info['symbol']
        self.debug = debug
        self.output = output
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

        self.the_summary = self.info.get('longBusinessSummary')
        self.the_recommendations = self.stock.recommendations
        self.the_history = self.stock.history(period="1y")

        if self.info.get('quoteType') == "ETF":
            self.is_etf = True

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

## -----------------------------------------------------------------------------------------##
## ----------------------------- Research CLASS    ----------- ------------------------------##
## -----------------------------------------------------------------------------------------##

class Research:
    def __init__(self, filenames=["nasdaqlisted.txt", "otherlisted.txt"], debug=False):
        self.debug = debug
        if self.debug:
            print("StockAnalysis::Research --> Grabbing All Tickers...")
        self.filenames = filenames

    def fetch_csv_data(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def get_ticker_symbols(self):
        # Check if we already have the files
        count = 0

        # Check if we already have the files in the data folder
        for filename in self.filenames:
            filepath = pkg_resources.resource_filename('StockApp.data', filename)
            if os.path.exists(filepath):
                if self.debug:
                    print(Fore.GREEN + f"StockAnalysis::Research::get_ticker_symbols File '{filename}' found in data folder." + Style.RESET_ALL)
                count += 1

        # If all files are found in the data folder, skip download
        if count == len(self.filenames):
            if self.debug:
                print(Fore.GREEN + "StockAnalysis::Research::get_ticker_symbols Skipping download as all files are already present." + Style.RESET_ALL)
        else:
            # Connect to FTP server and download missing files
            ftp_server = ftplib.FTP("ftp.nasdaqtrader.com")
            ftp_server.login()
            ftp_server.cwd('Symboldirectory')

            for filename in self.filenames:
                local_filepath = pkg_resources.resource_filename('StockApp.data', filename)
                if not os.path.exists(local_filepath):
                    with open(local_filepath, "wb") as file:
                        ftp_server.retrbinary(f"RETR {filename}", file.write)
                    if self.debug:
                        print(Fore.GREEN + f"StockAnalysis::Research::get_ticker_symbols Downloaded '{filename}' from FTP server." + Style.RESET_ALL)
                else:
                    if self.debug:
                        print(Fore.GREEN + f"StockAnalysis::Research::get_ticker_symbols File '{filename}' already exists locally." + Style.RESET_ALL)

            ftp_server.quit()

    def list_ticker_symbols(self):
        filepath = pkg_resources.resource_filename('StockApp.data', "nasdaqlisted.txt")
        df = pd.read_csv(filepath, sep="|")
        filepath = pkg_resources.resource_filename('StockApp.data', "otherlisted.txt")
        df2 = pd.read_csv(filepath, sep="|")
        # filter out ETFs
        filtered_df1 = df[df['ETF'] != "Y"]
        filtered_df2 = df2[df2['ETF'] != "Y"]
        # Combine into one dataframe
        combined_df = pd.concat([filtered_df1, filtered_df2], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['Symbol'])
        if self.debug:
            print(combined_df.head(3))
            print("StockAnalysis::Research::list_ticker_symbols Total Tickers: ", len(combined_df))
        tickers = combined_df['Symbol'].to_list()
        filtered_tickers = [value for value in tickers if isinstance(value, str) and not value.startswith("File")]
        return filtered_tickers

    def compare_files(self, file1, file2):
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()

        # Find lines that are in file1 but not in file2
        lines_unique_to_file1 = [line.strip() for line in lines1 if line.strip() not in lines2]

        # Find lines that are in file2 but not in file1
        lines_unique_to_file2 = [line.strip() for line in lines2 if line.strip() not in lines1]

        return lines_unique_to_file1, lines_unique_to_file2

    def choose_tickers(self, my_list, number):
        random_tickers = random.sample(my_list, number)
        if self.debug:
            print("StockAnalysis::Research::choose_tickers Tickers Chosen --> ", random_tickers)
        return random_tickers

    def grab_dogs_of_the_dow(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)

        # Send a GET request to the Dogs of the Dow website
        url = 'https://www.dogsofthedow.com/dogday.htm'
        driver.get(url)
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # if self.debug:
        #     print("StockAnalysis::Research::grab_dogs_of_the_dow --> Soup: ", soup)
        # Find the table containing the tickers
        table = soup.find('table', class_='tablepress tablepress-id-5 tablepress-responsive dataTable no-footer')
        # Extract tickers from the table
        tickers = []
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header row
                ticker = row.find_all('td')[0].text.strip()
                tickers.append(ticker)
            if self.debug:
                # Print the extracted tickers
                print("StockAnalysis::Research::grab_dogs_of_the_dow --> " \
                "Tickers from Dogs of the Dow:")
                for ticker in tickers:
                    print(ticker)

        else:
            print(Fore.RED + "FATAL ERROR StockAnalysis::Research::grab_dogs_of_the_dow " \
            "--> Failed to find Table of tickers." + Style.RESET_ALL)

        driver.quit()
        return soup

    def find_and_print_soup_content(self, soup, target_word, content_amount=1000):
        # Find all text elements in the soup
        text_elements = soup.find_all(text=True)

        # Join all text elements into a single string
        full_text = ' '.join(text_elements)

        # Find the index of the target word in the full text
        word_index = full_text.find(target_word)

        if word_index != -1:
            # Extract 100 words before and after the target word
            context_start = max(0, word_index - content_amount)
            context_end = min(len(full_text), word_index + len(target_word) + content_amount)
            context = full_text[context_start:context_end]
            # Print the context
            print("Context around '{}':".format(target_word))
            print(context)
        else:
            print("Word '{}' not found in the text.".format(target_word))

    def find_elements_by_keyword(self, soup, keyword):
        # Find all elements containing the keyword in their text or attributes
        elements = soup.find_all(lambda tag: keyword in tag.text or keyword in tag.get('class', []))
        #elements = soup.find_all(lambda tag: tag.name if tag.name else '').find_all(text=lambda text: keyword in text or keyword in tag.get('class', []))
        # Print the found elements
        if self.debug:
            for element in elements:
                print(element)
        return elements

    # Example usage:
    # Assuming 'soup' is the BeautifulSoup object and 'keyword' is the keyword to search for
    # Replace 'soup' and 'keyword' with your specific values

    # Find elements containing the keyword
    #found_elements = find_elements_by_keyword(soup, 'Symbol')
