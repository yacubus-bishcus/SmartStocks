from datetime import datetime, timedelta
from colorama import Fore, Style
import pandas_datareader.data as web
import numpy as np
from tqdm import tqdm
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler, PowerTransformer
import os
import sys
import pkg_resources
import requests
import logging
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from yfinance import Ticker
import matplotlib.pyplot as plt 

# My Modules 
from Model_Handler import Model_Handler
from SmartStocksStock import Stock, IndexStock
from MonteCarlo import MonteCarlo
from Simulation_Analysis import Simulation_Analysis
from DateGenerator import DateGenerator
from Models import MACD 

logger = logging.getLogger(__name__)

class Analysis: # takes inputs of stocks (Ticker objects) and args from Argsparser 
    def __init__(self, stock_list=None, args=None):
        self.stock_list = stock_list
        self._risk_free_rate = None
        self.args = args
        self.total_cuts = 0
        self._recommendations = None
        self.index_stock = None 
        self.index_stock1 = None
        self.index_stock2 = None 
        self.index_stock3 = None 
    
    def __del__(self):
        pass
    
    # Attributes here 
    @property 
    def risk_free_rate(self):
        return self._risk_free_rate
    
    @property 
    def recommendations(self):
        return self._recommendations
## -----------------------------------------------------------------------------------------##
## -----------------------------FUNCTIONS FOR MONTHLY REPORT ---- --------------------------##
## -----------------------------------------------------------------------------------------##
    def return_api_key(self):
        return '229A9YWEQTI3G0O5'

    def set_args_once(self, args):
        if not self.args_set:
            self.args = args
            self.args_set = True
            logger.debug("Analysis::set_args_once --> Args set.")
        else:
            logger.debug("Analysis::set_args_once --> Args already set.")

    def determine_risk_free_rate(self):
        # use historical data for the 10 year US treasury bond yield
        # only looking at past year data
        treasury_yield_data = None
        logger.info("Determining Risk Free Rate From FRED DATA...")
        try:
            treasury_yield_data = web.DataReader('DGS10','fred',(datetime.today() - timedelta(days=30 * 12)).date(), (datetime.today() - timedelta(days=1)).date())
        except requests.exceptions.ConnectionError as e:
            logger.exception("Error Unable to connect to FRED. Please check your internet connection and try again.")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"An unexpected error occured: {e}")
            sys.exit(1)

        if treasury_yield_data is None:
            logger.error(Fore.RED + "Analysis::determine_risk_free_rate --> Treasury Yield Data Missing. Check Internet Connection." + Style.RESET_ALL)
            self.risk_free_rate = None
            sys.exit(1)
    # Get the latest risk-free rate (last available value)
        self._risk_free_rate = treasury_yield_data['DGS10'].iloc[-1] / 100  # Convert percentage to decimal
        logger.info(f"Risk Free Rate Determined --> {self._risk_free_rate}")
        logger.debug(f"Risk Free Rate --> {self._risk_free_rate}")

    """
    Outputs a pandas DataFrame containing the normalized sums of each chosen
    models outputs. In essense create an order of merit rating system for each
    stock. Input includes a list of Stock objects, market data, chosen_models
    to perform, and the output object.
    """
    def determine_top_performers(self, Stock_list, market_data, chosen_models, output):
        tickers = []
        prices = []
        # iterating over ticker object in a list of ticker objects
        # making a list of ticker symbols
        for stock in Stock_list:
            tickers.append(stock.symbol)
            prices.append(stock.price)

        logger.debug(f"determine_top_performers tickers --> {tickers}")
        # Initate Model Handler to add models as necessary all calculated ratings will be from a years data
        models = Model_Handler(Stock_list=Stock_list, market_data=market_data, risk_free_rate=self.risk_free_rate)

        # Determine the total number of models to be applied to the stock
        if self.args.import_model_class is not None:
            number_of_performance_measures = len(chosen_models) + len(self.args.import_model_class)
        else:
            number_of_performance_measures = len(chosen_models)

        # Initialize performance array based on the number of stocks and the
        # total number of models to be applied to the stock
        performance = np.zeros((len(Stock_list), number_of_performance_measures), dtype=float)
        logger.info(f"Performance Matrix Created Stock List: {len(Stock_list)} and Performance Measures: {number_of_performance_measures}")
        # IF THE USER is assigning their own model to the stock this code will
        # execute the model using execute_model method and place the output in
        # the performance array assign models also outputs the model name from
        # get_name method.
        if self.args.import_model_class != "" and self.args.import_model_class is not None:
            model_names = []
            for i, (module, class_name) in enumerate(zip(self.args.import_model_module, self.args.import_model_class)):
                performance[:, i], model_name = self.assign_models(module, class_name, Stock_list, market_data)
                model_names.append(model_name)

        # IF THE USER is assigned their own model AND they want the program
        # internal models to be used this code executes the program internal
        # models and adds their outputs to the performance array. Again the
        # performance array here contains each models output for each given
        # stock. the data here is yet to be normalized or labled.
        if len(chosen_models) > 1:
            for index, model in enumerate(chosen_models):
                if self.args.import_model_class is not None:
                    if models.add_model(model) is not None:
                        performance[:, index + len(self.args.import_model_class)] = models.add_model(model)
                else:
                    if models.add_model(model) is not None:
                        logger.debug(f"Index: {index} Model: {model}")
                        logger.debug(models.add_model(model))
                        performance[:, index] = models.add_model(model)
        else:
            model = chosen_models[0]
            index = 0
            model_result = models.add_model(model)
            performance[:, index] = model_result

        # Assign column names based on the models used names
        if self.args.import_model_class is not None:
            columns = model_names + chosen_models
        else:
            columns = chosen_models

        # create a pandas DataFrame given the performance array and apply labels
        perf_df = pd.DataFrame(performance, columns=columns, index=tickers)

        # Apply weights if provided
        if self.args.weights:
            for col, weight in self.args.weights.items():
                perf_df[col] *= weight

        # Calculate the WAM column
        row_sums = perf_df.sum(axis=1)
        perf_df['WAM'] = row_sums

        # normalize the models scores
        # Exclude 'WAM' column when fitting the scalar
        # only complete this analysis when sample size is larger than 5 
        if len(Stock_list) > 5 and number_of_performance_measures > 1:
            # Handle NaN values before scaling
            perf_df = perf_df.fillna(perf_df.mean())
            my_scaler = PowerTransformer(method='yeo-johnson')
            norm_df = pd.DataFrame(my_scaler.fit_transform(perf_df.drop(columns=['WAM'])), columns=perf_df.drop(columns=['WAM']).columns, index=perf_df.index)
            # add the WAM column back to the normalized dataframe
            norm_df['WAM'] = perf_df['WAM']
            # Prepare features and target variables
            X = norm_df[columns]
            Y = norm_df['WAM']

            # split the data into training and test sets
            X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.1, random_state=self.args.seed)

            # Train the model
            regression_model = LinearRegression()
            regression_model.fit(X_train, y_train)

            # Evaluate the model on the test set
            y_pred_test = regression_model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred_test)
            r_squared = regression_model.score(X_test, y_test)
            output.mse = mse
            output.r_squared = r_squared
            logger.info(f"Mean Squared Error: {mse}")
            logger.info(f"R-squared: {r_squared}")

            # make predictions for all stocks
            X_all_scaled = my_scaler.transform(perf_df.drop(columns=['WAM'])) # transform all data not just test set
            X_all_scaled_df = pd.DataFrame(X_all_scaled, columns=columns, index=perf_df.index)
            y_pred_all = regression_model.predict(X_all_scaled_df)
            norm_df['SAM'] = y_pred_all

            # After calculations format for output
            norm_df['Price'] = prices
            norm_df.insert(0, 'Symbol', tickers)
            #norm_df.columns.values[0] = 'Stock'
            norm_df = norm_df.round(2)
            # return dataframe of performance metrics and a list of dataframes of
            #simualation results where each index of the list is the simulation for
            #a given stock
        else:
            norm_df = perf_df 
            norm_df['SAM'] = norm_df['WAM']

        return norm_df.round(3)

    def calculate_futures(self, stock_list, output=None):
        logger.info("Grabbing Market Data...")
        market_index = IndexStock(period=self.args.model_period, interval=self.args.model_interval)
        market_index.index = self.args.index # for history its just market_index.index.history 
        market_data = market_index.index.history 

        if market_data is None:
            logger.error(Fore.RED + "conduct_report --> market_data is empty. Check Internet Connection." + Style.RESET_ALL)
            return
        
        if len(stock_list) > 0:
            filtered_stocks = []
            filtered_tickers = []
            filtered_prices = []
            logger.info("Processing Stocks...")
            for stock in tqdm(stock_list, desc="Stocks"):
                my_stock = Stock(stock, self.args.model_period, self.args.model_interval)
                if not self.apply_cuts(my_stock):
                    filtered_stocks.append(my_stock)
                    filtered_tickers.append(my_stock.symbol)
                    filtered_prices.append(my_stock.price)

            logger.info("Data Processing Complete.")
            logger.info(f"Total Number of Stocks Cut --> {self.total_cuts}")
        if self.args.simulations > 0:
            model_histories = []
            for stock in filtered_stocks:
                model_histories.append(stock.history) 
            
            future_prices_list = []
            future_stds_list = []
            for history in tqdm(model_histories, desc='Stocks Simulation'):
                future_price, stock_stds = self.conduct_simulations(history) # future_price and stock_stds should be returned as series 
                future_prices_list.append(future_price)
                future_stds_list.append(stock_stds) 

            future_prices = pd.DataFrame(future_prices_list)
            future_prices.index = filtered_tickers 
            future_stds = pd.DataFrame(future_stds_list)
            future_stds.index = filtered_tickers
            future_prices = future_prices.T
            future_stds = future_stds.T
            date_gen = DateGenerator(self.args)
            dates = date_gen.generate_dates_with_intervals()
            future_prices['Date'] = dates 
            future_prices.set_index('Date', inplace=True)

            if self.args.include_history:
                close_histories_list = []
                for i in range(int(self.args.number_to_highlight)):
                    close_histories_list.append(model_histories[i]['Close'])

                close_histories = pd.DataFrame(close_histories_list)
                close_histories.index = filtered_tickers
                close_histories = close_histories.T

                combined_df = pd.concat([close_histories, future_prices], axis=0, ignore_index=False)
                combined_df.index = combined_df.index.rename('Date')
            if output is not None:
                sheet_name = "Future_Prices" + datetime.today().strftime('%b_%d')
                output.write_to_excel(df=future_prices, sheet_name=sheet_name, data_w_dates=True)
            if self.args.sim_market:
                df, stds = self.conduct_simulations(market_data)
                market_df = pd.DataFrame(df)
                market_stds_df = pd.DataFrame(stds)
                date_gen = DateGenerator(self.args)
                dates = date_gen.generate_dates_with_intervals()
                market_df['Date'] = dates
                market_df.set_index('Date', inplace=True)
                market_df.columns = ['Index Price']
                if self.args.include_history:
                    market_history_df = pd.DataFrame(market_data['Close'])
                    market_history_df.columns = ['Index Price']
                    # combine the market history with market futures
                    combined_market_df = pd.concat([market_history_df, market_df], axis=0, ignore_index=False)
                    combined_market_df.index = combined_market_df.index.rename('Date')
            
            model_handler = Model_Handler(Stock_list=filtered_stocks, market_data=market_data, args=self.args)
            
            if self.args.sim_market:
                if self.args.include_history:
                    model_handler.pass_futures_market_data(combined_market_df)
                    model_handler.pass_futures_data(combined_df)
                else:
                    model_handler.pass_futures_market_data(market_df, market_stds_df)
                    model_handler.pass_futures_data(future_prices, future_stds)
            else:
                if self.args.include_history:
                    model_handler.pass_futures_data(combined_df)
                else:
                    model_handler.pass_futures_data(future_prices, future_stds)

            model = model_handler.get_futures_instance()
            figure = model.plot(stock_name="Stocks", current_prices=filtered_prices, show_every_nth_errorbar=self.args.show_every_nth_errorbar)
            caption = model.caption 
            if figure is not None:
                figure.text(0.5,-0.2, caption, ha='center', fontsize=8)
                figure.tight_layout(pad=2.0)

                return figure
    
    def conduct_simulations(self, history):
        sim_analysis = Simulation_Analysis()
        macd = MACD()
        avg_bull_adj, avg_bear_adj = macd.calculate_historical_adjustments(history['Close'])
        drift, volatility = sim_analysis.calculate_drift_and_volatility(history['Close'], self.args.use_log_returns) # takes series of the closed prices
        stds_6 = 6*np.std(history['Close'])
        min_cap = history['Close'][-1] - stds_6 
        max_cap = history['Close'][-1] + stds_6 
        logger.info(f"Minimum Cap set to: {min_cap}")
        logger.info(f"Maximum Cap set to: {max_cap}")
        
        if self.args.model_period == "1d":
            model_period = 1
        elif self.args.model_period == "5d":
            model_period = 5
        elif self.args.model_period == "1mo":
            model_period = 30 
        elif self.args.model_period == "3mo":
            model_period = 90 
        elif self.args.model_period == "6mo":
            model_period = 182 
        elif self.args.model_period == "1y":
            model_period = 365
        elif self.args.model_period == "2y":
            model_period = 2*365
        elif self.args.model_period == "5y":
            model_period = 5*365
        elif self.args.model_period == "10y":
            model_period = 10*365 
        elif self.args.model_period == "ytd":
            model_period = 365 
        else:
            logger.error("Model Period Could not be found. Default using 1mo (30).")
            model_period = 30 

        if self.args.price_model == "high_low":
            monte = MonteCarlo(data=history, num_simulations=self.args.simulations, sim_time=self.args.sim_time, history_time=model_period, processes=self.args.processes, jump_param=self.args.jump_parameter, apply_function=sim_analysis.stock_price_processing_high_low)
        elif self.args.price_model == "close_open":
            monte = MonteCarlo(data=history, num_simulations=self.args.simulations, sim_time=self.args.sim_time, history_time=model_period, processes=self.args.processes, jump_param=self.args.jump_parameter, apply_function=sim_analysis.stock_price_processing_close_open)

        monte.calculate_initial_condition(['avg_prices', 'historical_returns'])
        monte.head_shoulders_window = self.args.h_s_window
        monte.seed = self.args.seed
        average_reduction = sim_analysis.calculate_average_reduction(prices=history['Close'], window_size=self.args.h_s_window)
        if self.args.model_interval == "1m":
            interval_minutes = 1
        elif self.args.model_interval == "2m":
            interval_minutes = 2
        elif self.args.model_interval == "5m":
            interval_minutes = 5
        elif self.args.model_interval == "15m":
            interval_minutes = 15
        elif self.args.model_interval == "30m":
            interval_minutes = 30
        elif self.args.model_interval == "60m":
            interval_minutes = 60 
        elif self.args.model_interval == "90m":
            interval_minutes = 90
        elif self.args.model_interval == "1h":
            interval_minutes = 60 
        elif self.args.model_interval == "1d":
            interval_minutes = 24*60 
        else:
            logger.error(f"Interval Minutes could not be set by Model Interval {self.args.model_interval}. Applying interval of 1m.")
            interval_minutes = 1

        interval_means, interval_stds = monte.execute_normal_simulation_with_mp(drift=drift,
                                                                                volatility=volatility,
                                                                                interval_minutes=interval_minutes,
                                                                                average_reduction=average_reduction,
                                                                                bull=avg_bull_adj,
                                                                                bear=avg_bear_adj,
                                                                                min_cap=min_cap,
                                                                                max_cap=max_cap,
                                                                                incremental_adjustment_steps=self.args.incremental_steps)
        
        sim_df = pd.Series(interval_means) # returned as series 
        std_df = pd.Series(interval_stds) # returned as series 
        return sim_df, std_df # returns just one price per interval

    def pull_top_performers(self, df, tickers, filter=3):
        if len(tickers) >= filter:
            try:
                top_performers = df.nlargest(filter, 'WAM') # finds the stock with the largest WAM
                logger.debug("Top Performers Pulled.")
            except Exception as e:
                logger.info(df)
                logger.exception(Fore.RED + f"FATAL ERROR {e}" + Style.RESET_ALL)
                sys.exit(1)

            top_df = pd.DataFrame(top_performers)
            top_df_tickers = top_df.index.tolist()
        else:
            logger.error(Fore.YELLOW + "USER ERROR:" \
             "Requesting more Performers than Researched. This could result " \
             "from too many of the researched stocks being filtered based on "\
             "your filters. Try increasing the amount of stocks researched, "\
             "change your filters, or decrease your --number_to_highlight and "\
             "try again." + Style.RESET_ALL)
            sys.exit(1)

        return top_df, top_df_tickers

    def pull_worst_performers(self, df, tickers, filter=3):
        if len(tickers) > filter:
            try:
                low_performers = df.nsmallest(filter, 'WAM') # finds the stock with the smallest WAM
            except Exception as e:
                logger.info(df)
                logger.exception(Fore.RED + f"FATAL ERROR {e}" + Style.RESET_ALL)
                sys.exit(1)

            low_df = pd.DataFrame(low_performers)
            low_df_tickers = low_df.iloc[:,0].tolist()
        else:
            logger.error(Fore.YELLOW + "USER ERROR:" \
             "Requesting more Performers than Researched. This could result " \
             "from too many of the researched stocks being filtered based on "\
             "your filters. Try increasing the amount of stocks researched, "\
             "change your filters, or decrease your --number_to_highlight and "\
             "try again." + Style.RESET_ALL)
            sys.exit(1)

        return low_df, low_df_tickers

    """
    Very Important function. Assigns models and returns their outputs. These
    outputs will be distributed over the same time period for a given report
    that way the stocks can be compared 'apples to apples'. This function allows
    user to add models to Models.py directly or, as preferred, there own module
    and class. Any imported models must have the following methods: execute_model,
    get_name, get_caption, and plot for the model to be used properly.
    """

    def assign_models(self, module, class_name, stock_list, market_data):
        # Initiate Model_Handler class must input anything required for models
        models = Model_Handler(stock_list, market_data, self.risk_free_rate, self.args)

        # Check if user is importing their own model
        # User model must have two methods 'enter_inputs' and 'execute_model'
        if self.args.import_model_class != "" and self.import_model_module != "":
            try:
                imported_model = models.import_model(module, class_name)
                attributes = ['execute_model', 'get_name', 'get_caption', 'plot']
                if all(hasattr(imported_model, attr) for attr in attributes):
                    # Provide user the option to pull from default models parameters
                    # this function with inputs has not been tested
                    if models.requires_inputs(imported_model.execute_model):
                        inputs = self.grab_useful_parameters(stock_list, market_data)
                        return imported_model.execute_model(*inputs), imported_model.get_name()
                    else:
                        return imported_model.execute_model(), imported_model.get_name()
                else:
                    logger.error(Fore.RED + "USER ERROR: USERs imported module " \
                    "must have four methods: 'execute_model', 'get_name'"\
                    ", 'get_caption', and 'plot'."\
                    "execute_model executes the models calculations." \
                    "get_name returns the name of the model" \
                    "get_caption returns the plot caption for the model" \
                    "plot returns the plotting figure for the model calculation"\
                    "SEE EXAMPLES PROVIDED in Models.py." + Style.RESET_ALL)
            except Exception as e:
                logger.exception(Fore.RED + f"Error --> {e}" + Style.RESET_ALL)
                return None, ""
        else:
            return None, ""

    # Return parameters used by our Model_Handler class
    def grab_useful_parameters(self, stock_list, market_data):
        return stock_list, market_data, self.risk_free_rate, self.time_delta

    # Apply Cuts method called in conduct_report input is a Stock object
    def apply_cuts(self, stock):
        # filter out any penny stock tickers
        # Additionally if a stock does not have a price check if its from one
        # of the research files and filter it out for future reference
        if stock.price is None:
            self.total_cuts += 1
            logger.warning(f"{stock.name} does not have a price, cutting.")
            return True
        if stock.price < float(self.args.min_price) or stock.price > float(self.args.max_price):
            self.total_cuts += 1
            logger.warning(f"{stock.name} is out of the price range, cutting.")
            return True
        # Filter out any ETFs
        if stock.is_etf:
            self.total_cuts += 1
            logger.warning(f"{stock.name} is an etf, cutting.")
            return True
        # Ensure fifty percent is not none
        if stock.fifty_percent is None:
            self.total_cuts += 1
            logger.warning(f"{stock.name} does not have a 50 day, cutting.")
            return True
        # Ensure two hundred percent is not none
        if stock.twohundred_percent is None:
            self.total_cuts += 1
            logger.warning(f"{stock.name} does not have a 200 day, cutting")
            return True

        # make sure stocks have history we need
        # Ensure history is not none

   
    def read_table(self, sheet_name):
        if self.args.output.endswith(".docx"):
            filename = self.args.output.replace(".docx", ".xlsx")
        else:
            filename = self.args.output + ".xlsx"

        filepath = pkg_resources.resource_filename('output', filename)
        df = pd.DataFrame()
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name)
        except Exception as e:
            logger.exception(Fore.RED + f"Error --> {e}" + Style.RESET_ALL)
        return df
