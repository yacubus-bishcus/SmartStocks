import numpy as np
import pandas as pd

class Simulation_Analysis:
    def __init__(self, **kwargs):
        pass 

    def __del__(self):
        pass

    def _compute_volatility_features(self, prices, window=20):
        if isinstance(prices, pd.Series):
            price_series = prices
        else:
            price_array = np.asarray(prices)
            price_array = price_array.squeeze()
            if price_array.ndim != 1:
                price_array = price_array.reshape(-1)
            price_series = pd.Series(price_array)
        log_returns = np.log(price_series).diff().dropna()
        realized_vol = log_returns.rolling(window=window, min_periods=1).std()
        realized_vol = realized_vol.reindex(price_series.index)
        realized_vol = realized_vol.fillna(method='bfill').fillna(method='ffill')
        if realized_vol.isna().all():
            realized_vol = pd.Series(np.zeros(len(price_series)), index=price_series.index)
        threshold = realized_vol.median()
        volatility_regime = (realized_vol > threshold).astype(int)
        return realized_vol, volatility_regime

    def stock_price_processing_close_open(self, data):
        avg_prices = data[['Open', 'High', 'Close', 'Low']].mean(axis=1)
        historical_returns = data['Close'] - data['Open'] # some thought to making this high and low to have more variation
        rolling_volatility, volatility_regime = self._compute_volatility_features(data['Close'])
        return {
            'avg_prices': avg_prices,
            'historical_returns': historical_returns,
            'rolling_volatility': rolling_volatility,
            'volatility_regime': volatility_regime,
        }

    def stock_price_processing_high_low(self, data):
        avg_prices = data[['Open','High','Close','Low']].mean(axis=1)
        historical_returns = data['High'] - data['Low']
        rolling_volatility, volatility_regime = self._compute_volatility_features(data['Close'])
        return {
            'avg_prices': avg_prices,
            'historical_returns': historical_returns,
            'rolling_volatility': rolling_volatility,
            'volatility_regime': volatility_regime,
        }

    def calculate_drift_and_volatility(self, stock_prices, use_log_returns):
        if use_log_returns:
            returns = stock_prices.pct_change().dropna()
        else:
            returns = stock_prices.diff().dropna()

        mean_return = returns.mean()
        variance = returns.var()
        drift = mean_return - (0.5 * variance)
        volatility = returns.std()
        return drift, volatility      
    
    @staticmethod
    def detect_head_and_shoulders(prices, window_size=20):
        patterns = np.zeros(len(prices))
        reductions = []
        
        for i in range(window_size, len(prices) - window_size):
            window = prices[i-window_size:i+window_size]
            left_shoulder = window[:window_size//2]
            head = window[window_size//2:window_size]
            right_shoulder = window[window_size:]
            
            if (np.max(left_shoulder) < np.max(head) and 
                np.max(right_shoulder) < np.max(head) and
                np.max(left_shoulder) > np.min(head) and 
                np.max(right_shoulder) > np.min(head)):
                patterns[i] = 1
                reduction = (prices[i] - np.min(prices[i:])) / prices[i]
                reductions.append(reduction)
        
        return patterns, reductions


    def calculate_average_reduction(self, prices, window_size=20):
        _, reductions = Simulation_Analysis.detect_head_and_shoulders(prices, window_size)
        if reductions:
            return np.mean(reductions)
        else:
            return 0.05  # Default value if no patterns are found
