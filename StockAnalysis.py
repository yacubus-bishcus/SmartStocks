from datetime import datetime, timedelta
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from colorama import Fore, Style
import pandas_datareader.data as web
import numpy as np
import pandas as pd
from openpyxl import load_workbook
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

# My Modules 
from Model_Handler import Model_Handler
from Stock import Stock, IndexStock
from MonteCarlo import MonteCarlo
from Simulation_Analysis import Simulation_Analysis

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
            logger.info(model_result)
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
            output.add_to_report_card('mse',mse)
            output.add_to_report_card('r_squared',r_squared)
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

        return norm_df

    def conduct_simulations(self, history):
        sim_analysis = Simulation_Analysis(self.args)
        drift, volatility = sim_analysis.calculate_drift_and_volatility(history['Close']) # takes series of the closed prices

        if self.args.price_model == "high_low":
            monte = MonteCarlo(data=history, num_simulations=self.args.simulations, sim_time=self.args.sim_time, processes=self.args.processes, jump_param=self.args.jump_parameter, apply_function=sim_analysis.stock_price_processing_high_low)
        elif self.args.price_model == "close_open":
            monte = MonteCarlo(data=history, num_simulations=self.args.simulations, sim_time=self.args.sim_time, processes=self.args.processes, jump_param=self.args.jump_parameter, apply_function=sim_analysis.stock_price_processing_close_open)

        monte.calculate_initial_condition(['avg_prices', 'historical_returns'])

        if self.args.processes > 1:
            if self.args.simulation_model == "gaussian":
                simulated_price = monte.execute_normal_simulation_with_mp(drift=drift, volatility=volatility)
            elif self.args.simulation_model == "poisson-gamma":
                simulated_price = monte.execute_poisson_gamma_simulation_with_mp()
        else:
            if self.args.simulation_model == "gaussian":
                simulated_price = monte.execute_normal_simulation(drift=drift, volatility=volatility) # all simulated prices for individual stock
            elif self.args.simulation_model == "poisson-gamma":
                beta_guess = np.var(history['Close']) / np.mean(history['Close'])
                alpha_guess = (np.mean(history['Close']) / np.var(history['Close'])) **2.
                simulated_price = monte.execute_poisson_gamma_simulation(alpha_guess, beta_guess)

        sim_df = pd.DataFrame(simulated_price) # write to 2-D dataframe

        del simulated_price

        return sim_df.mean(axis=0) # returns just one price per day

    def write_to_excel(self, df, sheet_name):
        # Define the file path
        filepath = pkg_resources.resource_filename('output', 'Historicals.xlsx')

        # Check if the file already exists
        if os.path.exists(filepath):
            # Load the existing workbook
            book = load_workbook(filepath)
            with pd.ExcelWriter(filepath, engine='openpyxl', mode='a') as writer:
                # Assign the workbook and existing sheets to the writer
                writer.book = book
                writer.sheets = {ws.title: ws for ws in book.worksheets}
                
                # Write the DataFrame to the specified sheet
                df.to_excel(writer, index=True, sheet_name=sheet_name)
                
        else:
            # Create a new workbook and write the DataFrame to it
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=True, sheet_name=sheet_name)

    def pull_top_performers(self, df, tickers, filter=3):
        top_history_df = pd.DataFrame()
        if len(tickers) > filter:
            try:
                top_performers = df.nlargest(filter, 'WAM') # finds the stock with the largest WAM
            except Exception as e:
                logger.info(df)
                logger.exception(Fore.RED + f"FATAL ERROR {e}" + Style.RESET_ALL)
                sys.exit(1)

            top_df = pd.DataFrame(top_performers)
            top_df_tickers = top_df.iloc[:,0].tolist()
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
        low_history_df = pd.DataFrame()
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
        filepath = pkg_resources.resource_filename('output', "Historicals.xlsx")
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
    def execute_stock_program(self, args):
        if not isinstance(self.stock_list, Ticker):
            for stock in self.stock_list:
                result = self.define_stock_program(stock, args)
        else:
            result = self.define_stock_program(self.stock_list, args)

        return result

    def define_stock_program(self, stock, args):
        stock_compare = None
        stock_compare2 = None
        stock_compare3 = None

       
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
            return stock_compare.return_string_difference()


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
