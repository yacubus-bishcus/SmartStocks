import matplotlib.pyplot as plt
import logging
import pandas as pd 
from colorama import Fore, Style 

# My Modules 
from Models import BaseModel

logger = logging.getLogger(__name__)

class Futures(BaseModel):
    def __init__(self, stock_futures=None, futures_stds=None, market_futures=None, market_stds=None, args=None):
        self.stock_futures = stock_futures
        self.futures_stds = futures_stds
        self.market_futures = market_futures
        self.market_stds = market_stds
        self.args = args
        self._caption = """
        Future prices here are calculated from a monte carlo calculation incorporating
        drift, volatility and jumps of a stock over the desired time horizon.
        The jump threshold standard deviation used was two standard deviations.
        """
        self._name = "Futures"

    def __del__(self):
        pass
    
    @property
    def name(self):
        return self._name 

    @property
    def caption(self):
        return self._caption

    def execute_model(self):
        pass

    def plot(self, stock_name=None, ax=None):
        plt.ioff()
        string_title = stock_name + " Future Prices"
        fig, ax1 = plt.subplots(figsize=(10,6))
        self.stock_futures = self.check_index_type(self.stock_futures)
        if self.stock_futures is not None:
            if self.futures_stds is not None:
                for column in self.stock_futures.columns:
                    ax1.errorbar(self.stock_futures.index, 
                                 self.stock_futures[column].values, 
                                 yerr=self.futures_stds[column].values, 
                                 label=column, 
                                 ecolor='red', 
                                 capsize=5, 
                                 capthick=2)
            else:
                for column in self.stock_futures.columns:
                    ax1.plot(self.stock_futures.index, 
                             self.stock_futures[column].values, 
                             label=column)

            xlabel_string = "Date"
            ax1.set_xlabel(xlabel_string)
            ax1.set_ylabel("Predicted Price")
            ax1.legend(loc='upper left')
            if self.market_futures is not None and self.market_futures != []:
                ax2 = ax1.twinx()
                self.market_futures = self.check_index_type(self.market_futures)
                if self.market_futures is not None:
                    if self.market_stds is not None:
                        for column in self.market_futures.columns:
                            ax1.errorbar(self.market_futures.index, 
                                        self.market_futures[column].values, 
                                        yerr=self.market_stds[column].values, 
                                        label=column, 
                                        ecolor='red', 
                                        capsize=5, 
                                        capthick=2, color='black', linestyle='--')
                    else:
                        for column in self.market_futures.columns:
                            ax1.plot(self.market_futures.index, 
                                    self.market_futures[column].values, 
                                    label=column, linestyle='--', color='black')


                ax2.set_ylabel("Market Predicted Price")
                ax2.legend(loc='upper right')
            plt.title(string_title)
            fig.autofmt_xdate()
            return fig
        else:
            logger.error(Fore.YELLOW + f"Futures Data attempted to plot NoneType object. Returning None." + Style.RESET_ALL)
            logger.warning(self.stock_futures)
            return None 
    