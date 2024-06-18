from StockApp.Model_Handler import Model_Handler
from StockApp.Stock import MyStock, Index_Stocks
from StockApp.MonteCarlo import MonteCarlo
from StockApp.Simulation_Analysis import Simulation_Analysis
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
from tqdm import tqdm
import logging
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from scipy.stats import poisson, gamma
from scipy.optimize import minimize
from scipy.special import gamma, gammaln


logger = logging.getLogger(__name__)

class Analysis:
    def __init__(self, stock_list=None, args=None):
        self.stock_list = stock_list
        self.myIndexStock = None
        self.risk_free_rate = None
        self.args = args
        self.today = datetime.today()
        self.total_cuts = 0
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
            logger.debug("StockAnalysis::Analysis::set_args_once --> Args set.")
        else:
            logger.debug("StockAnalysis::Analysis::set_args_once --> Args already set.")

    def conduct_report(self, output, sheet_name):
        # Initialize local variables
        top_tickers = []
        performers = pd.DataFrame()
        top_performers = pd.DataFrame()
        filename = ""
        figures = []

        if self.args.output.endswith(".docx"):
            filename = self.args.output.replace(".docx", ".png")
        filepath = pkg_resources.resource_filename('StockApp.output', filename)

        logger.info("Grabbing Market Data...")
        # Ensure you can grab market data and establish risk free rate or MODELS
        # Five year market data
        market_data = self.get_market_data(self.args.index)
        logger.info("Grabbing Simulated Market Data...")
        # user selected sim_market period time
        sim_market_data = self.get_market_data(self.args.index, self.args.model_time_delta)
        self.determine_risk_free_rate()
        logger.info("Market Data Acquired.")

        if market_data is None:
            logger.error(Fore.RED + "conduct_report --> market_data is empty. Check Internet Connection." + Style.RESET_ALL)
            return

        if sim_market_data is None:
            logger.error(Fore.RED + "conduct_report --> market_data for simulations is empty. Check Internet Connection." + Style.RESET_ALL)
            return

        if self.risk_free_rate is None:
            logger.error(Fore.RED + "conduct_monthly report::determine_risk_free_rate no return. Check Internet Connection." + Style.RESET_ALL)
            return

        # Determine top performances from list
        # apply cuts as necessary prior to determine_top_performers
        if len(self.stock_list) > 0:
            total_stocks = output.grab_report_card_value('total_stocks')
            total_stocks += len(self.stock_list)
            output.add_to_report_card('total_stocks', total_stocks)
            filtered_stocks = []
            filtered_tickers = []
            logger.info("Processing Stocks...")
            for stock in tqdm(self.stock_list, desc="Stocks"):
                my_stock = MyStock(stock, self.args)
                if not self.apply_cuts(my_stock):
                    filtered_stocks.append(my_stock)
                    filtered_tickers.append(my_stock.symbol)
            logger.info("Data Processing Complete.")
            logger.info(f"Total Number of Stocks Cut --> {self.total_cuts}")
            logger.info("Determining Top Performers...")
            performers_df, future_prices = self.determine_top_performers(filtered_stocks, market_data, self.args.models, output)
            # Write to excel file for historic comparison
            sheet_name = sheet_name + self.today.strftime('%Y_%m_%d')
            self.write_to_excel(performers_df, sheet_name)
            logger.info(f"--> Performance Data written to {sheet_name}")
            top_performers, top_tickers, empty_place_holder = self.pull_top_performers(df=performers_df, tickers=filtered_tickers, filter=int(self.args.number_to_highlight))
            if top_performers.empty or len(top_tickers) == 0:
                return

        ########################################################################
        ########## Top Performance gets a Model Graphical Page #################
        ########################################################################
        if len(self.stock_list) > 0:
            # pull_top_performers returns the dataframe and currently a number
            the_number_one, the_number_one_ticker, one_sim_df = self.pull_top_performers(df=performers_df, tickers=filtered_tickers, filter=1, future_prices=future_prices) # future_prices here is a list of dataframes for each stock
            target_stock = None
            for myStock in filtered_stocks:
                if myStock.symbol == the_number_one_ticker[0]:
                    target_stock = myStock
            if target_stock is None:
                logger.warning("Top Ticker Not Found.")
                return
            else:
                the_number_one_ticker = the_number_one_ticker[0]
                logger.info(f"Top Ticker Found: {the_number_one_ticker}")

            # Write the number one predicted stocks predicted future prices for reference
            sheet_name2 = "Future_Prices_" + the_number_one_ticker + self.today.strftime('%Y_%m_%d')
            self.write_to_excel(one_sim_df.mean(axis=0), sheet_name2)
            logger.info(f"--> Future Data written to {sheet_name2}")
            # here the model handler will be based off the user's input for time_delta
            number_one_model = Model_Handler(myStock_list=target_stock, market_data=market_data, risk_free_rate=self.risk_free_rate, args=self.args)
            number_one_model.pass_futures_data(one_sim_df)
            number_one_model.pass_futures_market_data(sim_market_data)
            number_one_model.pass_market_stock(self.myIndexStock)
            number_one_model.add_all_plotting_models()
            figures = number_one_model.plot_catcher(filepath)

        return figures, top_tickers, the_number_one_ticker, sheet_name

    def get_market_data(self, index, time_delta="5y"):
        # Check if index_stock object already exists that way you only set indexes
        # once
        if self.myIndexStock is None:
            index_stock = Index_Stocks()  # lazy initialization
            # creates
            self.myIndexStock = index_stock.create_my_index_stock(self.args.index, self.args)

        if time_delta == "5y":
            market_data = self.myIndexStock.the_5y_history
        elif time_delta == "1y":
            market_data = self.myIndexStock.the_year_history
        elif time_delta == "6mo":
            market_data = self.myIndexStock.the_6mo_history
        elif time_delta == "3mo":
            market_data = self.myIndexStock.the_3mo_history
        elif time_delta == "1mo":
            market_data = self.myIndexStock.the_month_history
        elif time_delta == "5d":
            market_data = self.myIndexStock.the_5d_history
        elif time_delta == "1d":
            market_data = self.myIndexStock.the_day_history
        else:
            logger.error(f"Get Market Data Time Delta {time_delta} not available, exiting.")
            sys.exit(1)

        market_data['daily_return'] = market_data['Close'].pct_change()

        return market_data

    def determine_risk_free_rate(self):
        # use historical data for the 10 year US treasury bond yield
        # only looking at past year data
        treasury_yield_data = None
        logger.info("Determining Risk Free Rate From FRED DATA...")
        try:
            treasury_yield_data = web.DataReader('DGS10','fred',self.start_date.date(), self.end_date.date())
        except requests.exceptions.ConnectionError as e:
            logger.exception("Error Unable to connect to FRED. Please check your internet connection and try again.")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"An unexpected error occured: {e}")
            sys.exit(1)

        if treasury_yield_data is None:
            logger.error(Fore.RED + "FATAL ERROR: StockAnalysis::Analysis::determine_risk_free_rate --> Treasury Yield Data Missing. Check Internet Connection." + Style.RESET_ALL)
            self.risk_free_rate = None
            sys.exit(1)
    # Get the latest risk-free rate (last available value)
        self.risk_free_rate = treasury_yield_data['DGS10'].iloc[-1] / 100  # Convert percentage to decimal
        logger.info(f"Risk Free Rate Determined --> {self.risk_free_rate}")
        logger.debug(f"Risk Free Rate --> {self.risk_free_rate}")

    """
    Outputs a pandas DataFrame containing the normalized sums of each chosen
    models outputs. In essense create an order of merit rating system for each
    stock. Also outputs a pandas Dataframe of the simulations output.
    Input includes a list of MyStock objects and chosen_models to perform.
    """
    def determine_top_performers(self, myStock_list, market_data, chosen_models, output):
        tickers = []
        prices = []
        histories= []
        # iterating over ticker object in a list of ticker objects
        # making a list of ticker symbols
        for stock in myStock_list:
            tickers.append(stock.symbol)
            prices.append(stock.price)
            if stock.the_5y_history is not None:
                histories.append(stock.the_5y_history) # dataframe of the stocks 5year history
            else:
                histories.append(stock.the_year_history)

        logger.debug(f"determine_top_performers tickers --> {tickers}")
        # Initate Model Handler to add models as necessary all calculated ratings will be from a years data
        models = Model_Handler(myStock_list=myStock_list, market_data=market_data, risk_free_rate=self.risk_free_rate)

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
                performance[:, i], model_name = self.assign_models(module, class_name, myStock_list, market_data)
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

        # Apply weights if provided
        if self.args.weights:
            for col, weight in self.args.weights.items():
                perf_df[col] *= weight

        # Calculate the WAM column
        row_sums = perf_df.sum(axis=1)
        perf_df['WAM'] = row_sums

        # normalize the models scores
        # Exclude 'WAM' column when fitting the scalar
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

        # Perform monte carlo simulation for each stock
        expected_future_prices = []
        simulated_prices = []
        logger.info("Conducting Monte Carlo Simulation on Each Stock...")
        sim_analysis = Simulation_Analysis(self.args)
        for history in tqdm(histories, desc='Stocks Simulation'):
            drift, volatility = sim_analysis.calculate_drift_and_volatility(history['Close']) # takes series of the closed prices

            if self.args.price_processing_model == "high_low":
                monte = MonteCarlo(data=history, num_simulations=self.args.simulations, sim_time=self.args.sim_time, processes=self.args.processes, jump_param=self.args.jump_parameter, apply_function=sim_analysis.stock_price_processing_high_low)
            elif self.args.price_processing_model == "close_open":
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
            expected_future_price = simulated_price[:,-1].mean() # at the given time period e.g. at 30 days
            expected_future_prices.append(expected_future_price) # writes it to list for all stocks
            simulated_prices.append(sim_df) # all simulations on all stocks as a list of pandas dataframes

        logger.info("Simulations complete.")
        # convert expected future prices to a pandas series
        expected_future_prices = pd.Series(expected_future_prices, index=tickers)
        #here I sum the models "scores" after normalizing
        # Apply weights if provided. need to be provided as a dictionary with keys
        # matching models used

        future_key = "MCFP " + str(self.args.sim_time) + " Days"
        norm_df[future_key] = expected_future_prices
        # After calculations format for output
        norm_df['Price'] = prices
        norm_df.insert(0, 'Symbol', tickers)
        #norm_df.columns.values[0] = 'Stock'
        norm_df = norm_df.round(2)
        # return dataframe of performance metrics and a list of dataframes of
        #simualation results where each index of the list is the simulation for
        #a given stock
        return norm_df, simulated_prices

    def write_to_excel(self, df, sheet_name):
        # Write to excel file for historic comparison
        filepath = pkg_resources.resource_filename('StockApp.output', 'Historicals.xlsx')

        if os.path.exists(filepath):
            book = load_workbook(filepath)
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                writer.book = book
                df.to_excel(writer, index=True, sheet_name=sheet_name)
                writer.save()
        else:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=True, sheet_name=sheet_name)
                writer.save()

    def pull_top_performers(self, df, tickers, filter=3, future_prices=None):
        top_history_df = pd.DataFrame()
        if len(tickers) > filter:
            try:
                top_performers = df.nlargest(filter, 'WAM') # finds the stock with the largest WAM
            except Exception as e:
                logger.info(df)
                logger.exception(Fore.RED + f"FATAL ERROR {e}" + Style.RESET_ALL)
                sys.exit(1)
            if future_prices is not None:
                # convert the list of dataframes into a series
                future_prices_series = pd.Series(future_prices, index=df.index)
                index = top_performers.index
                top_history_df = future_prices_series.loc[index] # grabs dataframe of the top stock for writing to excel and plotting
                top_history_df = pd.concat(top_history_df.tolist(), keys=index)
                #top_history_df = top_history_df.mean(axis=1)

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

        return top_df, top_df_tickers, top_history_df

    def pull_worst_performers(self, df, tickers, filter=3, future_prices=None):
        low_history_df = pd.DataFrame()
        if len(tickers) > filter:
            try:
                low_performers = df.nsmallest(filter, 'WAM') # finds the stock with the smallest WAM
            except Exception as e:
                logger.info(df)
                logger.exception(Fore.RED + f"FATAL ERROR {e}" + Style.RESET_ALL)
                sys.exit(1)
            if future_prices is not None:
                # convert the list of dataframes into a series
                future_prices_series = pd.Series(future_prices, index=df.index)
                index = low_performers.index
                low_history_df = future_prices_series.loc[index] # grabs dataframe of the top stock for writing to excel and plotting
                low_history_df = pd.concat(low_history_df.tolist(), keys=index)

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

        return low_df, low_df_tickers, low_history_df

