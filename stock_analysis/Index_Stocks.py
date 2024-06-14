#from MyStock import Stock
import yfinance as yf
from colorama import Fore, Style

class Index_Stocks:
    def __init__(self, debug=None):
        self.sap_ticker = '^GSPC'
        self.dow_ticker = '^DJI'
        self.nas_ticker = '^IXIC'
        self.tickers = ['^GSPC', '^DJI', '^IXIC']
        self.index_stocks = None
        self.sap_stock = None
        self.dow_stock = None
        self.nas_stock = None
        self.info_set = False
        if debug is not None:
            self.debug = debug
        else:
            self.debug = False

    def set_index_info(self):
        if not self.info_set:
            self.index_stocks = yf.Tickers(self.tickers)
            self.sap_stock = self.index_stocks.tickers[self.sap_ticker]
            self.dow_stock = self.index_stocks.tickers[self.dow_ticker]
            self.nas_stock = self.index_stocks.tickers[self.nas_ticker]

            if self.debug:
                print("Index_Stocks::set_index_info --> Stocks Set.")
                print("Index_stocks::set_index_info --> SAP STOCK: ", self.sap_stock)

            self.info_set = True
        else:
            if self.debug:
                print("Index_Stocks::set_index_info --> Info already fetched.")

    def get_history(self, index, period='1mo'):
        if index.lower() == "s&p":
            return self.sap_stock.history(period=period)
        elif index.lower() == "dow":
            return self.dow_stock.history(period=time_delta)
        elif index.lower() == "nas":
            return self.nas_stock.history(period=time_delta)
        else:
            print(Fore.YELLOW + "USER ERROR: Index_Stocks::get_history --> Index Name Not Found" + Style.RESET_ALL)
            return None
