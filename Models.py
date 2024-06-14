import pandas as pd

"""
Default Model Calculation (simple) calculates how the current price
compares to the average 50 day price. Measures how the stock is doing today.
Measure performance based on how its doing the last 50 days.
ETFs don't always have a current price if current price not available.
Uses the open price if current price not available.
Outputs an array of performances for each stock in stock_list.

"""

class Simple_Model:
    def __init__(self, stock_list=None, debug=False):
        self.stock_list = stock_list
        self.debug = debug
        print("Simple Model Imported.")

    def get_name(self):
        return "Simple"

    def execute_model(self):
        performance = []
        # if self.debug:
        #     print("Model_Handler::calculate_recent_performance Stock List --> ", self.stock_list)
        for stock in self.stock_list:
            current_price = stock.info.get('currentPrice')
            fifty_day_average = stock.info.get('fiftyDayAverage')
            # if self.debug:
            #     print("Model_Handler::calculate_recent_performance ", stock.info.get('symbol'), " Price --> ", current_price)
            #     print("Model_Handler::calculate_recent_performance ", stock.info.get('symbol'), " 50 average --> ", fifty_day_average)
            if current_price is not None:
                performance_measure = current_price - fifty_day_average
            else:
                open_price = stock.info.get('open')
                if open_price is not None:
                    performance_measure = open_price - fifty_day_average
                else:
                    print(Fore.YELLOW + "Model_Handler::calculate_recent_performance: DATA ERROR: Current and Open Prices for " + stock.info.get('name') + " not available." + Style.RESET_ALL)
                    return 0
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
    def __init__(self, stock_list=None, debug=False):
        self.stock_list = stock_list
        self.debug = debug
        print("RelativeStrengthIndex Imported.")

    def __del__(self):
        pass

    def get_name(self):
        return "RSI"

    def execute_model(self):
        self.set_my_parameters(stock_list, market_data, risk_free_rate, time_delta, debug)
        rsi_list = []
        for stock in self.stock_list:
            self.set_history(stock)
            rsi = self.calculate_rsi()
            smoothed_rsi = self.smooth_rsi(rsi)
            rsi_list.append(smoothed_rsi)

        return rsi_list

    def set_my_parameters(self, stock_list=None, market_data=None, risk_free_rate=None, time_delta=None, debug=False):
        self.stock_list = [stock_list] # must convert to a list of objects first
        self.market_data = market_data
        self.risk_free_rate = risk_free_rate
        self.time_delta = time_delta
        self.debug = debug

    def set_history(self, stock):
        df = pd.DataFrame(stock.history(period="1y"))
        if self.debug:
            print(df)
        self.history = df['Close']
        if self.debug:
            print("RelativeStrengthIndex::set_history history --> ", self.history)


    def calculate_rsi(self, period=14):
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

    def get_name(self):
        return "CAPM"

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
