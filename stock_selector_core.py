import pandas as pd
import pandas_ta as ta
from collections import deque, namedtuple
import numpy as np
from datetime import datetime

# Import oracles
import bollinger_oracle
import macd_oracle
import rsi_oracle
import trendCalculator

MACDHolder = namedtuple("MACDHolder", ["macd", "signal", "histogram", "is_bullish_crossover", "is_bearish_crossover"])
BollingerHolder = namedtuple("BollingerHolder", ["price", "upper_band", "middle_band", "lower_band", "percent_b", "bandwidth"])

class StockSignalGenerator:
    def __init__(self, strategy_config: dict = None): # Made config optional for easier standalone testing
        if not strategy_config:
            print("Warning: No strategy_config provided to StockSignalGenerator, using default parameters.")
            strategy_config = { # Default structure
                'ema': {}, 'macd': {}, 'bollinger_bands': {}, 'rsi': {}, 'adx': {},
                'atr': {}, 'trend_calculator_smas': {}, 'confidence': {},
                'min_price_at_signal': 0.10
            }

        ema_conf = strategy_config.get('ema', {})
        self.ema_short_period = int(ema_conf.get('short_period', 10))
        self.ema_medium_period = int(ema_conf.get('medium_period', 50))
        self.ema_long_period = int(ema_conf.get('long_period', 200))

        macd_conf = strategy_config.get('macd', {})
        self.macd_fast_period = int(macd_conf.get('fast_period', 12))
        self.macd_slow_period = int(macd_conf.get('slow_period', 26))
        self.macd_signal_period = int(macd_conf.get('signal_period', 9))

        bb_conf = strategy_config.get('bollinger_bands', {})
        self.bollinger_period = int(bb_conf.get('period', 20))
        self.bollinger_k = float(bb_conf.get('std_dev', 2.0))

        rsi_conf = strategy_config.get('rsi', {})
        self.rsi_period = int(rsi_conf.get('period', 14))
        self.rsi_overbought_threshold = float(rsi_conf.get('overbought_threshold', 70))
        self.rsi_oversold_threshold = float(rsi_conf.get('oversold_threshold', 30))
        self.rsi_momentum_threshold = float(rsi_conf.get('momentum_threshold', 50))

        adx_conf = strategy_config.get('adx', {})
        self.adx_period = int(adx_conf.get('period', 14))
        self.adx_trend_threshold = float(adx_conf.get('trend_threshold', 25))

        atr_conf = strategy_config.get('atr', {})
        self.atr_period = int(atr_conf.get('period', 14))
        self.atr_multiplier = float(atr_conf.get('multiplier', 3.0))

        trend_sma_conf = strategy_config.get('trend_calculator_smas', {})
        self.trend_short_window = int(trend_sma_conf.get('short_window', self.ema_short_period))
        self.trend_medium_window = int(trend_sma_conf.get('medium_window', self.ema_medium_period))
        self.trend_long_window = int(trend_sma_conf.get('long_window', self.ema_long_period))

        self.min_data_length = max(
            self.ema_long_period, self.macd_slow_period + self.macd_signal_period,
            self.bollinger_period, self.rsi_period, self.adx_period, self.atr_period
        ) + 15

        self.confidence_params = strategy_config.get('confidence', {})
        self.base_confidence = int(self.confidence_params.get('base_score', 500))

        self.macd_signal_history = {}
        self.bollinger_detail_history = {}
        self.min_price_at_signal = float(strategy_config.get('min_price_at_signal', 0.10))

    def _calculate_indicators(self, symbol: str, data_df: pd.DataFrame):
        if data_df.empty: return data_df
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data_df.columns for col in required_cols): return pd.DataFrame()

        if not isinstance(data_df.index, pd.DatetimeIndex):
            if 'timestamp' in data_df.columns:
                data_df.index = pd.to_datetime(data_df['timestamp'], unit='ms', utc=True)
                if 'timestamp' in data_df.columns: data_df = data_df.drop(columns=['timestamp'])
            else: return pd.DataFrame()

        data_df.ta.ema(length=self.ema_short_period, append=True, col_names=(f'EMA_{self.ema_short_period}'))
        data_df.ta.ema(length=self.ema_medium_period, append=True, col_names=(f'EMA_{self.ema_medium_period}'))
        data_df.ta.ema(length=self.ema_long_period, append=True, col_names=(f'EMA_{self.ema_long_period}'))
        data_df.ta.macd(fast=self.macd_fast_period, slow=self.macd_slow_period, signal=self.macd_signal_period, append=True)
        data_df.ta.bbands(length=self.bollinger_period, std=self.bollinger_k, append=True)
        data_df.ta.rsi(length=self.rsi_period, append=True, col_names=(f'RSI_{self.rsi_period}'))
        data_df.ta.adx(length=self.adx_period, append=True)
        data_df.ta.obv(append=True)
        data_df.ta.atr(length=self.atr_period, append=True, col_names=(f'ATR_{self.atr_period}'))

        ema_col_name = f'EMA_{self.ema_short_period}'
        if ema_col_name in data_df.columns and not data_df[ema_col_name].empty:
            data_df[f'{ema_col_name}_derivative'] = data_df[ema_col_name].diff()
        else: data_df[f'{ema_col_name}_derivative'] = np.nan

        macd_col = f'MACD_{self.macd_fast_period}_{self.macd_slow_period}_{self.macd_signal_period}'
        macd_signal_col = f'MACDs_{self.macd_fast_period}_{self.macd_slow_period}_{self.macd_signal_period}'
        macd_hist_col = f'MACDh_{self.macd_fast_period}_{self.macd_slow_period}_{self.macd_signal_period}'

        if symbol not in self.macd_signal_history: self.macd_signal_history[symbol] = deque(maxlen=10)
        self.macd_signal_history[symbol].clear()
        if all(c in data_df.columns for c in [macd_col, macd_signal_col, macd_hist_col]):
            for i in range(len(data_df)):
                if i < 1: continue
                hist_val = data_df[macd_hist_col].iloc[i]; prev_hist_val = data_df[macd_hist_col].iloc[i-1]
                self.macd_signal_history[symbol].append(MACDHolder(
                    data_df[macd_col].iloc[i], data_df[macd_signal_col].iloc[i], hist_val,
                    hist_val > 0 and prev_hist_val <= 0, hist_val < 0 and prev_hist_val >= 0))

        bbl_col = f'BBL_{self.bollinger_period}_{self.bollinger_k:.1f}'
        bbm_col = f'BBM_{self.bollinger_period}_{self.bollinger_k:.1f}'
        bbu_col = f'BBU_{self.bollinger_period}_{self.bollinger_k:.1f}'
        bbp_col = f'BBP_{self.bollinger_period}_{self.bollinger_k:.1f}'
        bbb_col = f'BBB_{self.bollinger_period}_{self.bollinger_k:.1f}'

        if symbol not in self.bollinger_detail_history: self.bollinger_detail_history[symbol] = deque(maxlen=5)
        self.bollinger_detail_history[symbol].clear()
        if all(c in data_df.columns for c in [bbl_col, bbm_col, bbu_col, bbp_col, bbb_col, 'close']):
            for i in range(len(data_df)):
                self.bollinger_detail_history[symbol].append(BollingerHolder(
                    data_df['close'].iloc[i], data_df[bbu_col].iloc[i], data_df[bbm_col].iloc[i],
                    data_df[bbl_col].iloc[i], data_df[bbp_col].iloc[i], data_df[bbb_col].iloc[i]))
        return data_df

    def atr_trail_stop_loss(self, data_df: pd.DataFrame, is_long: bool):
        atr_col = f'ATR_{self.atr_period}'
        if data_df.empty or atr_col not in data_df.columns or data_df[atr_col].isnull().all(): return None
        current_atr = data_df[atr_col].iloc[-1]
        if pd.isna(current_atr): return None
        price = data_df['close'].iloc[-1]
        if pd.isna(price): return None
        return price - self.atr_multiplier * current_atr if is_long else price + self.atr_multiplier * current_atr

    def generate_signal(self, symbol: str, data_df_input: pd.DataFrame):
        if data_df_input.empty or len(data_df_input) < self.min_data_length: return None
        data_df = data_df_input.copy()
        data_df = self._calculate_indicators(symbol, data_df)
        if data_df.empty: return None

        ema_s_col, ema_m_col, ema_l_col = f'EMA_{self.ema_short_period}', f'EMA_{self.ema_medium_period}', f'EMA_{self.ema_long_period}'
        ema_d_col = f'EMA_{self.ema_short_period}_derivative'
        macd_col = f'MACD_{self.macd_fast_period}_{self.macd_slow_period}_{self.macd_signal_period}'
        macds_col = f'MACDs_{self.macd_fast_period}_{self.macd_slow_period}_{self.macd_signal_period}'
        macdh_col = f'MACDh_{self.macd_fast_period}_{self.macd_slow_period}_{self.macd_signal_period}'
        bbl_col, bbm_col, bbu_col = f'BBL_{self.bollinger_period}_{self.bollinger_k:.1f}', f'BBM_{self.bollinger_period}_{self.bollinger_k:.1f}', f'BBU_{self.bollinger_period}_{self.bollinger_k:.1f}'
        rsi_col, adx_val_col, obv_col = f'RSI_{self.rsi_period}', f'ADX_{self.adx_period}', 'OBV'

        essential_cols = [ema_s_col, ema_m_col, ema_l_col, ema_d_col, macd_col, macds_col, macdh_col, bbl_col, bbm_col, bbu_col, rsi_col, adx_val_col, obv_col]
        if not all(col in data_df.columns for col in essential_cols) or data_df.iloc[-1][essential_cols].isnull().any(): return None

        current_price = data_df['close'].iloc[-1]
        if pd.isna(current_price) or current_price < self.min_price_at_signal: return None

        # Retrieve values by direct column name access
        ema_s_val, ema_m_val, ema_l_val = data_df[ema_s_col].iloc[-1], data_df[ema_m_col].iloc[-1], data_df[ema_l_col].iloc[-1]
        ema_d_val = data_df[ema_d_col].iloc[-1]
        macd_val, macds_val, macdh_val = data_df[macd_col].iloc[-1], data_df[macds_col].iloc[-1], data_df[macdh_col].iloc[-1]
        bbl_val, bbm_val, bbu_val = data_df[bbl_col].iloc[-1], data_df[bbm_col].iloc[-1], data_df[bbu_col].iloc[-1]
        rsi_val, adx_val = data_df[rsi_col].iloc[-1], data_df[adx_val_col].iloc[-1]
        obv_series = data_df[obv_col]

        signal_type = "HOLD"; reason_parts = []; confidence_score = self.base_confidence
        conf_adj = self.confidence_params.get

        oracle_bb_signal = bollinger_oracle.get_bollinger_band_signal(current_price, bbu_val, bbl_val, bbm_val, self.bollinger_detail_history.get(symbol))
        macd_hist_deque = deque([h.histogram for h in self.macd_signal_history.get(symbol, []) if h.histogram is not None], maxlen=5)
        oracle_macd_signal = macd_oracle.get_macd_signal(macd_val, macds_val, macdh_val, macd_hist_deque)
        oracle_rsi_signal = rsi_oracle.get_rsi_signal(rsi_val, self.rsi_oversold_threshold, self.rsi_overbought_threshold)

        price_trend = trendCalculator.get_trend(data_df['close'], self.trend_short_window, self.trend_medium_window, self.trend_long_window)
        rsi_trend = trendCalculator.get_trend(data_df[rsi_col].dropna(), self.trend_short_window, self.trend_medium_window, self.trend_long_window) if len(data_df[rsi_col].dropna()) >= self.trend_long_window else "SIDEWAYS/UNCERTAIN"
        obv_trend = trendCalculator.get_trend(obv_series.dropna(), self.trend_short_window, self.trend_medium_window, self.trend_long_window) if len(obv_series.dropna()) >= self.trend_long_window else "SIDEWAYS/UNCERTAIN"

        if ema_s_val > ema_m_val and ema_m_val > ema_l_val and (pd.isna(ema_d_val) or ema_d_val > 0): reason_parts.append("Strong EMA Up"); confidence_score += conf_adj('ema_trend_strong_add', 150)
        elif ema_s_val < ema_m_val and ema_m_val < ema_l_val and (pd.isna(ema_d_val) or ema_d_val < 0): reason_parts.append("Strong EMA Down"); confidence_score += conf_adj('ema_trend_strong_add', 150) # Magnitude
        elif ema_m_val > ema_l_val: reason_parts.append("EMA Bull Bias"); confidence_score += conf_adj('ema_trend_bias_add', 75)
        elif ema_m_val < ema_l_val: reason_parts.append("EMA Bear Bias"); confidence_score += conf_adj('ema_trend_bias_add', 75)

        if adx_val > self.adx_trend_threshold: reason_parts.append(f"ADX Trend ({adx_val:.0f})"); confidence_score += conf_adj('adx_strong_add', 50)
        else: reason_parts.append(f"ADX No Trend ({adx_val:.0f})"); confidence_score += conf_adj('adx_weak_add', -25)

        if oracle_macd_signal == "BUY": reason_parts.append("MACD Cross Up"); confidence_score += conf_adj('macd_cross_add', 100)
        if oracle_macd_signal == "SELL": reason_parts.append("MACD Cross Down"); confidence_score += conf_adj('macd_cross_add', 100)

        if oracle_rsi_signal == "BUY": reason_parts.append("RSI Oversold"); confidence_score += conf_adj('rsi_extremes_add', 75)
        if oracle_rsi_signal == "SELL": reason_parts.append("RSI Overbought"); confidence_score += conf_adj('rsi_extremes_add', 75)
        elif rsi_val > self.rsi_momentum_threshold: reason_parts.append(f"RSI Bull Mom ({rsi_val:.0f})"); confidence_score += conf_adj('rsi_momentum_add', 25)
        elif rsi_val < self.rsi_momentum_threshold: reason_parts.append(f"RSI Bear Mom ({rsi_val:.0f})"); confidence_score += conf_adj('rsi_momentum_add', 25)

        if price_trend == "UPTREND": reason_parts.append("Price Trend Up"); confidence_score += conf_adj('price_trend_sma_add', 50)
        if price_trend == "DOWNTREND": reason_parts.append("Price Trend Down"); confidence_score += conf_adj('price_trend_sma_add', 50)
        if obv_trend == "UPTREND": reason_parts.append("OBV Trend Up"); confidence_score += conf_adj('obv_trend_add', 50)
        if obv_trend == "DOWNTREND": reason_parts.append("OBV Trend Down"); confidence_score += conf_adj('obv_trend_add', 50)
        if oracle_bb_signal == "BUY": reason_parts.append("BB Buy"); confidence_score += conf_adj('bb_signal_add', 50)
        if oracle_bb_signal == "SELL": reason_parts.append("BB Sell"); confidence_score += conf_adj('bb_signal_add', 50)

        is_bullish_ema = ema_s_val > ema_m_val and ema_m_val > ema_l_val
        is_bearish_ema = ema_s_val < ema_m_val and ema_m_val < ema_l_val
        buy_thresh = self.confidence_params.get('buy_threshold', 700)
        sell_thresh = self.confidence_params.get('sell_threshold', 700) # Sell if bearish confidence is high

        if is_bullish_ema and oracle_macd_signal == "BUY" and rsi_val > (self.rsi_momentum_threshold -10) and adx_val > (self.adx_trend_threshold -5) and confidence_score >= buy_thresh : signal_type = "BUY"
        elif is_bearish_ema and oracle_macd_signal == "SELL" and rsi_val < (self.rsi_momentum_threshold +10) and adx_val > (self.adx_trend_threshold -5) and confidence_score >= sell_thresh : signal_type = "SELL"

        confidence_score = max(100, min(999, int(confidence_score)))

        if signal_type != "HOLD":
            atr_stop = self.atr_trail_stop_loss(data_df, signal_type == "BUY")
            if atr_stop: reason_parts.append(f"ATR Stop: {atr_stop:.2f}")

            ts_str = data_df.index[-1].strftime("%Y-%m-%d %H:%M:%S")
            ind_summary = {
                "EMA":f"{ema_s_val:.1f},{ema_m_val:.1f},{ema_l_val:.1f}", "EMA_D":f"{ema_d_val:.2f}" if pd.notna(ema_d_val) else "N/A",
                "MACD":f"{macd_val:.2f}(H:{macdh_val:.2f},S:{macds_val:.2f})", "BB":f"L:{bbl_val:.1f} M:{bbm_val:.1f} U:{bbu_val:.1f}",
                "RSI":f"{rsi_val:.1f}", "ADX":f"{adx_val:.1f}", "OBV":f"{obv_series.iloc[-1]:.0f} (Trend:{obv_trend})",
                "PriceTrend":price_trend, "RSITrend":rsi_trend
            }
            return {"symbol":symbol, "timestamp":ts_str, "signal_type":signal_type, "price_at_signal":current_price,
                    "confidence_score":confidence_score, "reason":"; ".join(reason_parts), "indicator_values":ind_summary}
        return None