## -----------------------------------------------------------------------------------------##
## -----------------------------EXECUTE STOCK PROGRAM ----------- --------------------------##
## -----------------------------------------------------------------------------------------##
    """
    Early design functions for simple tasks such as compare two stocks 50 day
    averages and the like. No reporting methods, modeling methods
    or simulation methods below. execute_stock_program takes 
    """
    def execute_stock_program(self):
        result = None 
        if not isinstance(self.stock_list, Ticker):
            for stock in self.stock_list:
                result = self.define_stock_program(stock)
        else:
            result = self.define_stock_program(self.stock_list)

        return result

    def define_stock_program(self, stock):
        stock_compare = None
        stock_compare2 = None
        stock_compare3 = None
        args = self.args 
       
        if self.index_stock is None:
            logger.info(f"Initializing IndexStock with ticker: {args.index}")
            self.index_stock = IndexStock(args.model_period, args.model_interval)
            self.index_stock.index = args.index 

        stock = Stock(stock, args.model_period, args.model_interval)

        ## ------------------ APPLY FILTERS HERE ------------------------##
        # filter out any penny stock tickers
        if stock.price is None:
            logger.warning("NO STOCK PRICE FOUND!")
            return

        if not isinstance(self.stock_list, Ticker):
            if stock.price < float(args.min_price) or stock.price > float(args.max_price):
                logger.warning(f"{stock.name} is out of the price range, skipping.")
                return

        self._recommendations = stock.recommendations
           
        if args.c:
            stock.print_daily_change()

        if args.c_50:
            stock.print_50_change()

        if args.c_200:
            stock.print_200_change()

        if any([args.compare_index, args.compare_index_50, args.compare_index_200]):
            stock_compare = CompareStocks(stock, self.index_stock.index)
            if args.compare_index:
                stock_compare.compare_daily_stocks()
                stock_compare.print_difference()
            if args.compare_index_50:
                stock_compare.compare_50_day_stocks()
                stock_compare.print_difference()
            if args.compare_index_200:
                stock_compare.compare_200_day_stocks()
                stock_compare.print_difference()

        if any([args.compare_Daily, args.compare_50, args.compare_200]):
            if not all([self.index_stock1, self.index_stock2, self.index_stock3]):
                self.index_stock1 = IndexStock(args.model_period, args.model_interval)
                self.index_stock1.index = "^GSPC"
                self.index_stock2= IndexStock(args.model_period, args.model_interval)
                self.index_stock2.index = "^DJI"
                self.index_stock3 = IndexStock(args.model_period, args.model_interval)
                self.index_stock3.index = "^IXIC"
            stock_compare = CompareStocks(stock, self.index_stock1.index)
            stock_compare2 = CompareStocks(stock, self.index_stock2.index)
            stock_compare3 = CompareStocks(stock, self.index_stock3.index)
            
            if args.compare_Daily:
                stock_compare.compare_daily_stocks()
                stock_compare2.compare_daily_stocks()
                stock_compare3.compare_daily_stocks()
                stock_compare.print_difference()
                stock_compare2.print_difference()
                stock_compare3.print_difference()
            if args.compare_50:
                stock_compare.compare_50_day_stocks()
                stock_compare2.compare_50_day_stocks()
                stock_compare3.compare_50_day_stocks()
                stock_compare.print_difference()
                stock_compare2.print_difference()
                stock_compare3.print_difference()
            if args.compare_200:
                stock_compare.compare_200_day_stocks()
                stock_compare2.compare_200_day_stocks()
                stock_compare3.compare_200_day_stocks()
                stock_compare.print_difference()
                stock_compare2.print_difference()
                stock_compare3.print_difference()
       

        if all([stock_compare, stock_compare2, stock_compare3]):
            return stock_compare.return_string_difference(), stock_compare2.return_string_difference(), stock_compare3.return_string_difference()
        elif any([args.c, args.c_50, args.c_200]):
            return None 
        else:
            if stock_compare is not None:
                return stock_compare.return_string_difference()
            else:
                return None 


