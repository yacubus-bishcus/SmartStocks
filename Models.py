import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import logging
import sys
from colorama import Fore, Style 
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


"""
ALL Models must have the following methods at minimum
get_name(name), get_caption(), execute_model(), plot(ax)
"""
class Models:
    def __init__(self, myStockList=None):
        self.stock_list = myStockList
        #self.caption =  Enter Caption here

    def __del__(self):
        pass

    def get_name(self, name):
        return name

    def get_caption(self):
        return #self.caption

    def execute_model(self):
        pass

    def plot(self, ax):
        return

## ---------------------------------------------------------------------------##
## ------------------------ Fifty_Day_Model CLASS ----------- ----------------##
## ---------------------------------------------------------------------------##

class Fifty_Day_Model:
    def __init__(self, stock_list=None):
        self.stock_list = stock_list
        self.caption = """
        Fifty Day Model Calculation (simple) calculates how the current price
        compares to the average 50 day price. Measures how the stock is doing today.
        Measure performance based on how its doing the last 50 days.
        ETFs don't always have a current price if current price not available.
        Uses the open price if current price not available.
        Outputs an array of performances for each stock in stock_list.
        """
        #logger.debug("Fifty_Day_Model --> 50 Day Model Imported.")

    def get_name(self):
        return "50 Day"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        performance = []
        for stock in self.stock_list:
            current_price = stock.price
            fifty_day_average = stock.fifty_percent
            if fifty_day_average is None:
                logger.error(Fore.YELLOW + f"Fifty_Day_Model::execute_model DATA ERROR: Fifty Day Average for {stock.info.get('name')} not available." + Style.RESET_ALL)
                return None
            if current_price is not None:
                performance_measure = current_price - fifty_day_average
            else:
                open_price = stock.info.get('open')
                if open_price is not None:
                    performance_measure = open_price - fifty_day_average
                else:
                    logger.error(Fore.YELLOW + f"Fifty_Day_Model::execute_model DATA ERROR: Current and Open Prices for {stock.info.get('name')} not available." + Style.RESET_ALL)
                    return None
            performance.append(performance_measure)

        return performance

    def plot(self, ax):
        return

## ---------------------------------------------------------------------------##
## ----------------- TwoHundred_Day_Model CLASS ----------- ------------------##
## ---------------------------------------------------------------------------##

