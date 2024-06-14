from MyOutput import WordPrinter
import sys
from colorama import Fore, Style


class Stock:
    # python only reads one __init__
    def __init__(self, stock, debug=None, output=None):
        # initialize attributes
        self.symbol = None
        self.name = None
        self.recommendations = None
        self.longBusinessSummary = None
        self.price = 0.
        self.daily_percent = 0.
        self.twohundred_percent = 0.
        self.fifty_percent = 0.
        # Constructor with 3 arguments
        if stock is not None and debug is not None and output is not None:
            if isinstance(stock, list):
                self.stock = stock[0]
            else:
                self.stock = stock
            self.symbol = self.stock.info['symbol']
            self.debug = debug
            self.output = output
        # Constructor with 2 Arguments
        elif stock is not None and debug is not None:
            if isinstance(stock, list):
                self.stock = stock[0]
            else:
                self.stock = stock

            self.symbol = self.stock.info['symbol']
            self.debug = debug
        # Constructor with 1 Argument (minimum)
        else:
            self.stock = stock
            self.debug = False

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
                if self.debug:
                    print(f"Stock: {self.name} ({self.symbol})")
            else:
                print(Fore.YELLOW + "ERROR: Stock name not available." + Style.RESET_ALL)
                return
        else:
            print(Fore.YELLOW + "ERROR: Unable to fetch information for the stock. Please check the symbol." + Style.RESET_ALL)
            return

        self.price = self.info.get('currentPrice')
        if self.price:
            if self.debug:
                print(f"Current Price: {self.price}")
        else:
            if self.is_index:
                self.price = self.info.get('ask')
                if self.debug:
                    print(f"Current Price: {self.price}")
            else:
                print(self.name, " current Price not available.")

        self.fiftyavg = self.info.get('fiftyDayAverage')
        if self.fiftyavg:
            if self.debug:
                print(f"Fifty Day Average: {self.fiftyavg}")
        else:
            print(self.name, " Fifty Day Average Not Available.")

        self.twohundredavg = self.info.get('twoHundredDayAverage')
        if self.twohundredavg:
            if self.debug:
                print(f"Two Hundred Day Average: {self.twohundredavg}")
        else:
            print(self.name, " Two Hundred Day Average Not Available.")

        self.open_price = self.info.get('open')
        if self.open_price:
            if self.debug:
                print(f"Open Price: {self.open_price}")
        else:
            print(Fore.Yellow + "ERROR: Open Price not available." + Style.RESET_ALL)
            if self.debug:
                print("Here is the information we have on ", self.name)
                print(self.info)

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
            print(Fore.YELLOW + "ERROR: Open Price and Current Price Not Available." + Style.RESET_ALL)
            if self.debug:
                print("Here is the information we have on ", self.name)
                print(self.info)
            return

        self.summary = self.info.get('longBusinessSummary')
        self.recommendations = self.stock.recommendations

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

    def output_daily_change(self):
        self.output.write(self.name, " Daily Change Percent: ", self.daily_percent)

    def output_50_change(self):
        self.output.write(self.name, " 50 Day Average Change Percent: ", self.fifty_percent)

    def output_200_change(self):
        self.output.write(self.name, " 200 Day Average Change Percent: ", self.twohundred_percent)

    def output_recommendations(self):
        self.output.write_table(self.recommendations, 'Recommendations')

    def print_summary(self):
        print(self.name, " Summary: ", self.summary)

    def output_summary(self):
        self.output.write(self.name, " Summary: ", self.summary)
