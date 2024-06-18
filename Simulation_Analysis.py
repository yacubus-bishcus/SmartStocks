class Simulation_Analysis:
    def __init__(self, args=None):
        self.args = args

    def __del__(self):
        pass

    def stock_price_processing_close_open(self, data):
        avg_prices = data[['Open', 'High', 'Close', 'Low']].mean(axis=1)
        historical_returns = data['Close'] - data['Open'] # some thought to making this high and low to have more variation
        return {'avg_prices':avg_prices, 'historical_returns':historical_returns}

    def stock_price_processing_high_low(self, data):
        avg_prices = data[['Open','High','Close','Low']].mean(axis=1)
        historical_returns = data['High'] - data['Low']
        return {'avg_prices':avg_prices, 'historical_returns':historical_returns}
        
    def calculate_drift_and_volatility(self, stock_prices):
        returns = stock_prices.pct_change().dropna()
        mean_return = returns.mean()
        variance = returns.var()
        drift = mean_return - (0.5 * variance)
        volatility = returns.std()
        return drift, volatility
