import matplotlib.pyplot as plt
import logging
import pandas as pd 

logger = logging.getLogger(__name__)

class Futures:
    def __init__(self, stock_futures=None, market_futures=None, args=None):
        self.stock_futures = stock_futures
        self.market_futures = market_futures
        self.args = args
        self.caption = """
        Future prices here are calculated from a monte carlo calculation incorporating
        drift, volatility and jumps of a stock over the desired time horizon.
        The jump threshold standard deviation used was two standard deviations.
        """

    def __del__(self):
        pass

    def get_name(self, name):
        return "Futures"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        pass


    def plot(self, stock_name=None, ax=None):
        plt.ioff()
        string_title = stock_name + " Future Prices"
        fig, ax1 = plt.subplots(figsize=(10,6))
        self.stock_futures = self.check_index_type(self.stock_futures)
        ax1.plot(self.stock_futures.index, self.stock_futures.values, label=self.stock_futures.columns)
        xlabel_string = "Date"
        ax1.set_xlabel(xlabel_string)
        ax1.set_ylabel("Predicted Price")
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        self.market_futures = self.check_index_type(self.market_futures)
        ax2.plot(self.market_futures.index, self.market_futures.values, label='Market Predicted Price', color='black', linestyle='--')
        ax2.set_ylabel("Market Predicted Price")
        ax2.legend(loc='upper right')
        plt.title(string_title)
        fig.autofmt_xdate()
        return fig
    
    def check_index_type(self, df):
        if pd.api.types.is_datetime64_any_dtype(df.index):
            logger.info("Index is of datetime type.")
        elif pd.api.types.is_string_dtype(df.index):
            logger.warning("Index is of string type.")
            df.index = pd.to_datetime(df.index)
            logger.info("Index Converted to datetime objects.")
        else:
            logger.error("Index is of another type.")

        return df 
        
