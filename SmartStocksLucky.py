import logging 
from colorama import Fore, Style 
from tqdm import tqdm

#MY Modules 
from SmartStocksStock import Stock, IndexStock 

logger = logging.getLogger(__name__)

class FeelingLucky:
    def __init__(self, args=None):
        self.args = args 

    def __del__(self):
        pass 

    def chase_greatness(self, stock_list, analysis):
        # get WAM 
        logger.info("Grabbing Market Data...")
        market_index = IndexStock(period=self.args.model_period, interval=self.args.model_interval)
        market_index.index = self.args.index 
        market_data = market_index.index.history
        analysis.determine_risk_free_rate() 
        logger.info("Market Data Acquired")

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

            result = analysis.determine_top_performers(filtered_stocks, market_data, self.args.models)
            performers_df, mse, r_squared = result 
            # Figure out top performances
            top_performers, _ = analysis.pull_top_performers(df=performers_df, tickers=filtered_tickers, _filter=int(self.args.number_to_highlight))

            return top_performers, mse, r_squared