if __name__ == '__main__':
    dummy_conf = {
        'ema': {'short_period':10,'medium_period':20,'long_period':50}, # Shorter for dummy
        'macd': {'fast_period':12,'slow_period':26,'signal_period':9},
        'bollinger_bands': {'period':20,'std_dev':2.0},
        'rsi': {'period':14,'overbought_threshold':70,'oversold_threshold':30,'momentum_threshold':50},
        'adx': {'period':14,'trend_threshold':20}, # Lowered ADX threshold for more signals
        'atr': {'period':14,'multiplier':3.0},
        'trend_calculator_smas': {'short_window':10,'medium_window':20,'long_window':50},
        'confidence': {'base_score':500, 'buy_threshold': 650, 'sell_threshold': 650}, # Lowered conf threshold
        'min_price_at_signal': 0.01
    }
    generator = StockSignalGenerator(strategy_config=dummy_conf)

    data_len = max(generator.min_data_length, 60) # Ensure enough data
    data = {'open':np.random.uniform(90,110,data_len),'high':np.random.uniform(100,120,data_len),
            'low':np.random.uniform(80,100,data_len),'close':np.random.uniform(90,110,data_len),
            'volume':np.random.uniform(100000,500000,data_len)}
    data['high'] = np.maximum.reduce([data['open'],data['high'],data['low'],data['close']])
    data['low'] = np.minimum.reduce([data['open'],data['high'],data['low'],data['close']])

    idx = pd.to_datetime([datetime(2023,1,1)+pd.Timedelta(days=i) for i in range(data_len)])
    dummy_df = pd.DataFrame(data, index=idx)

    print(f"Testing with dummy data for 'TEST', len: {len(dummy_df)}")
    signal = generator.generate_signal("TEST", dummy_df.copy())
    if signal:
        import json; print("Signal (config & pandas-ta):\n", json.dumps(signal,indent=4))
    else: print("No signal for TEST (config & pandas-ta).")

```
