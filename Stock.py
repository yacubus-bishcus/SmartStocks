import yfinance as yf
import sys
import logging
from colorama import Fore, Style

logger = logging.getLogger(__name__)

## -----------------------------------------------------------------------------------------##
## ----------------------------- INDEX_STOCKS CLASS    ----------- -------------------------##
## -----------------------------------------------------------------------------------------##
class Index_Stocks:
    def __init__(self):
        self.sap_ticker = '^GSPC'
        self.dow_ticker = '^DJI'
        self.nas_ticker = '^IXIC'
        self.tickers = ['^GSPC', '^DJI', '^IXIC']
        self.index_stocks = None
        self.sap_stock = None
        self.dow_stock = None
        self.nas_stock = None
        self.info_set = False
        self.myIndexStock = None

    def create_my_index_stock(self, index, args):
        if not self.info_set:
            if index.lower() == "s&p500":
                self.myIndexStock = MyStock(yf.Ticker(self.sap_ticker), args)
                self.info_set = True
                logger.info("S&P500 stock created.")
            elif index.lower() == "dow jones":
                self.myIndexStock = MyStock(yf.Ticker(self.dow_ticker), args)
                self.info_set = True
            elif index.lower() == "nasdaq":
                self.myIndexStock = MyStock(yf.Ticker(self.nas_ticker), args)
                self.info_set = True
            else:
                logger.info("create_my_index_stock --> Index Not Found. Exiting.")
                sys.exit(1)

        return self.myIndexStock

    def set_index_info(self):
        if not self.info_set:
            self.index_stocks = yf.Tickers(self.tickers)
            self.sap_stock = self.index_stocks.tickers[self.sap_ticker]
            self.dow_stock = self.index_stocks.tickers[self.dow_ticker]
            self.nas_stock = self.index_stocks.tickers[self.nas_ticker]
            logger.debug("--> Index Stocks Set.")
            self.info_set = True
        else:
            logger.debug("--> Info already fetched.")

    def get_history(self, index, period='max'):
        if index.lower() == "s&p":
            try:
                logger.info(f"Grabbing S&P500 for {period}...")
                history = self.sap_stock.history(period=period)
                logger.info("S&P500 DATA ACQUIRED.")
            except Exception as e:
                logger.info("Market Data Collection Fail...Check Internet. Exiting...")
                logger.exception(f"Index_Stocks::get_history {e}")
                sys.exit(1)
            return history
        elif index.lower() == "dow":
            try:
                logger.info(f"Grabbing DOW JONES for {period}...")
                history = self.dow_stock.history(period=time_delta)
                logger.info("DOW JONES DATA ACQUIRED.")
            except Exception as e:
                logger.info("Market Data Collection Fail...Check Internet. Exiting...")
                logger.exception(f"Index_Stocks::get_history {e}")
                sys.exit(1)
            return history
        elif index.lower() == "nas":
            try:
                logger.info(f"Grabbing NASDAQ for {period}...")
                history = self.nas_stock.history(period=time_delta)
                logger.info("NASDAQ DATA ACQUIRED.")
            except Exception as e:
                logger.info("Market Data Collection Fail...Check Internet. Exiting...")
                logger.exception(f"Index_Stocks::get_history {e}")
                sys.exit(1)
            return history
        else:
            logger.error(Fore.YELLOW + "USER ERROR --> Index Name Not Found" + Style.RESET_ALL)
            return None


## -----------------------------------------------------------------------------------------##
## ----------------------------- MyStock CLASS    ----------- ------------------------------##
## -----------------------------------------------------------------------------------------##

