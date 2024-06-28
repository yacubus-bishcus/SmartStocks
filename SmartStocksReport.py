import logging
from tqdm import tqdm
from colorama import Fore, Style
from datetime import datetime
import pandas as pd

# My Modules
from SmartStocksStock import Stock, IndexStock
from DateGenerator import DateGenerator

logger = logging.getLogger(__name__)

class Report:
    def __init__(self, output=None, args=None):
        self.output = output
        self.args = args

    def __del__(self):
        # Save file
        if self.output is not None:
            self.output.smartstock_explanation_statement()
            self.output.write(f"Ran {self.args.simulations} trials simulating {self.args.sim_time} days of future prices for each stock using seed {self.args.seed} with {self.args.processes} processors.")
            self.output.write("Weights Used for Weighted Aggregate Merit: " + str(self.args.weights))
            self.output.save()


    def write_report(self, analysis):
        self.output.write(f"The total number of stocks evaluated for this report was {self.output.total_stocks}")
        top_ticker_string = "The top " + str(self.args.number_to_highlight) + " stocks were " .join(self.output.top_performers) + "."
        self.output.write(top_ticker_string)
        self.output.write(f"The BEST stock was {self.output.best}.")
        self.output.write("Supervised Aggregate Merit Mean Square Error: " + str(self.output.mse))
        self.output.write("Supervised Aggregate Merit R-Squared: " + str(self.output.r_squared))
        self.output.write("See below for the WAM/SAM Table and the top performers charts.")
        # now we include the table
        table_data = analysis.read_table(self.output.table_sheet_name)
        self.output.write_table(table_data, "User Input Stocks Performance Metric")
        # now we include the plots
        self.output.create_plots(self.output.best, self.output.figures)
        logger.info("Report Complete.")

    def conduct_report(self, stock_list, analysis):
        #get WAM
        logger.info("Grabbing Market Data...")
        market_index = IndexStock(period=self.args.model_period, interval=self.args.model_interval)
        market_index.index = self.args.index # for history its just market_index.index.history 
        market_data = market_index.index.history 
        analysis.determine_risk_free_rate()
        logger.info("Market Data Acquired.")

        if market_data is None:
            logger.error(Fore.RED + "conduct_report --> market_data is empty. Check Internet Connection." + Style.RESET_ALL)
            return

        if analysis.risk_free_rate is None:
            logger.error(Fore.RED + "conduct_monthly report::determine_risk_free_rate no return. Check Internet Connection." + Style.RESET_ALL)
            return

        # Get WAM
        # apply cuts as necessary prior to determine_top_performers
        if len(stock_list) > 0:
            filtered_stocks = []
            filtered_tickers = []
            logger.info("Processing Stocks...")
            for stock in tqdm(stock_list, desc="Stocks"):
                my_stock = Stock(stock, self.args.model_period, self.args.model_interval)
                if not analysis.apply_cuts(my_stock):
                    filtered_stocks.append(my_stock)
                    filtered_tickers.append(my_stock.symbol)

            logger.info("Data Processing Complete.")
            logger.info(f"Total Number of Stocks Cut --> {analysis.total_cuts}")
            logger.info("Determining Top Performers...")

            performers_df = analysis.determine_top_performers(filtered_stocks, market_data, self.args.models, self.output)
            # Write to excel file for historic comparison
            sheet_name =  self.args.output.split('.')[0] + datetime.today().strftime('%m_%d')
            self.output.table_sheet_name = sheet_name
            logger.info(f"--> Writing Performance Data to {sheet_name}")
            self.output.write_to_excel(df=performers_df, sheet_name=sheet_name)
            logger.info(f"--> Performance Data written to {sheet_name}")

        # Figure out top performances
            top_performers, top_tickers = analysis.pull_top_performers(df=performers_df, tickers=filtered_tickers, filter=int(self.args.number_to_highlight))
            if top_performers.empty or len(top_tickers) == 0:
                return

        # Figure out the number one
            number_one_df, number_one_ticker = analysis.pull_top_performers(df=performers_df, tickers=filtered_tickers, filter=1)
            number_one_ticker = number_one_ticker[0]
        else:
            logger.warning("Stock List less than zero!")
            return

        # Conduct Simulations on the number to highlight top performers
        Stock_best = None
        combined_df = None 
        combined_market_df = None 
        for stock in filtered_stocks: # figure out the best stock to make plots with
            if stock.symbol == number_one_ticker:
                logger.info(f"Top Ticker Found: {number_one_ticker}")
                Stock_best = stock
                
        if self.args.simulations > 0:
            model_histories = []
            for stock in filtered_stocks:
                if stock.symbol in top_tickers:
                    model_histories.append(stock.history)

            logger.info(f"Conducting Simulations on the following tickers: {top_tickers}")
            future_prices_list = []
            future_stds_list = []
            for history in tqdm(model_histories, desc='Stocks Simulation'):
                future_price, stock_stds = analysis.conduct_simulations(history) # one price per day
                future_prices_list.append(future_price)
                future_stds_list.append(stock_stds)

            # concatenate all series objects in the list into a dataframe 
            future_prices = pd.DataFrame(future_prices_list)
            future_prices.index = top_tickers
            future_stds= pd.DataFrame(future_stds_list)
            future_stds.index = top_tickers 
            future_stds = future_stds.T
            future_prices = self.format_future_prices(future_prices)

            if self.args.include_history:
                close_histories_list = []
                for i in range(int(self.args.number_to_highlight)):
                    close_histories_list.append(model_histories[i]['Close'])

                close_histories = pd.DataFrame(close_histories_list)
                close_histories.index = top_tickers
                close_histories = close_histories.T

                combined_df = pd.concat([close_histories, future_prices], axis=0, ignore_index=False)
                combined_df.index = combined_df.index.rename('Date')

            sheet_name = "Future_Prices" + datetime.today().strftime('%b_%d')
            self.output.write_to_excel(df=future_prices, sheet_name=sheet_name, data_w_dates=True)
            if self.args.sim_market:
                df, stds = analysis.conduct_simulations(market_data)
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

        # Create Plots
        self.output.top_performers = top_tickers
        self.output.best = number_one_ticker
        
        if self.args.include_history:
            if self.args.sim_market:
                figures = self.output.smartstock_plots(Stock_best, 
                                                       stock_df=combined_df, 
                                                       stds_df=future_stds, 
                                                       market_df=combined_market_df,
                                                       market_stds=market_stds_df, 
                                                       analysis=analysis
                                                       )
            else:
                figures = self.output.smartstock_plots(Stock_best, 
                                                       stock_df=combined_df,
                                                       stds_df=future_stds, 
                                                       analysis=analysis)
        else:
            if self.args.sim_market:
                figures = self.output.smartstock_plots(Stock_best, 
                                                       stock_df=future_prices,
                                                       stds_df=future_stds, 
                                                       market_df=market_df, 
                                                       market_stds=market_stds_df,
                                                       analysis=analysis)
            else:
                figures = self.output.smartstock_plots(Stock_best, 
                                                       stock_df=future_prices, 
                                                       stds_df=future_stds,
                                                       analysis=analysis)

        self.output.figures = figures


    def format_future_prices(self, df):
        df = df.T
        date_gen = DateGenerator(self.args)
        dates = date_gen.generate_dates_with_intervals()
        df['Date'] = dates
        df.set_index('Date', inplace=True)
        return df