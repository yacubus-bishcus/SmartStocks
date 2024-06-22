import logging
from tqdm import tqdm
from colorama import Fore, Style
from datetime import datetime, timedelta
import pandas as pd
import pkg_resources

# My Modules
from Model_Handler import Model_Handler
from StockAnalysis import MyStock

logger = logging.getLogger(__name__)

class Report:
    def __init__(self, output, args):
        self.output = output
        self.args = args
    def __del__(self):
        # Save file
        self.output.create_explanation_statement()
        self.output.write(f"Ran {self.args.simulations} trials simulating {self.args.sim_time} days of future prices for each stock using seed {self.args.seed} with {self.args.processes} processors.")
        self.output.write("Weights Used for Weighted Aggregate Merit: " + str(self.args.weights))
        self.output.save()


    def write_report(self, analysis):
        total_stocks = str(self.output.grab_report_card_value('total_stocks'))
        self.output.write(f"The total number of stocks evaluated for this report was {total_stocks}")
        top_ticker_string = "The top " + str(self.args.number_to_highlight) + " stocks were " .join(self.output.grab_report_card_value('top_performers')) + "."
        self.output.write(top_ticker_string)
        self.output.write(f"The BEST stock was {self.output.grab_report_card_value('best')}.")
        self.output.write("Supervised Aggregate Merit Mean Square Error: " + str(self.output.grab_report_card_value('mse')))
        self.output.write("Supervised Aggregate Merit R-Squared: " + str(self.output.grab_report_card_value('r_squared')))
        self.output.write("See below for the WAM/SAM Table and the top performers charts.")
        # now we include the table
        table_data = analysis.read_table(self.output.grab_report_card_value('table_sheet_name'))
        self.output.write_table(table_data, "User Input Stocks Performance Metric")
        # now we include the plots
        self.output.add_plots_to_word(self.output.grab_report_card_value('best'), self.output.grab_report_card_value('figures'))
        logger.info("Report Complete.")

    def conduct_report(self, stock_list, analysis):
        #get WAM
        logger.info("Grabbing Market Data...")
        # Ensure you can grab market data and establish risk free rate or MODELS
        # Five year market data
        market_data = analysis.get_market_data(self.args.index)
        logger.info("Grabbing Simulated Market Data...")
        # user selected sim_market period time
        sim_market_data = analysis.get_market_data(self.args.index, self.args.model_time_delta)
        analysis.determine_risk_free_rate()
        logger.info("Market Data Acquired.")

        if market_data is None:
            logger.error(Fore.RED + "conduct_report --> market_data is empty. Check Internet Connection." + Style.RESET_ALL)
            return

        if sim_market_data is None:
            logger.error(Fore.RED + "conduct_report --> market_data for simulations is empty. Check Internet Connection." + Style.RESET_ALL)
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
                my_stock = MyStock(stock, self.args)
                if not analysis.apply_cuts(my_stock):
                    filtered_stocks.append(my_stock)
                    filtered_tickers.append(my_stock.symbol)

            logger.info("Data Processing Complete.")
            logger.info(f"Total Number of Stocks Cut --> {analysis.total_cuts}")
            logger.info("Determining Top Performers...")
            performers_df = analysis.determine_top_performers(filtered_stocks, market_data, self.args.models, self.output)
            # Write to excel file for historic comparison
            sheet_name =  self.args.output.split('.')[0] + datetime.today().strftime('%m_%d')
            self.output.add_to_report_card('table_sheet_name',sheet_name)
            analysis.write_to_excel(performers_df, sheet_name)
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
        if self.args.simulations > 0:
            histories = []
            model_histories = []
            for stock in filtered_stocks:
                if stock.symbol in top_tickers:
                    histories.append(stock.the_5y_history)
                    if self.args.model_time_delta == "5y":
                        model_histories.append(stock.the_5y_history)
                    elif self.args.model_time_delta == "1y":
                        model_histories.append(stock.the_year_history)
                    elif self.args.model_time_delta == "ytd":
                        model_histories.append(stock.the_ytd_history)
                    elif self.args.model_time_delta == "6mo":
                        model_histories.append(stock.the_6mo_history)
                    elif self.args.model_time_delta == "3mo":
                        model_histories.append(stock.the_3mo_history)
                    elif self.args.model_time_delta == "1mo":
                        model_histories.append(stock.the_month_history)
                    elif self.args.model_time_delta == "5d":
                        model_histories.append(stock.the_5d_history)
                    elif self.args.model_time_delta == "1d":
                        model_histories.append(stock.the_day_history)
                    else:
                        time_delta_options = ['1d','5d','1mo','3mo','6mo','ytd','1y','5y']
                        logger.error(f"Time period must be one of the following options: {time_delta_options}.")
                        sys.exit(1)

            MyStock_best = None
            for stock in filtered_stocks: # figure out the best stock to make plots with
                if stock.symbol == number_one_ticker:
                    logger.info(f"Top Ticker Found: {number_one_ticker}")
                    MyStock_best = stock

            logger.info(f"Conducting Simulations on the following tickers: {top_tickers}")
            future_prices = pd.DataFrame() # will be a dataframe of price per day per stock
            for history in tqdm(histories, desc='Stocks Simulation'):
                future_price = analysis.conduct_simulations(history) # one price per day
                stock_series = pd.Series(future_price)
                future_prices = future_prices.append(stock_series, ignore_index=True)

            future_prices.index = top_tickers
            future_prices = self.format_future_prices(future_prices, True)

            close_histories = pd.DataFrame()
            for i in range(int(self.args.number_to_highlight)):
                close_histories = close_histories.append(model_histories[i]['Close'], ignore_index=True)

            close_histories.index = top_tickers
            close_histories = close_histories.T
            close_histories.index = close_histories.index.date
            combined_df = pd.concat([close_histories, future_prices], axis=0, ignore_index=False)
            combined_df.index = combined_df.index.rename('Date')
            sheet_name = "Future_Prices" + datetime.today().strftime('%b_%d')

            analysis.write_to_excel(combined_df, sheet_name)

            df = analysis.conduct_simulations(sim_market_data)
            market_series = pd.Series(df)
            market_df = pd.DataFrame()
            market_df = market_df.append(market_series, ignore_index=True)
            market_df = self.format_future_prices(market_df, True)
            market_df.columns = ['Price']
            market_history = pd.Series(sim_market_data['Close'])
            market_history_df = pd.DataFrame()
            market_history_df = market_history_df.append(market_history, ignore_index=False)
            market_history_df = self.format_future_prices(market_history_df, False)
            market_history_df.index = market_history_df.index.date
            market_history_df.columns = ['Price']
            # combine the market history with market futures
            combined_market_df = pd.concat([market_history_df, market_df], axis=0, ignore_index=False)
            combined_market_df.index = combined_market_df.index.rename('Date')


        # Create Plots
        self.output.add_to_report_card('top_performers', top_tickers)
        self.output.add_to_report_card('best', number_one_ticker)
        figures = self.create_plots(MyStock_best, market_data, combined_df, combined_market_df, analysis)
        self.output.add_to_report_card('figures', figures)

    def create_plots(self, MyStock_best, market_data, combined_stock_df, combined_market_df, analysis):
        filename = ""
        figures = []
        if MyStock_best is None:
            logger.warning("No best stock was found. Skipping plotting.")
            return

        if self.args.output.endswith(".docx"):
            filename = self.args.output.replace(".docx", ".png")
        filepath = pkg_resources.resource_filename('StockApp.output', filename)

        # here the model handler will be based off the user's input for time_delta
        number_one_model = Model_Handler(myStock_list=MyStock_best, market_data=market_data, risk_free_rate=analysis.risk_free_rate, args=self.args)
        number_one_model.pass_futures_data(combined_stock_df)
        number_one_model.pass_futures_market_data(combined_market_df)
        number_one_model.pass_market_stock(analysis.myIndexStock)
        number_one_model.add_all_plotting_models()
        figures = number_one_model.plot_catcher(filepath)

        return figures

    def format_future_prices(self, df, md):
        df = df.T
        if md:
            dates = [(datetime.today() + timedelta(days=i)) for i in range(self.args.sim_time)]
            dates = [dt.date() for dt in dates]
            df['Date'] = dates
            df.set_index('Date', inplace=True)
        return df
