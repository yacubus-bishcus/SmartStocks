import yfinance as yf
import logging
from colorama import Fore, Style

logger = logging.getLogger(__name__)

# Set the logging level for yfinance to CRITICAL to suppress error messages
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

## -----------------------------------------------------------------------------------------##
## ----------------------------- Stock CLASS    ----------- ------------------------------##
## -----------------------------------------------------------------------------------------##
# warning for cyrpto stocks daily price will always = 0 since open = price  
class Stock: # takes a Ticker Object and makes it into a Stock Object
    def __init__(self, stock=None, period="1mo", interval="1d"):
        # initialize attributes
        self._period = period 
        self._interval = interval 
        self._stock = stock 
        self._fifty_percent = None 
        self._daily_percent = None 
        self._twohundred_percent = None 
        index_high = 0.
        index_low = 0.

        if stock is not None:
            if isinstance(stock, list):
                stock = stock[0]

            self._symbol = stock.info.get('symbol')
            self._name = stock.info.get('longName')

            if not self.name:
                logger.error(Fore.YELLOW + "ERROR: Stock name not available." + Style.RESET_ALL)

            is_index = False
            index_funds = ['^IXIC','^DJI','^GSPC']

            if self.symbol in index_funds:
                is_index = True
                try:
                    index_high = stock.info.get('dayHigh') 
                    index_low = stock.info.get('dayLow')
                except Exception as e:
                    logger.exception(f"Index {self.symbol} Day High and Low not found. {e}")
                    logger.warning(f"Daily Percent will be returned as ZERO for Index {self.symbol}")


            self._is_crypto = False 
            if stock.info.get('quoteType') == "CRYPTOCURRENCY":
                self._is_crypto = True 
                
            self._is_etf = False
            if stock.info.get('quoteType') == "ETF":
                self._is_etf = True 

            try:
                self._recommendations = stock.recommendations 
            except Exception as e:
                logger.exception(f"Recommendations for {self.name} not found. {e}")
                self._recommendations = None 

            try:
                self._summary = stock.info.get('longBusinessSummary')
            except Exception as e:
                logger.exception(f"Summary for {self.name} not found. {e}")
                self._summary = None 

            self._price = stock.info.get('currentPrice')
            if self._price is None:
                if is_index:
                    self._price = stock.info.get('open')
                elif self.is_crypto:
                    self._price = stock.info.get('open')
                else:
                    logger.warning(f"{self.name} current Price not available.")

            self._open = stock.info.get('open')
            if self._open is None:
                logger.warning(Fore.YELLOW + "ERROR: Open Price not available." + Style.RESET_ALL)
            self._fiftyavg = stock.info.get('fiftyDayAverage')
            if self._fiftyavg is None:
                logger.warning(f"{self.name} Fifty Day Average Not Available.")

            self._twohundredavg = stock.info.get('twoHundredDayAverage')
            if self._twohundredavg is None:
                logger.warning(f"{self.name} Two Hundred Day Average Not Available.")
                            
            if not is_index:
                if self.price is not None and self.open is not None:
                    if self.price > 0 and self.open > 0:
                        self._daily_percent = (self.price - self.open)/self.price*100
                    else:
                        logger.warning(f"{self.name} Price is {self.price} and Open is {self.open}.")
            else:
                if index_high != 0 and index_low != 0:
                    self._daily_percent = (index_high - index_low)/index_high*100.
                else:
                    self._daily_percent = 0.

            if self.price is not None and self.fiftyavg is not None:
                if self.fiftyavg > 0:
                    self._fifty_percent = (self.price - self.fiftyavg)/self.price*100
                else:
                    logger.warning(f"FiftyDayAverage {self.fiftyavg}. Cannot determine FiftyDayAverage Difference")
            
            if self.price is not None and self.twohundredavg is not None:
                if self.twohundredavg > 0:
                    self._twohundred_percent = (self.price - self.twohundredavg)/self.price*100
                else:
                    logger.warning(f"Two Hundred Day Average {self.twohundredavg}. Cannot determine TwoHundred Day Average Difference.")


            df = stock.history(period=self._period, interval=self._interval)[['Open','High','Low','Close']]
            try:
                df.index = df.index.tz_localize(None)
            except Exception as e:
                logger.exception(Fore.RED + f"Error Setting Stock Index {e}" + Style.RESET_ALL)
                logger.info("Printing History: ")
                logger.info(df)
            self._history = df 
        

    @property
    def period(self):
        return self._period 
    
    @property 
    def interval(self):
        return self._interval 
    
    @property
    def symbol(self):
        return self._symbol

    @property 
    def name(self):
        return self._name 
            
    @property 
    def recommendations(self):
        return self._recommendations
    
    @property 
    def summary(self):
        return self._summary 
    
    @property 
    def price(self):
        return self._price 
    
    @property 
    def open(self):
        return self._open 
    
    @property
    def is_etf(self):
        return self._is_etf 
    
    @property 
    def is_crypto(self):
        return self._is_crypto
    
    @property 
    def daily_percent(self):
        return self._daily_percent
    
    @property 
    def fiftyavg(self):
        return self._fiftyavg
    
    @property 
    def twohundredavg(self):
        return self._twohundredavg

    @property 
    def fifty_percent(self):
        return self._fifty_percent 

    @property 
    def twohundred_percent(self):
        return self._twohundred_percent
    
    @property 
    def history(self):
        return self._history

    @history.setter
    def history(self, period, interval):
        self._history = self._stock.history(period=period, interval=interval)
        
    def __del__(self):
        pass

    # Define other getter methods for encapsulation

    def print_daily_change(self):
        print(self.name, " Daily Change Percent: ", self.daily_percent)

    def print_50_change(self):
        print(self.name, " 50 Day Average Change Percent: ", self.fifty_percent)

    def print_200_change(self):
        print(self.name, " 200 Day Average Change Percent: ", self.twohundred_percent)

    def print_summary(self):
        print(self.name, " Summary: ", self.summary)


## -----------------------------------------------------------------------------------------##
## ----------------------------- INDEX_STOCKS CLASS    ----------- -------------------------##
## -----------------------------------------------------------------------------------------##

class IndexStock(Stock): #inherits from Stock parent but is special case for 
    def __init__(self, period="1mo", interval="1d"):
        super().__init__(None, period=period, interval=interval)
        # self.sap_ticker = '^GSPC'
        # self.dow_ticker = '^DJI'
        # self.nas_ticker = '^IXIC' 
        self._info_set = False
        self._index = None 
        self._period = period 
        self._interval = interval 

    @property
    def info_set(self):
        return self._info_set
    
    @property 
    def index(self):
        return self._index
    
    @property
    def period(self):
        return self._period 
    
    @property
    def interval(self):
        return self._interval 
    
    @index.setter
    def index(self, ticker):
        if not self.info_set:
            logger.info(f"Setting Index: {ticker}")
            self._index = Stock(yf.Ticker(ticker), self.period, self.interval)
            logger.info(f"Index {self._index.name} set.")
            self._info_set = True 
        else:
            logger.info(f"Index {self._index.name} already set.")