class MyStock:
    # python only reads one __init__
    def __init__(self, stock, time_period=None, args=None):
        # initialize attributes
        self.args = args
        self.model_time_delta = '1mo'
        if self.args is not None:
            self.model_time_delta = self.args.model_time_delta
        elif time_period is not None:
            self.model_time_delta = time_period
        else:
            logger.info("Default model_time_delta used 1mo")

        self.symbol = None
        self.name = None
        self.the_recommendations = None
        self.the_summary = None
        self.price = 0.
        self.daily_percent = 0.
        self.twohundred_percent = 0.
        self.fifty_percent = 0.
        self.is_etf = False
        self.the_5y_history = None
        self.the_year_history = None
        self.the_ytd_history = None
        self.the_6mo_history = None
        self.the_3mo_history = None
        self.the_month_history = None
        self.the_5d_history = None
        self.the_day_history = None

        if isinstance(stock, list):
            self.stock = stock[0]
        else:
            self.stock = stock

        if self.stock is None:
            logger.error("--> Some Stocks such as ETFs are not compatible with this program. Exiting Program.")
            sys.exit(1)

        self.symbol = self.stock.info['symbol']
        self.is_index = False
        index_funds = ['^IXIC','^DJI','^GSPC']
        if self.symbol in index_funds:
            self.is_index = True

        # Fetch stock info from Yahoo Finance
        # handle error cases
        self._fetch_stock_info()
        self.fifty_percent = self.get_fifty_percent()
        self.twohundred_percent = self.get_twohundred_percent()

    def _fetch_stock_info(self):
        self.info = self.stock.info

        if self.info:
            self.name = self.info.get('longName')
            if self.name:
                pass
            else:
                logger.error(Fore.YELLOW + "ERROR: Stock name not available." + Style.RESET_ALL)
                return
        else:
            logger.error(Fore.YELLOW + "ERROR: Unable to fetch information for the stock. Please check the symbol." + Style.RESET_ALL)
            return

        self.price = self.info.get('currentPrice')
        if self.price:
            pass
        else:
            if self.is_index:
                self.price = self.info.get('ask')
            else:
                logger.warning(f"{self.name} current Price not available.")

        self.fiftyavg = self.info.get('fiftyDayAverage')
        if self.fiftyavg:
            logger.debug(f"Fifty Day Average: {self.fiftyavg}")
        else:
            logger.warning(f"{self.name} Fifty Day Average Not Available.")

        self.twohundredavg = self.info.get('twoHundredDayAverage')
        if self.twohundredavg:
            logger.debug(f"Two Hundred Day Average: {self.twohundredavg}")
        else:
            logger.warning(f"{self.name} Two Hundred Day Average Not Available.")

        self.open_price = self.info.get('open')
        if self.open_price:
            logger.debug(f"Open Price: {self.open_price}")
        else:
            logger.warning(Fore.YELLOW + "ERROR: Open Price not available." + Style.RESET_ALL)

        if self.price and self.open_price:
            self.daily_percent = (self.price - self.open_price)/self.price*100
            if self.fiftyavg:
                self.fifty_percent = (self.price - self.fiftyavg)/self.price*100
            if self.twohundredavg:
                self.twohundred_percent = (self.price - self.twohundredavg)/self.price*100

        elif self.open_price:
            if self.fiftyavg:
                self.fifty_percent = (self.open_price - self.fiftyavg)/self.open_price*100
            if self.twohundredavg:
                self.twohundred_percent = (self.open_price - self.twohundredavg)/self.open_price*100
        else:
            logger.error(Fore.YELLOW + "ERROR: Open Price and Current Price Not Available." + Style.RESET_ALL)
            return

        if self.info.get('quoteType') == "ETF":
            self.is_etf = True

        if not self.is_index:
            self.the_summary = self.info.get('longBusinessSummary')
            if not self.is_etf:
                self.the_recommendations = self.stock.recommendations
        self.history = self.stock.history

        # Set histories
        # I try several times to get info for 1y and 1mo because these are the
        # most popular. I only work down in looking for history, I never look
        # for a longer history. Warnings are tossed if histories can't be found
        # this may cause crashes but will test during debugging
        # Always Set 1y since thats what WAM is based off
        try:
            self.the_5y_history = self.history(period='5y')
            logger.info(f"Five Year History found for {self.name}")
        except:
            logger.warning(f"fetch_stock_info --> 5y history not found, trying 1y for {self.name}")
            try:
                self.the_5d_history = self.history(period='1y')
            except:
                logger.warning(f"fetch_stock_info --> 1y history not found for {self.name}")
        try:
            self.the_year_history = self.history(period="1y")
        except:
            logger.warning("fetch_stock_info --> 1y History not found, trying ytd.")
            try:
                self.the_year_history = self.stock.history(period="ytd")
            except:
                logger.warning("fetch_stock_info --> ytd History not found, trying 1mo.")
                try:
                    self.the_year_history = self.stock.history(period="1mo")
                except:
                    logger.warning(f"fetch_stock_info --> history cannot be found for {self.name}")

        if self.model_time_delta == "ytd":
            try:
                self.the_ytd_history = self.history(period="ytd")
            except:
                logger.warning(f"fetch_stock_info --> ytd History not found for {self.name}.")


        try:
            self.the_6mo_history = self.history(period="6mo")
        except:
            logger.warning(f"fetch_stock_info --> 6mo History not found for {self.name}")


        try:
            self.the_3mo_history = self.history(period="3mo")
            logger.info(f"fetch_stock_info --> 3mo history found for {self.name}")
        except:
            logger.warning(f"fetch_stock_info --> 3mo History not found for {self.name}")
        # set 1mo
        if self.model_time_delta == "1mo":
            try:
                self.the_month_history = self.history(period='1mo')
                logger.info(f"fetch_stock_info --> 1mo History is set for {self.name}.")
            except:
                logger.warning("fetch_stock_info --> 1mo not found trying 5d...")
                try:
                    self.the_month_history = self.history(period='5d')
                except:
                    logger.warning("fetch_stock_info --> 5d not found trying 1d...")
                    try:
                        self.the_month_history = self.stock.history(period="1d", interval='5m')
                    except:
                        logger.warning(f"fetch_stock_info --> history cannot be found for {self.name}")

        if self.model_time_delta == "5d":
            try:
                self.the_5d_history = self.history(period='5d')
            except:
                logger.warning(f"fetch_stock_info --> 5d History not found for {self.name}")


        try:
            self.the_day_history = self.history(period='1d', interval='5m')
            logger.info(f"{self.name} one day history set.")
        except:
            logger.warning(f"fetch_stock_info --> 1d History not found for {self.name}")

    def __del__(self):
        pass

    # Define setting methods
    def get_fifty_percent(self):
        return self.fifty_percent

    def get_twohundred_percent(self):
        return self.twohundred_percent

    # Define other getter methods for encapsulation

    def print_daily_change(self):
        print(self.name, " Daily Change Percent: ", self.daily_percent)

    def print_50_change(self):
        print(self.name, " 50 Day Average Change Percent: ", self.fifty_percent)

    def print_200_change(self):
        print(self.name, " 200 Day Average Change Percent: ", self.twohundred_percent)

    def print_summary(self):
        print(self.name, " Summary: ", self.the_summary)
