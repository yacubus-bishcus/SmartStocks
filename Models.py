import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import logging
import sys
from datetime import datetime, timedelta
import numpy as np
from StockApp.Simulation_Analysis import Simulation_Analysis
from StockApp.MonteCarlo import MonteCarlo

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

    def set_history(self, myStock, futures_data, time_period):
        # Create DataFrame from MyStock's history
        if time_period == "1y":
            df = pd.DataFrame(myStock.the_year_history)
        elif time_period == "ytd":
            df = pd.DataFrame(myStock.the_ytd_history)
        elif time_period == "6mo":
            df = pd.DataFrame(myStock.the_6mo_history)
        elif time_period == "3mo":
            df = pd.DataFrame(myStock.the_3mo_history)
        elif time_period == "1mo":
            df = pd.DataFrame(myStock.the_month_history)
        elif time_period == "5d":
            df = pd.DataFrame(myStock.the_5d_history)
        elif time_period == "1d":
            df = pd.DataFrame(myStock.the_day_history)
        else:
            logger.error(f"Time Period must be one of the following options: 1yr, ytd, 6mo, 3mo, 1mo, 5d, 1d. Your time period: {time_period}")
            sys.exit(1)

        if futures_data is not None:
            if not isinstance(futures_data, pd.DataFrame):
                futures_data = pd.DataFrame(futures_data)

            # if 'Date' in futures_data.index.names:
            #     # Reset index to make data a regular column
            #     futures_data.reset_index(inplace=True)
            # Ensure 'Date' column is in datetime format
            futures_data.index = pd.to_datetime(futures_data.index)
            futures_data.index = futures_data.index.date
            if 'Price' not in futures_data.columns:
                logger.warning("Price not in Future Data Column. Potential data formating will lead to improper plotting.")

            # Extract 'Date' and 'Close' prices from MyStock's history
            history = pd.DataFrame(df['Close'])
            # if 'Date' in history.index.names:
            #     history.reset_index(inplace=True)
            history.columns = ['Price']
            history.index = pd.to_datetime(history.index)
            history.index = history.index.date

            # Concatenate history and futures_data along rows
            combined_history = pd.concat([history, futures_data], axis=0, ignore_index=False)
            combined_history.index = combined_history.index.rename('Date')
            # Convert 'Date' column to datetime and set timezone to 'America/New_York'
            #combined_history['Date'] = pd.to_datetime(history['Date'], utc=True).dt.tz_convert('America/New_York')
            combined_series = combined_history['Price']

            return combined_series
        else:
            # If no futures_data provided, just use 'Close' prices from MyStock's history
            try:
                series = df['Close']
            except:
                logger.warning(f"{myStock.name} failed to grab {time_period} history.")
                logger.exception(df)
                sys.exit(1)
            return df['Close']

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
        logger.debug("Models::Fifty_Day_Model --> 50 Day Model Imported.")

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
                    logger.error(Fore.YELLOW + f"Models::Fifty_Day_Model::execute_model DATA ERROR: Current and Open Prices for {stock.info.get('name')} not available." + Style.RESET_ALL)
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
        logger.debug("Models::TwoHundred_Day_Model --> 200 Day Average Model Imported.")

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
                logger.error(Fore.YELLOW + "Models::TwoHundred_Day_Model::execute_model DATA ERROR: 200 Day Average for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                return None
            if current_price is not None:
                performance_measure = current_price - average
            else:
                open_price = stock.info.get('open')
                if open_price is not None:
                    performance_measure = open_price - average
                else:
                    logger.error(Fore.YELLOW + "Models::TwoHundred_Day_Model::execute_model DATA ERROR: Current and Open Prices for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                    return None
            performance.append(performance_measure)

        return performance

    def plot(self, ax):
        return

## ---------------------------------------------------------------------------##
## ----------------------------- RSI CLASS ----------- ----------------------##
## ---------------------------------------------------------------------------##

class RSI:
    def __init__(self, myStock_list=None, futures_data=None, time_period="1mo"):
        self.stock_list = myStock_list
        self.futures_data = futures_data
        self.time_period = time_period
        self.first_period = None
        self.smooth_period = None
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

        logger.debug("Models::RSI:: Relative Strength Index Model Imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "RSI"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        models = Models(myStockList=self.stock_list)
        rsi_list = []
        if isinstance(self.stock_list, list):
            if len(self.stock_list) > 1:
                for stock in self.stock_list:
                    history = models.set_history(stock, self.futures_data, self.time_period)
                    self.first_period, self.smooth_period = self.calculate_periods(len(history))
                    self.rsi = self.calculate_model(history, self.first_period)
                    # provides a smoothed RSI for a year of data good for plotting
                    self.smoothed_rsi = self.smooth_rsi(self.rsi, self.smooth_period)
                    # Here i need a single value not the full year's data
                    smoothed_rsi_last_value = self.smoothed_rsi.iloc[-1]
                    rsi_list.append(smoothed_rsi_last_value)

                return rsi_list
        else:
            history = models.set_history(self.stock_list, self.futures_data, self.time_period)
            self.first_period, self.smooth_period = self.calculate_periods(len(history))
            self.rsi = self.calculate_model(history, self.first_period)
            self.smoothed_rsi = self.smooth_rsi(self.rsi, self.smooth_period)
            smoothed_rsi_last_value = self.smoothed_rsi.iloc[-1]
            return smoothed_rsi_last_value

    # RSI model doesn't actually use market_data, risk_free_rate or time_delta
    # self.stock_list input is set by Model_Handler. self.stock_list is a list
    # of MyStock objects
    def set_my_parameters(self, stock_list=None, market_data=None, risk_free_rate=None, time_delta=None):
        self.stock_list = [stock_list] # must convert to a list of objects first
        self.market_data = market_data
        self.risk_free_rate = risk_free_rate
        self.time_delta = time_delta


    def calculate_model(self, history, period=14):
        self.history = history
        data = self.history
        delta = data.diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        # Filter the first two rsi since there values are meaningless
        filtered_df = rsi.iloc[2:]
        return filtered_df

    def calculate_periods(self, total_period):
        first_period = int(round(14*total_period/365))
        if first_period < 1:
            first_period = 1
        smooth_period = int(round(3*total_period/365))
        if smooth_period < 1:
            smooth_period = 2

        return first_period, smooth_period

    def smooth_rsi(self, rsi, smoothing_period=3):
        # Apply exponential moving average to smooth RSI
        smoothed_rsi = rsi.ewm(span=smoothing_period).mean()
        return smoothed_rsi

    def plot(self, stock_name, log_scale=False, subplot=True, ax=None):
        title_string = stock_name + " RSI vs Price"
        plt.ioff()
        fig = None
        logger.info(f"RSI Model First Period: {self.first_period} Smoothing Period: {self.smooth_period}")
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
        return fig

## ---------------------------------------------------------------------------##
## ----------------------------- CAPM CLASS ----------- ----------------------##
## ---------------------------------------------------------------------------##

class CAPM:
    def __init__(self, myStock_list=None, md=None, rfr=None, td="1mo", futures_data=None):
        self.stock_list = myStock_list
        self.market_data = md
        self.futures_data = futures_data
        self.risk_free_rate = rfr
        self.time_delta = td
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

    def __del__(self):
        pass

    def get_name(self):
        return "CAPM"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        if isinstance(self.stock_list, list):
            if len(self.stock_list) > 1:
                # Calculate beta (market volatility) and market risk premium for all stocks
                beta_and_market_risk = [self.calculate_beta_and_market_risk_premium(stock) for stock in self.stock_list]
                self.betas, market_risk_premiums = zip(*beta_and_market_risk)
                # Calculate expected return for all stocks
                self.expected_returns = [self.calculate_expected_return(beta, mrp) for beta, mrp in zip(self.betas, market_risk_premiums)]
        else:
            self.beta, mrp = self.calculate_beta_and_market_risk_premium(self.stock_list)
            self.expected_returns = self.calculate_expected_return(self.beta, mrp)

        return self.expected_returns

    def calculate_beta_and_market_risk_premium(self, stock):
        # Determines market volatility
        stock_data = stock.history(period=self.time_delta)
        # Calculate daily returns
        stock_data['daily_return'] = stock_data['Close'].pct_change().dropna()
        # get the latest available daily return for the S&P 500 index
        market_return = self.market_data['daily_return'].iloc[-1]
        # Calculate CAPM metrics
        market_risk_premium = market_return - self.risk_free_rate
        covariance = stock_data['daily_return'].cov(self.market_data['daily_return'])
        market_variance = self.market_data['daily_return'].var()
        beta = covariance / market_variance
        return beta, market_risk_premium

    def calculate_history(self):
        models = Models(myStockList=self.stock_list)
        return models.set_history(self.stock_list, self.futures_data, self.time_delta)

    def calculate_expected_return(self, beta, mrp):
        return self.risk_free_rate + beta * mrp

    def plot(self, stock_name, ax=None):
        plt.ioff()
        #history = self.calculate_history()
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
    def __init__(self, myStock_list=None, futures_data=None, time_period="1mo"):
        self.stock_list = myStock_list
        if time_period == "1y":
            self.time_delta = 14
        elif time_period == "1mo":
            self.time_delta = 7
        else:
            self.time_delta = 1

        self.time_period = time_period
        self.futures_data = futures_data
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
        logger.debug("FIBONACCI model imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "FIBO"

    def get_caption(self):
        return self.caption

    def execute_model(self):
        fibo_list = []
        models = Models(myStockList=self.stock_list)
        if isinstance(self.stock_list, list):
            if len(self.stock_list) > 1:
                for stock in self.stock_list:
                    history = models.set_history(stock, self.futures_data, self.time_period)
                    self.fibo = self.calculate_model(history)
                    fibo_list.append(self.fibo)
                return fibo_list
        else:
            history = models.set_history(self.stock_list, self.futures_data, self.time_period)
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

    def plot(self, stock_name, ax=None):
        plt.ioff()
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        else:
            fig = ax.figure
        #fig, ax = plt.subplots(figsize=(10, 6))
        title_string = stock_name + " Fibonacci"
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
    def __init__(self, myStock_list=None, time_period="1mo", futures_data=None):
        self.stock_list = myStock_list
        self.futures_data = futures_data
        self.caption = """
        The stochastic oscillator measures the current price relative to the price range
        over a number of periods. Plotted between zero and 100, the idea is that the
        price should make new highs when the trend is up. In a downtrend, the price
        tends to make new lows. The stochastic tracks whether this is happening.
        """
        self.time_period = time_period
        logger.debug("STOCHASTIC model imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "STOCHASTIC"

    def get_caption(self):
        return self.caption

    def calculate_periods(self, total_period):
        window_period = int(round(14*total_period/365))
        smooth_period = int(round(3*total_period/365))
        if window_period < 1:
            window_period = 1
        if smooth_period < 1:
            smooth_period = 1

        return window_period, smooth_period

    def execute_model(self):
        output_list = []
        models = Models(myStockList=self.stock_list)
        if isinstance(self.stock_list, list):
            if len(self.stock_list) > 1:
                for stock in self.stock_list:
                    history = models.set_history(stock, self.futures_data, self.time_period)
                    self.k, self.d = self.calculate_model(stock, history)
                    # the %k and %d are pretty similar so just taking the average of the
                    # two to output as our performance measure.
                    output = self.calculate_performance_score().mean()
                    output_list.append(output)
                return output_list
        else:
            history = models.set_history(self.stock_list, self.futures_data, self.time_period)
            self.k, self.d = self.calculate_model(self.stock_list, history)
            output = self.calculate_performance_score().mean()
            return output


    def calculate_model(self, myStock, history):
        self.history = history
        # Calculate highest high and lowest low
        window, smoothing = self.calculate_periods(len(self.history))
        high = myStock.the_year_history['High'].rolling(window=window).max()
        low = myStock.the_year_history['Low'].rolling(window=window).min()
        # Calculate %k value
        k_percent = ((self.history - low) / (high - low)) * 100.
        k_percent_smooth = k_percent.rolling(window=smoothing).mean()
        d_percent = k_percent_smooth.rolling(window=smoothing).mean()
        return k_percent_smooth, d_percent

    def calculate_performance_score(self):
        avg_percent = (self.k +  self.d)/2.
        result_df = pd.DataFrame({'Average_Percent':avg_percent})
        return result_df

    def plot(self, stock_name, ax=None):
        plt.ioff()
        string_title = stock_name + " Stochastic"
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
    def __init__(self, myStock_list=None, futures_data=None, time_period="1mo"):
        self.stock_list = myStock_list
        self.time_period = time_period
        self.futures_data = futures_data
        self.short_period = 0
        self.long_period = 0
        self.signal_period = 0
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
        logger.debug("Models::MACD --> Model Imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "MACD"

    def get_caption(self):
        return self.caption

    def calculate_periods(self, total_period):
        short_period = int(round(12*total_period/365,1))
        if short_period < 1:
            short_period = 1
        long_period = int(round(26*total_period/365,1))
        if long_period < 1:
            long_period = short_period + 2
        signal_period = int(round(9*total_period/365,1))
        if signal_period < 1 or signal_period <= short_period:
            signal_period = short_period + 1

        return short_period, long_period, signal_period

    def execute_model(self):
        output_list = []
        model = Models(myStockList=self.stock_list)
        if isinstance(self.stock_list, list):
            if len(self.stock_list) > 1:
                for stock in self.stock_list:
                    history = model.set_history(stock, self.futures_data, self.time_period)
                    macd_line, signal_line, macd_histogram = self.calculate_model(stock, history)
                    output = self.calculate_performance_score()
                    output_list.append(output)

                return output_list
        else:
            history = model.set_history(self.stock_list, self.futures_data, self.time_period)
            macd_line, signal_line, macd_histogram = self.calculate_model(self.stock_list, history)
            output = self.calculate_performance_score()
            return output

    def calculate_model(self, myStock, history):
        self.history = history
        if self.short_period == 0:
            self.short_period, self.long_period, self.signal_period = self.calculate_periods(len(self.history))
        short_ema = self.history.ewm(span=self.short_period, min_periods=self.short_period, adjust=False).mean()
        long_ema = self.history.ewm(span=self.long_period, min_periods=self.long_period, adjust=False).mean()
        # Calculate MACD Line
        self.macd_line = short_ema - long_ema
        # Calculate signal line
        self.signal_line = self.macd_line.ewm(span=self.signal_period, min_periods=self.signal_period, adjust=False).mean()
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

    def plot(self, stock_name, show=False, ax=None):
        string_title = stock_name + " MACD"
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(self.macd_line, label='MACD Line', color='blue')
        ax1.plot(self.signal_line, label='Signal Line', color='magenta')
        ax1.bar(self.macd_histogram.index, self.macd_histogram, label='MACD Histogram', color='black')

        # Identify where the histogram goes from positive to negative
        hist_values = self.macd_histogram.values
        pos_to_neg = np.where((hist_values[:-1] > 0) & (hist_values[1:] <= 0))[0]
        neg_to_pos = np.where((hist_values[:-1] < 0) & (hist_values[1:] >= 0))[0]

        # Log information
        logger.info(f"MACD Model Short Period: {self.short_period} Long Period: {self.long_period} Signal Period: {self.signal_period}")

        ymin, _ = ax1.get_ylim()  # Get the current y-axis minimum

        # Plot arrows for positive to negative change
        for idx in pos_to_neg:
            ax1.annotate('', xy=(self.macd_histogram.index[idx + 1], hist_values[idx + 1]),
                         xytext=(self.macd_histogram.index[idx + 1], ymin),
                         arrowprops=dict(color='red', arrowstyle='->'))

        # Plot arrows for negative to positive change
        for idx in neg_to_pos:
            ax1.annotate('', xy=(self.macd_histogram.index[idx + 1], hist_values[idx + 1]),
                         xytext=(self.macd_histogram.index[idx + 1], ymin),
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

## ---------------------------------------------------------------------------##
## ----------------------------- FUTURES CLASS -------------------------------##
## ---------------------------------------------------------------------------##

class FUTURES:
    def __init__(self, futures_data=None, market_data=None, market_stock=None, args=None):
        self.futures_data = futures_data
        self.market_data = market_data
        self.market_stock = market_stock
        self.args = args
        self.sim_time = 30
        self.simulations = 100
        self.processes = 1
        self.model_time_delta = '1mo'
        self.price_processing_model = 'close_open'
        self.simulation_model = 'gaussian'
        if self.args is not None:
            self.sim_time = self.args.sim_time
            self.simulations = self.args.simulations
            self.processes = self.args.processes
            self.model_time_delta = self.args.model_time_delta
            self.price_processing_model = self.args.price_processing_model
            self.simulation_model = self.args.simulation_model

        self.analysis = Simulation_Analysis(self.args)
        self.caption = """
        Future prices here are calculated from a monte carlo calculation incorporating
        drift, volatility and jumps of a stock over the desired time horizon.
        The jump threshold standard deviation used was two standard deviations.
        """

    def __del__(self):
        pass

    def get_name(self, name):
        return "FUTURES"

    def get_caption(self):
        return self.caption

    def set_number_of_simulations(self, num_sim):
        self.simulations = num_sim

    def set_sim_time(self, sim_time):
        self.sim_time = sim_time

    def set_processes(self, processes):
        self.processes = processes

    def execute_model(self):
        drift, volatility = self.analysis.calculate_drift_and_volatility(self.market_data['Close']) # takes series of the closed prices
        if self.price_processing_model == "close_open":
            monte = MonteCarlo(data=self.market_data, num_simulations=self.simulations, sim_time=self.sim_time, processes=self.processes, jump_param=self.args.jump_parameter, apply_function=self.analysis.stock_price_processing_close_open)
        elif self.price_processing_model == 'high_low':
            monte = MonteCarlo(data=self.market_data, num_simulations=self.simulations, sim_time=self.sim_time, processes=self.processes, jump_param=self.args.jump_parameter, apply_function=self.analysis.stock_price_processing_high_low)

        monte.calculate_initial_condition(['avg_prices', 'historical_returns'])

        if self.processes > 1:
            simulated_price = monte.execute_normal_simulation_with_mp(drift=drift, volatility=volatility)
        else:
            simulated_price = monte.execute_normal_simulation(drift=drift, volatility=volatility) # all simulated prices for individual stock

        market_sim_df = pd.DataFrame(simulated_price) # write to 2-D dataframe
        market_sim_series = market_sim_df.mean(axis=0)
        market_sim_series.name = 'Price'
        dates = [datetime.today() + timedelta(days=i) for i in range(len(market_sim_series))]
        futures = market_sim_series.to_frame().reset_index(drop=True)
        futures['Date'] = dates
        futures.set_index('Date', inplace=True)
        model = Models()
        self.market_combined_df = model.set_history(self.market_stock, futures, self.model_time_delta)

    def plot(self, stock_name=None, ax=None):
        plt.ioff()
        string_title = stock_name + " Future Prices"
        fig, ax1 = plt.subplots(figsize=(10,6))
        ax1.plot(self.futures_data.index, self.futures_data.values, label='Predicted Price', color='blue')
        xlabel_string = "Date"
        ax1.set_xlabel(xlabel_string)
        ax1.set_ylabel("Predicted Price")
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        ax2.plot(self.market_combined_df.index, self.market_combined_df.values, label='Market Predicted Price', color='red')
        ax2.set_ylabel("Market Predicted Price")
        ax2.legend(loc='upper right')
        plt.title(string_title)
        fig.autofmt_xdate()
        return fig