## -----------------------------------------------------------------------------------------##
## -----------------------------EXECUTE STOCK PROGRAM ----------- --------------------------##
## -----------------------------------------------------------------------------------------##

    def execute_stock_program(self, args, output):
        if len(self.stock_list) > 1:
            for item in self.stock_list:
                self.define_stock_program(item, args, output)
        else:
            self.define_stock_program(self.stock_list, args, output)

    def define_stock_program(self, item, args, output):
        if not hasattr(self, 'index_stock'):
            index_stock = Index_Stocks()
            index_stock.set_index_info()

        stock = MyStock(item, self.args)

        ## ------------------ APPLY FILTERS HERE ------------------------##
        # filter out any penny stock tickers
        if stock.price is None:
            return
        if stock.price < float(args.min_price) or stock.price > float(args.max_price):
            logger.warning(f"{stock.name} is out of the price range, skipping.")
            return

        if args.r:
            if output is not None:
                stock.output_recommendations()
            else:
                print(stock.recommendations)

        if args.summary:
            if output is not None:
                stock.output_summary()
            else:
                stock.print_summary()

        if args.c:
            if output is not None:
                stock.output_daily_change()
            else:
                stock.print_daily_change()

        if args.c_50:
            if output is not None:
                stock.output_50_change()
            else:
                stock.print_50_change()

        if args.c_200:
            if output is not None:
                stock.output_200_change()
            else:
                stock.print_200_change()

        if args.c_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, args), args.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock,args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock, args), args.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

            stock_compare.compare_daily_stocks()

            if output is not None:
                stock_compare.output_stock_name()
                stock_compare.output_stock_current_price()
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_50_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_50_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_50_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

            stock_compare.compare_50_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_200_Dow:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.dow_stock, args), args.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_200_Nas:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.nas_stock, args), args.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_200_Sap:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

            stock_compare.compare_200_day_stocks()

            if output is not None:
                stock_compare.output_stock_name(50)
                stock_compare.output_difference()
            else:
                stock_compare.print_difference()

        if args.c_Daily:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

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

        if args.co_50:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

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

        if args.co_200:
            if output is not None:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug, output)

            else:
                stock_compare = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)
                stock_compare2 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)
                stock_compare3 = CompareStocks(stock, MyStock(index_stock.sap_stock, args), args.debug)

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
                logger.exception(Fore.RED + "Error --> " + Style.RESET_ALL + "{e}")
                return None, ""
        else:
            return None, ""

    # Return parameters used by our Model_Handler class
    def grab_useful_parameters(self, stock_list, market_data):
        return stock_list, market_data, self.risk_free_rate, self.time_delta

    # Apply Cuts method called in conduct_report input is a MyStock object
    def apply_cuts(self, myStock):
        # filter out any penny stock tickers
        # Additionally if a stock does not have a price check if its from one
        # of the research files and filter it out for future reference
        if myStock.price is None:
            self.total_cuts += 1
            logger.warning(f"{myStock.name} does not have a price, cutting.")
            return True
        if myStock.price < float(self.args.min_price) or myStock.price > float(self.args.max_price):
            self.total_cuts += 1
            logger.warning(f"{myStock.name} is out of the price range, cutting.")
            return True
        # Filter out any ETFs
        if myStock.is_etf:
            self.total_cuts += 1
            logger.warning(f"{myStock.name} is an etf, cutting.")
            return True
        # Ensure fifty percent is not none
        if myStock.fifty_percent is None:
            self.total_cuts += 1
            logger.warning(f"{myStock.name} does not have a 50 day, cutting.")
            return True
        # Ensure two hundred percent is not none
        if myStock.twohundred_percent is None:
            self.total_cuts += 1
            logger.warning(f"{myStock.name} does not have a 200 day, cutting")
            return True

        # make sure stocks have history we need
        # Ensure history is not none
        if self.args.model_time_delta == "1y":
            if myStock.the_year_history is None:
                self.total_cuts += 1
                logger.warning(f"{myStock.name} does not have a year history, cutting.")
                return True
        elif self.args.model_time_delta == "ytd":
            if myStock.the_ytd_history is None:
                self.total_cuts +=1
                logger.warning(f"{myStock.name} does not have a ytd history, cutting.")
                return True
        elif self.args.model_time_delta == "6mo":
            if myStock.the_6mo_history is None:
                self.total_cuts +=1
                logger.warning(f"{myStock.name} does not have a 6mo history, cutting.")
                return True
        elif self.args.model_time_delta == "3mo":
            if myStock.the_3mo_history is None:
                self.total_cuts +=1
                logger.warning(f"{myStock.name} does not have a 3mo history, cutting.")
                return True
        elif self.args.model_time_delta == "1mo":
            if myStock.the_month_history is None:
                self.total_cuts += 1
                logger.warning(f"{myStock.name} does not have a month history, cutting.")
                return True
        elif self.args.model_time_delta == "5d":
            if myStock.the_5d_history is None:
                self.total_cuts +=1
                logger.warning(f"{myStock.name} does not have a 5d history, cutting.")
                return True
        elif self.args.model_time_delta == "1d":
            if myStock.the_day_history is None:
                self.total_cuts +=1
                logger.warning(f"{myStock.name} does not have a 1d history, cutting.")
                return True


## -----------------------------------------------------------------------------------------##
## ----------------------------- CompareStocks CLASS    ----------- ------------------------##
## -----------------------------------------------------------------------------------------##

class CompareStocks:
    def __init__(self, stock1=None, stock2=None, output=None):
        # Constructor with 4 arguments
        if stock1 is not None and stock2 is not None and output is not None:
            self.stock1 = stock1
            self.stock2 = stock2
            self.output = output
        # Constructor with 3 arguments
        elif stock1 is not None and stock2 is not None:
            self.stock1 = stock1
            self.stock2 = stock2
        # Constructor with 2 arguments defaults debug to false (minimum)
        else:
            self.stock1 = stock1
            self.stock2 = stock2

        #Initialize variables
        self.difference = 0


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
