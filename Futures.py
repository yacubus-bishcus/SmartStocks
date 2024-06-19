import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import logging

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
        ax1.plot(self.stock_futures.index, self.stock_futures.values, label=self.stock_futures.columns)
        xlabel_string = "Date"
        ax1.set_xlabel(xlabel_string)
        ax1.set_ylabel("Predicted Price")
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        ax2.plot(self.market_futures.index, self.market_futures.values, label='Market Predicted Price', color='black', linestyle='--')
        ax2.set_ylabel("Market Predicted Price")
        ax2.legend(loc='upper right')
        plt.title(string_title)
        fig.autofmt_xdate()
        return fig