class TwoHundred_Day_Model:
    def __init__(self, stock_list=None):
        self.stock_list = stock_list
        self.caption = """
        Two Hundred Day Model Calculation (simple) calculates how the current price
        compares to the average 200 day price. Measures how the stock is doing today.
        Measure performance based on how its doing the last 200 days.
        ETFs don't always have a current price if current price not available.
        Uses the open price if current price not available.
        Outputs an array of performances for each stock in stock_list.
        """
        #logger.debug("TwoHundred_Day_Model --> 200 Day Average Model Imported.")

    def get_name(self):
        return "200 Day"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        performance = []
        for stock in self.stock_list:
            current_price = stock.price
            average = stock.twohundred_percent

            if average is None:
                logger.error(Fore.YELLOW + "TwoHundred_Day_Model::execute_model DATA ERROR: 200 Day Average for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                return None
            if current_price is not None:
                performance_measure = current_price - average
            else:
                open_price = stock.info.get('open')
                if open_price is not None:
                    performance_measure = open_price - average
                else:
                    logger.error(Fore.YELLOW + "TwoHundred_Day_Model::execute_model DATA ERROR: Current and Open Prices for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                    return None
            performance.append(performance_measure)

        return performance

    def plot(self, ax):
        return

## ---------------------------------------------------------------------------##
## ----------------------------- RSI CLASS ----------- ----------------------##
## ---------------------------------------------------------------------------##

class RSI:
    def __init__(self, Stock_list=None, futures_data=None):
        self.stock_list = Stock_list
        self.futures_data = futures_data
        # Initalize variables for plotting
        self.rsi = None
        self.smoothed_rsi = None
        self.history = None
        self.caption = """As a momentum indicator, the relative strength index
        compares a security's strength on days when prices go up to its strength
        on days when prices go down. Relating the result of this comparison to
        price action can give traders an idea of how a security may perform.
        Traditionally the RSI is considered overbought when above 70 and oversold
        when below 30.
        """

        #logger.debug("RSI:: Relative Strength Index Model Imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "RSI"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        rsi_list = []
        if isinstance(self.stock_list, list):
            if len(self.stock_list) >= 1:
                for stock in self.stock_list:
                    if self.futures_data is None:
                        history = stock.history['Close']
                    else:
                        history = self.futures_data

                    self.rsi = self.calculate_model(history)
                    #logger.debug("RSI VALUES: ")
                    #logger.debug(self.rsi)
                    # provides a smoothed RSI for a year of data good for plotting
                    self.smoothed_rsi = self.smooth_rsi(self.rsi)
                    #logger.debug("SMOOTHED RSI VALUES: ")
                    #logger.debug(self.smooth_rsi)
                    # Here i need a single value not the full year's data
                    if not self.smoothed_rsi.empty:
                        smoothed_rsi_last_value = round(self.smoothed_rsi.iloc[-1],3)
                    else:
                        logger.warning(f"{stock.name} Smoothed RSI Empty.")
                        logger.info(f"{self.rsi}")
                        logger.info(f"{self.smoothed_rsi}")
                        smoothed_rsi_last_value = 0
                    #logger.debug(f"Smoothed RSI Value: {smoothed_rsi_last_value}")
                    rsi_list.append(smoothed_rsi_last_value)

                return rsi_list
            else:
                if self.futures_data is None:
                    history = self.stock_list[0].history['Close']
                else:
                    history = self.futures_data

                self.rsi = self.calculate_model(history)
                self.smoothed_rsi = self.smooth_rsi(self.rsi)
                smoothed_rsi_last_value = round(self.smoothed_rsi.iloc[-1],3)
        else:
            if self.futures_data is None:
                history = self.stock_list.history['Close']
            else:
                history = self.futures_data

            #self.first_period, self.smooth_period = self.calculate_periods(len(history))
            self.rsi = self.calculate_model(history)
            self.smoothed_rsi = self.smooth_rsi(self.rsi)
            smoothed_rsi_last_value = round(self.smoothed_rsi.iloc[-1])
            return smoothed_rsi_last_value


    def calculate_model(self, history):
        self.history = history
        data = self.history
        delta = data.diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        # Filter the first two rsi since there values are meaningless
        filtered_df = rsi.iloc[2:]
        return filtered_df

    def smooth_rsi(self, rsi):
        # Apply exponential moving average to smooth RSI
        smoothed_rsi = rsi.ewm(span=3).mean()
        return smoothed_rsi

    def plot(self, stock_name=None, log_scale=False, subplot=True, show=False, ax=None):
        if stock_name is not None:
            title_string = stock_name + " RSI vs Price"
        else:
            title_string = "RSI vs Price"

        plt.ioff()
        fig = None

        if subplot:
            fig, ax1 = plt.subplots()
            ax1.plot(self.smoothed_rsi, color='red',label='Smoothed RSI')
            ax1.plot(self.rsi, color='blue', label='RSI')
            if log_scale:
                ax1.yscale('log')
            ax1.set_xlabel('TIME')
            ax1.set_ylabel('RSI', color='red')
            ax2 = ax1.twinx()
            ax2.plot(self.history, color='green', label='PRICE HISTORY')
            ax2.set_ylabel('PRICE', color='green')
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
        else:
            plt.plot(self.smoothed_rsi, label='Smoothed RSI')
            plt.plot(self.rsi, label='RSI')
            plt.plot(self.history, label='PRICE HISTORY')
            if log_scale:
                plt.yscale('log')
            plt.xlabel("TIME")
            plt.ylabel("RSI")
            plt.legend()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        plt.title(title_string)
        if show:
            plt.plot()

        return fig
    
    def check_index_type(self, df):
        if pd.api.types.is_datetime64_any_dtype(df.index):
            print("RSI Index is of datetime type.")
        elif pd.api.types.is_string_dtype(df.index):
            print("RSI Index is of string type.")
        else:
            print("RSI Index is of another type.")
## ---------------------------------------------------------------------------##
## ----------------------------- CAPM CLASS ----------- ----------------------##
## ---------------------------------------------------------------------------##

class CAPM:
    def __init__(self, Stock_list=None, md=None, rfr=None, futures_data=None):
        self.stock_list = Stock_list
        self.market_data = md
        self.futures_data = futures_data
        self.risk_free_rate = rfr
        self.caption = """
        The capital asset pricing model (CAPM) describes the relationship between
        systematic risk, or the general perils of investing, and expected return for
        assets, particularly stocks. It is a finance model that establishes a linear
        relationship between the required return on an investment and risk.
        CAPM is based on the relationship between an asset’s beta, the risk-free rate
        (typically the Treasury bill rate), and the equity risk premium, or the expected
        return on the market minus the risk-free rate. CAPM evolved as a way to
        measure this systematic risk. It is widely used throughout finance for
        pricing risky securities and generating expected returns for assets,
        given the risk of those assets and cost of capital.
        """
        self.expected_returns = []
        self.betas = []
        self.beta = []

        #logger.debug("CAPM Model Imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "CAPM"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        #logger.debug("Executing CAPM Model")
        if isinstance(self.stock_list, list):
            if len(self.stock_list) >= 1:
                # Calculate beta (market volatility) and market risk premium for all stocks
                beta_and_market_risk = [self.calculate_beta_and_market_risk_premium(stock) for stock in self.stock_list]
                self.betas, market_risk_premiums = zip(*beta_and_market_risk)
                #logger.debug(f"Beta: {self.betas} mrp: {market_risk_premiums}")
                # Calculate expected return for all stocks
                self.expected_returns = [self.calculate_expected_return(beta, mrp) for beta, mrp in zip(self.betas, market_risk_premiums)]
                #logger.debug(f"Expected Returns: {self.expected_returns}")
        else:
            self.beta, mrp = self.calculate_beta_and_market_risk_premium(self.stock_list)
            self.expected_returns = self.calculate_expected_return(self.beta, mrp)
        return self.expected_returns

    def calculate_beta_and_market_risk_premium(self, stock):
        # Determines market volatility
        stock_data = stock.history
        # Calculate daily returns
        stock_data['daily_return'] = stock_data['Close'].pct_change().dropna()
        #logger.debug(stock_data['daily_return'])
        self.market_data['daily_return'] = self.market_data['Close'].pct_change().dropna()
        #logger.debug(self.market_data['daily_return'])
        # Align data by date 
        aligned_data = pd.concat([stock_data['daily_return'], self.market_data['daily_return']], axis=1).dropna()
        aligned_data.columns = ['stock_return', 'market_return']
        # get the latest available daily return for the S&P 500 index
        try:
            market_return = aligned_data['market_return'].iloc[-1]
        except Exception as e:
            logger.warning(f"{stock.name} returned {e}")
            logger.info(f"{aligned_data}")
            market_return = 0
        # Calculate CAPM metrics
        market_risk_premium = market_return - self.risk_free_rate
        covariance = aligned_data['stock_return'].cov(aligned_data['market_return'])
        market_variance = aligned_data['market_return'].var()
        beta = covariance / market_variance
        return beta, market_risk_premium

    def calculate_expected_return(self, beta, mrp):
        return self.risk_free_rate + beta * mrp

    def plot(self, stock_name, ax=None):
        plt.ioff()
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(self.beta, self.expected_returns, color='red',label=' Beta vs Expected Returns')
        ax1.set_xlabel('Volatility Beta')
        ax1.set_ylabel('Expected Returns', color='red')
        #ax2 = ax1.twinx()
        #ax2.plot(history, color='blue', label='Price History')
        #ax2.set_ylabel('PRICE', color='blue')
        ax1.legend(loc='upper left')
        #ax2.legend(loc='upper right')
        title_string = stock_name + " CAPM Model"
        ax1.set_title(title_string)
        ax1.legend()

        return ax1.figure

## ---------------------------------------------------------------------------##
## -------------------------- FIBONACCI CLASS --------------------------------##
## ---------------------------------------------------------------------------##

class FIBONACCI:
    def __init__(self, Stock_list=None, futures_data=None):
        self.stock_list = Stock_list
        self.time_delta = 14
        self.futures_data = futures_data
        self.history = None
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 1.0]
        self.caption = """
        Fibonacci retracement levels—stemming from the Fibonacci sequence—are
        horizontal lines that indicate where support and resistance are likely to occur.
        Each level is associated with a percentage. The percentage is how much of a
        prior move the price has retraced. The Fibonacci retracement levels are 23.6%,
        38.2%, 61.8%, and 78.6%. While not officially a Fibonacci ratio, 50% is also
        used. The indicator is useful because it can be drawn between any two
        significant price points, such as a high and a low. The indicator will then
        create the levels between those two points.
        "Capital Asset Pricing Model (CAPM)." Investopedia, Investopedia, 2021, www.investopedia.com/terms/c/capm.asp.
        """
        #logger.debug("FIBONACCI model imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "FIBO"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        fibo_list = []
        if isinstance(self.stock_list, list):
            if len(self.stock_list) > 1:
                for stock in self.stock_list:
                    history = stock.history['Close']
                    self.fibo = self.calculate_model(history)
                    fibo_list.append(self.fibo)
                return fibo_list
            else:
                history = self.stock_list[0].history['Close']
                self.fibo = self.calculate_model(history)
        else:
            history = self.stock_list.history['Close']
            self.fibo = self.calculate_model(history)
            return self.fibo

    def calculate_model(self, history):
        self.history = history
        data = self.history
        window = self.calculate_periods(len(data))
        peak_prices = data.rolling(window=window, min_periods=1).max()
        trough_prices = data.rolling(window=window, min_periods=1).min()
        price_move = peak_prices - trough_prices
        self.retracement_levels = [trough_prices + ratio * price_move for ratio in self.fib_levels]
        return self.retracement_levels

    def calculate_periods(self, total_period):
        period = int(round(14*total_period/365,1))
        if period < 1:
            period = 1
        return period

    def plot(self, stock_name=None, ax=None):
        plt.ioff()
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        else:
            fig = ax.figure
        #fig, ax = plt.subplots(figsize=(10, 6))
        title_string = " Fibonacci"
        ax.plot(self.history.index, self.history.values, label='Stock Price', color='green')
        for i, level in enumerate(self.fib_levels):
            retracement_level = self.retracement_levels[i]
            ax.plot(retracement_level.index, retracement_level.values, label=f'Fib Level {level}', linestyle='--')

        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.set_title(title_string)
        ax.legend()

        return fig

## ---------------------------------------------------------------------------##
## -------------------- STOCHASTIC_OCSILLATOR CLASS --------------------------##
## ---------------------------------------------------------------------------##

class STOCHASTIC:
    def __init__(self, Stock_list=None, futures_data=None):
        self.stock_list = Stock_list
        self.futures_data = futures_data
        self.caption = """
        The stochastic oscillator measures the current price relative to the price range
        over a number of periods. Plotted between zero and 100, the idea is that the
        price should make new highs when the trend is up. In a downtrend, the price
        tends to make new lows. The stochastic tracks whether this is happening.
        """
        #logger.debug("STOCHASTIC model imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "STOCHASTIC"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        output_list = []
        if isinstance(self.stock_list, list):
            if len(self.stock_list) >= 1:
                for stock in self.stock_list:
                    if self.futures_data is None:
                        history = stock.history['Close']
                    else:
                        history = self.futures_data
                    self.k, self.d = self.calculate_model(stock, history)
                    # the %k and %d are pretty similar so just taking the average of the
                    # two to output as our performance measure.
                    output = self.calculate_performance_score().mean()
                    #logger.debug(output[0])
                    output_list.append(output[0])
                return output_list
            else:
                if self.futures_data is None:
                    history = self.stock_list[0].history['Close']
                else:
                    history = self.futures_data

                self.k, self.d = self.calculate_model(self.stock_list[0], history)
                output = self.calculate_performance_score().mean()
        else:
            if self.futures_data is None:
                history = self.stock_list.history['Close']
            else:
                history = self.futures_data

            self.k, self.d = self.calculate_model(self.stock_list, history)
            output = self.calculate_performance_score().mean()
            return output[0]


    def calculate_model(self, stock, history):
        self.history = history
        # Calculate highest high and lowest low
        high = stock.history['High'].rolling(window=14).max()
        low = stock.history['Low'].rolling(window=14).min()
        # Calculate %k value
        k_percent = ((self.history - low) / (high - low)) * 100.
        k_percent_smooth = k_percent.rolling(window=3).mean()
        d_percent = k_percent_smooth.rolling(window=3).mean()
        return k_percent_smooth, d_percent

    def calculate_performance_score(self):
        avg_percent = (self.k +  self.d)/2.
        result_df = pd.DataFrame({'Average_Percent':avg_percent})
        return result_df

    def plot(self, stock_name=None, ax=None):
        plt.ioff()
        if stock_name is not None:
            string_title = stock_name + " Stochastic"
        else:
            string_title = "Stochastic Oscillator"
        fig, ax1 = plt.subplots()
        ax1.plot(self.history, label='Stock Price', color='green')
        ax1.set_ylabel('Price', color='green')
        ax2 = ax1.twinx()
        ax2.plot(self.k, label='%K', color='blue')
        ax2.plot(self.d, label='%D', color='red')
        ax2.plot(((self.k+self.d)/2.), label='Avg', color='black',linestyle='--')
        ax2.set_ylabel('%k / %D / Avg', color = 'black')
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        plt.title(string_title)
        #plt.show()
        return fig

## ---------------------------------------------------------------------------##
## ------------------------------- MACD CLASS --------------------------------##
## ---------------------------------------------------------------------------##

class MACD:
    def __init__(self, Stock_list=None, futures_data=None, debug=False):
        self.stock_list = Stock_list
        self.futures_data = futures_data
        self.debug = debug
        self.macd_line = None
        self.signal_line = None
        self.macd_histogram = None
        self.caption = """
        A common way to summarize the performance of a stock based on its MACD data is
        to use the MACD crossover strategy. When the MACD line crosses above
        the signal line, it indicates a bullish signal, suggesting it might be a
        good time to buy. Conversely, when the MACD line crosses below the signal
        line, it indicates a bearish signal, suggesting it might be a good time to sell.
        """
        #logger.debug("MACD --> Model Imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "MACD"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        output_list = []
        output = None
        if isinstance(self.stock_list, list):
            if len(self.stock_list) > 1:
                for stock in self.stock_list:
                    if self.futures_data is None:
                        history = stock.history['Close']
                    else:
                        history = self.futures_data

                    macd_line, signal_line, macd_histogram = self.calculate_model(stock, history)
                    output = self.calculate_performance_score()
                    output_list.append(output)

                return output_list
            else:
                if self.futures_data is None:
                    history = self.stock_list[0].history['Close']
                else:
                    history = self.futures_data

                macd_line, signal_line, macd_histogram = self.calculate_model(self.stock_list[0], history)
                output = self.calculate_performance_score()

        else:
            if self.futures_data is None:
                history = self.stock_list.history['Close']
            else:
                history = self.futures_data

            macd_line, signal_line, macd_histogram = self.calculate_model(self.stock_list, history)
            output = self.calculate_performance_score()

        return output

    def calculate_model(self, myStock, history):
        self.history = history
        short_ema = self.history.ewm(span=12, min_periods=1, adjust=False).mean()
        long_ema = self.history.ewm(span=26, min_periods=1, adjust=False).mean()
        # Calculate MACD Line
        self.macd_line = short_ema - long_ema
        # Calculate signal line
        self.signal_line = self.macd_line.ewm(span=9, min_periods=1, adjust=False).mean()
        self.macd_histogram = self.macd_line - self.signal_line
        return self.macd_line, self.signal_line, self.macd_histogram

    def calculate_performance_score(self):
        performance_score = 0.
        # Iterate over the MACD and signal line data to identify crossovers
        for i in range(1, len(self.macd_line)):
            if self.macd_line[i] > self.signal_line[i] and self.macd_line[i-1] <= self.signal_line[i-1]:
                # Bullish crossover: MACD Line crosses above the signal line
                performance_score += 1
            elif self.macd_line[i] < self.signal_line[i] and self.macd_line[i-1] >= self.signal_line[i-1]:
                # Bearish crossover: MACD line crosses below the signal line
                performance_score -= 1

        return performance_score


    def auto_bin_macd_histogram(self):
        hist_values = self.macd_histogram.values
        iqr = np.subtract(*np.percentile(hist_values, [75, 25]))
        bin_width = 2 * iqr * len(hist_values) ** (-1 / 3)
        num_bins = int(np.ceil((hist_values.max() - hist_values.min()) / bin_width))
        return num_bins

    def plot(self, stock_name=None, show=False, ax=None, bin_size=None, show_histogram=False):
        if stock_name is not None:
            string_title = stock_name + " MACD"
        else:
            string_title = "MACD"

        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(self.macd_line, label='MACD Line', color='blue')
        ax1.plot(self.signal_line, label='Signal Line', color='magenta')

        # Auto-bin if bin_size is not provided
        if bin_size is None:
            bin_size = self.auto_bin_macd_histogram()
        
        # Bin the MACD histogram
        if bin_size > 1:
            binned_histogram = self.macd_histogram.groupby(np.arange(len(self.macd_histogram)) // bin_size).sum()
            binned_index = self.macd_histogram.index[::bin_size]
        else:
            binned_histogram = self.macd_histogram
            binned_index = self.macd_histogram.index

        if show_histogram:
            ax1.bar(binned_index, binned_histogram, label='MACD Histogram', color='black')

        # Identify where the histogram goes from positive to negative
        hist_values = binned_histogram.values
        pos_to_neg = np.where((hist_values[:-1] > 0) & (hist_values[1:] <= 0))[0]
        neg_to_pos = np.where((hist_values[:-1] < 0) & (hist_values[1:] >= 0))[0]

        ymin, _ = ax1.get_ylim()  # Get the current y-axis minimum

        # Plot arrows for positive to negative change
        for idx in pos_to_neg:
            ax1.annotate('', xy=(binned_index[idx + 1], hist_values[idx + 1]),
                         xytext=(binned_index[idx + 1], ymin),
                         arrowprops=dict(color='red', arrowstyle='->'))

        # Plot arrows for negative to positive change
        for idx in neg_to_pos:
            ax1.annotate('', xy=(binned_index[idx + 1], hist_values[idx + 1]),
                         xytext=(binned_index[idx + 1], ymin),
                         arrowprops=dict(color='green', arrowstyle='->'))

        plt.title(string_title)
        ax1.set_xlabel('Date')
        ax1.set_ylabel('MACD')
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        ax2.plot(self.history, label='Stock Price', color='black', linestyle='--')
        ax2.set_ylabel('Stock Price')
        ax2.legend(loc='upper right')

        if show:
            plt.show()

        return fig
    
    def check_index_type(self, df):
        if pd.api.types.is_datetime64_any_dtype(df.index):
            print("MACD Index is of datetime type.")
        elif pd.api.types.is_string_dtype(df.index):
            print("MACD Index is of string type.")
        else:
            print("MACD Index is of another type.")