## -----------------------------------------------------------------------------------------##
## ----------------------------- CompareStocks CLASS    ----------- ------------------------##
## -----------------------------------------------------------------------------------------##

class CompareStocks:
    def __init__(self, stock1=None, stock2=None):
        self.stock1 = stock1
        self.stock2 = stock2
        self.difference = 0.

    def compare_daily_stocks(self):
        if self.stock1.daily_percent and self.stock2.daily_percent:
            self.difference = round(self.stock1.daily_percent - self.stock2.daily_percent, 2)

    def compare_50_day_stocks(self):
        if self.stock1.fifty_percent and self.stock2.fifty_percent:
            self.difference = round(self.stock1.fifty_percent - self.stock2.fifty_percent, 2)
        else:
            logger.error("DATA ERROR: compare_50_day_stocks")

    def compare_200_day_stocks(self):
        if self.stock1.twohundred_percent and self.stock2.twohundred_percent:
            self.difference = round(self.stock1.twohundred_percent - self.stock2.twohundred_percent, 2)

    def print_difference(self):
        if self.difference > 0:
            print(self.stock1.name, " is outperforming ", self.stock2.name, " by ", Fore.GREEN + str(self.difference) + Style.RESET_ALL, " percent.")
        else:
            print(self.stock1.name, " is underperforming ", self.stock2.name, " by ", Fore.RED + str(self.difference) + Style.RESET_ALL, " percent.")

    def return_string_difference(self):
        if self.difference > 0:
            string = self.stock1.name + " is outperforming " + self.stock2.name + " by " + str(self.difference) + " percent."
        else:
            string = self.stock1.name + " is underperforming " + self.stock2.name, " by " + str(self.difference) + " percent."

        return string


