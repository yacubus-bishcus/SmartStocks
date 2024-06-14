import pandas as pd
import matplotlib.pyplot as plt


class Models:
    def __init__(self, myStockList=None, debug=False):
        self.stock_list = myStockList
        self.debug = debug

    def __del__(self):
        pass

    def get_name(self, name):
        return name

    def set_history(self, myStock):
        # here I'm using MyStock's history which is set when MyStock object is
        # initialized. The history is for 1 year. It is set to 1 year and not
        # the last 14 days for plotting purposes only.
        df = pd.DataFrame(myStock.the_history)
        if self.debug:
            print("Models::set_history 1 Year History --> ")
            print(df.head(5))
        history = df['Close']
        if self.debug:
            print("Models::set_history Close Column --> ")
            print(history.head(5))
        return history

    def execute_model(self):
        output_list = []
        for stock in self.stock_list:
            self.set_history(stock)
            self.output = self.calculate_stoch()
            output_list.append(self.output)

        return output_list


"""
Default Model Calculation (simple) calculates how the current price
compares to the average 50 day price. Measures how the stock is doing today.
Measure performance based on how its doing the last 50 days.
ETFs don't always have a current price if current price not available.
Uses the open price if current price not available.
Outputs an array of performances for each stock in stock_list.

"""

class Fifty_Day_Model:
    def __init__(self, stock_list=None, debug=False):
        self.stock_list = stock_list
        self.debug = debug
        if self.debug:
            print("Models::Fifty_Day_Model --> 50 Day Model Imported.")

    def get_name(self):
        return "50 Day"

    def execute_model(self):
        performance = []
        # if self.debug:
        #     print("Model_Handler::calculate_recent_performance Stock List --> ", self.stock_list)
        for stock in self.stock_list:
            current_price = stock.price
            fifty_day_average = stock.fifty_percent
            if fifty_day_average is None:
                print(Fore.YELLOW + "Models::Fifty_Day_Model::execute_model DATA ERROR: Fifty Day Average for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                return None
            if current_price is not None:
                performance_measure = current_price - fifty_day_average
            else:
                open_price = stock.info.get('open')
                if open_price is not None:
                    performance_measure = open_price - fifty_day_average
                else:
                    print(Fore.YELLOW + "Models::Fifty_Day_Model::execute_model DATA ERROR: Current and Open Prices for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                    return None
            performance.append(performance_measure)

        return performance

"""
Default Model Calculation (simple) calculates how the current price
compares to the average 200 day price. Measures how the stock is doing today.
Measure performance based on how its doing the last 200 days.
ETFs don't always have a current price if current price not available.
Uses the open price if current price not available.
Outputs an array of performances for each stock in stock_list.

"""

class TwoHundred_Day_Model:
    def __init__(self, stock_list=None, debug=False):
        self.stock_list = stock_list
        self.debug = debug
        if self.debug:
            print("Models::TwoHundred_Day_Model --> 200 Day Average Model Imported.")

    def get_name(self):
        return "200 Day"

    def execute_model(self):
        performance = []
        for stock in self.stock_list:
            current_price = stock.price
            average = stock.twohundred_percent

            if average is None:
                print(Fore.YELLOW + "Models::TwoHundred_Day_Model::execute_model DATA ERROR: 200 Day Average for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                return None
            if current_price is not None:
                performance_measure = current_price - average
            else:
                open_price = stock.info.get('open')
                if open_price is not None:
                    performance_measure = open_price - average
                else:
                    print(Fore.YELLOW + "Models::TwoHundred_Day_Model::execute_model DATA ERROR: Current and Open Prices for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                    return None
            performance.append(performance_measure)

        return performance
"""
As a momentum indicator, the relative strength index compares a security's
strength on days when prices go up to its strength on days when prices go down.
Relating the result of this comparison to price action can give traders an idea
of how a security may perform. (Steve Nison. "Japanese Candlestick Charting
Techniques, 2nd Edition," Page 226. New York Institute of Finance, 2001.)
The RSI, used in conjunction with other technical
indicators, can help traders make better-informed trading decisions
(P. J. Kaufman. "Trading Systems and Methods," Pages 345-350 John Wiley &
Sons, 2019, sixth edition.)

"""
class RSI:
    def __init__(self, myStock_list=None, debug=False):
        self.stock_list = myStock_list
        self.debug = debug
        # Initalize variables for plotting
        self.rsi = None
        self.smoothed_rsi = None
        self.history = None
        if self.debug:
            print("Models::RSI:: Relative Strength Index Model Imported.")

    def __del__(self):
        pass

    # def get_name(self):
    #     return "RSI"

    def execute_model(self):
        #self.set_my_parameters(stock_list, market_data, risk_free_rate, time_delta, debug)
        models = Models(myStockList=self.stock_list, debug=self.debug)
        rsi_list = []
        for stock in self.stock_list:
            history = models.set_history(stock)
            self.rsi = self.calculate_model(history)
            # provides a smoothed RSI for a year of data good for plotting
            self.smoothed_rsi = self.smooth_rsi(self.rsi)
            # Here i need a single value not the full year's data
            smoothed_rsi_last_value = self.smoothed_rsi.iloc[-1]
            rsi_list.append(smoothed_rsi_last_value)

        return rsi_list

    # RSI model doesn't actually use market_data, risk_free_rate or time_delta
    # self.stock_list input is set by Model_Handler. self.stock_list is a list
    # of MyStock objects
    def set_my_parameters(self, stock_list=None, market_data=None, risk_free_rate=None, time_delta=None, debug=False):
        self.stock_list = [stock_list] # must convert to a list of objects first
        self.market_data = market_data
        self.risk_free_rate = risk_free_rate
        self.time_delta = time_delta
        self.debug = debug


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

    def smooth_rsi(self, rsi, smoothing_period=3):
        # Apply exponential moving average to smooth RSI
        smoothed_rsi = rsi.ewm(span=smoothing_period).mean()
        return smoothed_rsi

    def plot(self, stock_name, log_scale=False, subplot=False):
        title_string = stock_name + " RSI vs Price"
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

        plt.title(title_string)
        plt.show()

"""
The capital asset pricing model (CAPM) describes the relationship between
systematic risk, or the general perils of investing, and expected return for
assets, particularly stocks. It is a finance model that establishes a linear
relationship between the required return on an investment and risk.
CAPM is based on the relationship between an asset’s beta, the risk-free rate
(typically the Treasury bill rate), and the equity risk premium, or the expected
return on the market minus the risk-free rate.
CAPM evolved as a way to measure this systematic risk.
It is widely used throughout finance for pricing risky securities and
generating expected returns for assets, given the risk of those assets and cost
of capital.
"Capital Asset Pricing Model (CAPM)." Investopedia, Investopedia, 2021, www.investopedia.com/terms/c/capm.asp.
"""
class CAPM:
    def __init__(self, stock_list=None, market_data=None, risk_free_rate=None, time_delta="1mo", debug=False):
        self.stock_list = stock_list
        self.market_data = market_data
        self.risk_free_rate = risk_free_rate
        self.time_delta = time_delta
        self.debug = debug
        if self.debug:
            print("Models::CAPM:: CAPM Model Imported")

    def __del__(self):
        pass

    # def get_name(self):
    #     return "CAPM"

    def execute_model(self):
        # Calculate beta (market volatility) and market risk premium for all stocks
        beta_and_market_risk = [self.calculate_beta_and_market_risk_premium(stock) for stock in self.stock_list]
        betas, market_risk_premiums = zip(*beta_and_market_risk)
        # Calculate expected return for all stocks
        expected_returns = [self.calculate_expected_return(beta, mrp) for beta, mrp in zip(betas, market_risk_premiums)]
        return expected_returns

    def calculate_beta_and_market_risk_premium(self, stock):
        # Determines market volatility
        if self.debug:
            print("Model_Handler::calculate_beta_and_market_risk_premium Stock Info --> ", stock.info.get('symbol'))

        stock_data = stock.history(period=self.time_delta)
        # Calculate daily returns
        stock_data['daily_return'] = stock_data['Close'].pct_change()
        # get the latest available daily return for the S&P 500 index
        market_return = self.market_data['daily_return'].iloc[-1]
        # Calculate CAPM metrics
        market_risk_premium = market_return - self.risk_free_rate
        covariance = stock_data['daily_return'].cov(self.market_data['daily_return'])
        market_variance = self.market_data['daily_return'].var()
        beta = covariance / market_variance
        return beta, market_risk_premium


    def calculate_expected_return(self, beta, mrp):
        return self.risk_free_rate + beta * mrp


class FIBONACCI:
    def __init__(self, myStock_list=None, time_delta=14, debug=False):
        self.stock_list = myStock_list
        self.time_delta = time_delta
        self.debug = debug
        self.fib_levels = [0.236, 0.382, 0.5, 0.618,1.0]
        if self.debug:
            print("Models::FIBONACCI model imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "FIBONACCI"

    def execute_model(self):
        fibo_list = []
        models = Models(myStockList=self.stock_list, debug=self.debug)
        for stock in self.stock_list:
            history = models.set_history(stock)
            self.fibo = self.calculate_model(history)
            fibo_list.append(self.fibo)

        return fibo_list

    def calculate_model(self, history):
        self.history = history
        data = self.history
        peak_prices = data.rolling(window=14, min_periods=1).max()
        trough_prices = data.rolling(window=14, min_periods=1).min()
        price_move = peak_prices - trough_prices

        self.retracement_levels = [trough_prices + ratio * price_move for ratio in self.fib_levels]
        # if self.debug:
        #     print("Models::FIBONACCI::calculate_fibo Retracement Levels --> ")
        #     for i, level in enumerate(self.retracement_levels):
        #         print(f"Level {i+1}: {level}")

        return self.retracement_levels

    def plot(self, stock_name):
        title_string = stock_name + " Fibonacci Retracement Levels"
        plt.figure(figsize=(10,6))
        plt.plot(self.history.index, self.history.values, label='Stock Price', color='green')
        for i, level in enumerate(self.fib_levels):
            retracement_level = self.retracement_levels[i] # get the dataframe for the current level
            plt.plot(retracement_level.index, retracement_level.values, label=f'Fib Level {level}', linestyle='--')

        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.title(title_string)
        plt.legend()
        plt.show()

"""
The stochastic oscillator measures the current price relative to the price range
 over a number of periods. Plotted between zero and 100, the idea is that the
 price should make new highs when the trend is up. In a downtrend, the price
 tends to make new lows. The stochastic tracks whether this is happening.
 "Investopedia. (n.d.). Top 7 Technical Analysis Tools. Retrieved from
 https://www.investopedia.com/top-7-technical-analysis-tools-4773275"
"""

class STOCHASTIC_OCSILLATOR:
    def __init__(self, myStock_list=None, time_delta=14, smoothing=3, debug=False):
        self.stock_list = myStock_list
        self.period = time_delta
        self.smoothing = smoothing
        self.debug = debug
        if self.debug:
            print("Models::STOCHASTIC_OCSILLATOR model imported.")

    def __del__(self):
        pass

    def get_name(self, name):
        return name

    def execute_model(self):
        output_list = []
        models = Models(myStockList=self.stock_list, debug=self.debug)
        for stock in self.stock_list:
            history = models.set_history(stock)
            self.k, self.d = self.calculate_model(stock, history)
            # the %k and %d are pretty similar so just taking the average of the
            # two to output as our performance measure.
            output_list.append((self.k + self.d)/2.)

        return output_list

    def calculate_model(self, myStock, history):
        self.history = history
        # Calculate highest high and lowest low
        high = myStock.the_history['High'].rolling(window=self.period).max()
        low = myStock.the_history['Low'].rolling(window=self.period).min()
        # Calculate %k value
        k_percent = ((self.history - low) / (high - low)) * 100.
        k_percent_smooth = k_percent.rolling(window=self.smoothing).mean()
        d_percent = k_percent_smooth.rolling(window=self.smoothing).mean()
        if self.debug:
            print("Models::STOCHASTIC_OCSILLATOR K Percent Smooth -->")
            print(k_percent_smooth.head(5))
            print("Models::STOCHASTIC_OCSILLATOR D Percent -->")
            print(d_percent.head(5))
        return k_percent_smooth, d_percent

    def plot(self, stock_name):
        string_title = stock_name + " Stochastic Oscillator"
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
        plt.show()

"""
A common way to summarize the performance of a stock based on its MACD data is
to use the MACD crossover strategy. In this strategy, you track the crossovers
between the MACD line and the signal line. When the MACD line crosses above
the signal line, it indicates a bullish signal, suggesting it might be a
good time to buy. Conversely, when the MACD line crosses below the signal
line, it indicates a bearish signal, suggesting it might be a good time to sell.
"""

class MACD:
    def __init__(self, myStock_list=None, short_period=12, long_period=26, signal_period=9, debug=False):
        self.stock_list = myStock_list
        self.short_period = short_period
        self.long_period = long_period
        self.signal_period = signal_period
        self.debug = debug
        if self.debug:
            print("Models::MACD --> Model Imported.")

    def __del__(self):
        pass

    def get_name(self, name):
        return name

    def execute_model(self):
        output_list = []
        model = Models(myStockList=self.stock_list, debug=self.debug)
        for stock in self.stock_list:
            history = model.set_history(stock)
            macd_line, signal_line, macd_histogram = self.calculate_model(stock, history)
            output = self.calculate_performance_score()
            output_list.append(output)

        return output_list

    def calculate_model(self, myStock, history):
        self.history = history
        short_ema = self.history.ewm(span=self.short_period, min_periods=self.short_period, adjust=False).mean()
        long_ema = self.history.ewm(span=self.long_period, min_periods=self.long_period, adjust=False).mean()
        # Calculate MACD Line
        self.macd_line = short_ema - long_ema
        # Calculate signal line
        self.signal_line = self.macd_line.ewm(span=self.signal_period, min_periods=self.signal_period, adjust=False).mean()
        self.macd_histogram = self.macd_line - self.signal_line
        if self.debug:
            print("Models::calculate_model MACD Line -->")
            print(self.macd_line)
        return self.macd_line, self.signal_line, self.macd_histogram

    def calculate_performance_score(self):
        performance_score = 0.
        # Iterate over the MACD and signal line data to identify crossovers
        for i in range(1, len(self.macd_line)):
            if self.macd_line[i] > self.signal_line[i] and self.macd_line[i-1] <= self.signal_line[i-1]:
                # Bullish crossover: MACD Line crosses above the signal line
                performance += 1
            elif self.macd_line[i] < self.signal_line[i] and self.macd_line[i-1] >= self.signal_line[i-1]:
                # Bearish crossover: MACD line crosses below the signal line
                performance_score -= 1
        if self.debug:
            print("Models::MACD::calculate_performance_score --> ")
            print(performance_score)

        return performance_score

    def plot(self, stock_name):
        string_title = stock_name + " MACD Analysis"
        fig, ax1 = plt.subplots(figsize=(10,6))
        ax1.plot(self.macd_line, label='MACD Line', color='blue')
        ax1.plot(self.signal_line, label='Signal Line', color='red')
        ax1.bar(self.macd_histogram.index, self.macd_histogram, label='MACD Histogram', color='green')
        plt.title(string_title)
        ax1.set_xlabel('Date')
        ax1.set_ylabel('MACD')
        ax1.legend(loc='upper left')
        ax2 = ax1.twinx()
        ax2.plot(self.history, label='Stock Price', color='black', linestyle='--')
        ax2.set_ylabel('Stock Price')
        ax2.legend(loc='upper right')
        plt.show()