## -----------------------------------------------------------------------------------------##
## ----------------------------- DataAnalysis CLASS    ----------- ------------------------##
## -----------------------------------------------------------------------------------------##

class DataAnalysis:
    def __init__(self, directory=None, files=[], sheet_name=None):
        if directory is None:
            # Get the current working directory
            current_directory = os.getcwd()
            self._directory = current_directory
        else: 
            self._directory = directory 

        self._files = files 
        if sheet_name is None:
            self._sheet_name = "Future_Prices" + datetime.today().strftime('%b_%d')
        else:
            self._sheet_name = sheet_name 

        self._fig = None 

    def __del__(self):
        pass 
    
    @property 
    def fig(self):
        return self._fig 
    
    @fig.setter 
    def fig(self, value):
        self._fig = value 

    @property 
    def directory(self):
        return self._directory
    
    @directory.setter 
    def directory(self, value):
        self._directory = value 

    @property 
    def sheet_name(self):
        return self._sheet_name 
    
    @sheet_name.setter 
    def sheet_name(self, value):
        self._sheet_name = value 

    @property 
    def files(self):
        return self._files
    
    @files.setter # example use object.files = (test*sims.xlsx, [1,2,3,4])
    def files(self, value):
        base_filename, numbers = value 
        filenames = []
        for number in numbers:
            complete_filename = base_filename.replace('*', str(number))
            filenames.append(complete_filename)
        
        self._files.append(filenames) 
    
    def reset_files(self):
        self._files = [] 

    @directory.setter 
    def directory(self, value):
        self._directory = value 

    def read_table(self, sheet_name):
        df_list = []
        for filename in self.files:
            filepath = os.path.join(self.directory, filename[0])
            try:
                df = pd.read_excel(filepath, sheet_name=sheet_name)
            except Exception as e:
                logger.exception(f"Error: {e}")
                continue
            df_list.append(df)
        return df_list
            

    
    def plot(self, column_names, title="Plots from Files", ylabel="Prices", show=True):
        df_list = self.read_table(sheet_name=self.sheet_name)
        self._fig = plt.figure(figsize=(10, 6))
        i = 0
        for df in df_list:
            plt.plot(df[column_names[0]], df[column_names[1]], label=self.files[i])
            i += 1 
        
        plt.xlabel(column_names[0])
        plt.ylabel(ylabel)
        plt.title(title)
        plt.legend() 
        if show:
            plt.show() 

        return self.fig 
    
    def figsave(self, filename):
        filepath = os.path.join(self.directory, filename)
        if self.fig is not None:
            self.fig.savefig(filepath)
        else:
            logger.error("No figure to save.")