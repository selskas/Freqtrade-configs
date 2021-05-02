# --- Do not remove these libs ---
from datetime import datetime
from datetime import timedelta

import talib.abstract as ta
from pandas import DataFrame

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter
from freqtrade.strategy import IntParameter
from freqtrade.strategy.interface import IStrategy


# --------------------------------


class SMAOffset(IStrategy):
    # ROI table:
    minimal_roi = {
        "0": 1
    }

    # Stoploss:
    stoploss = -0.25

    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    # Optimal timeframe for the strategy
    timeframe = '5m'

    use_sell_signal = True
    sell_profit_only = False

    process_only_new_candles = True

    plot_config = {
        'main_plot': {
            'sma_30_offset': {'color': 'orange'},
            'sma_30_offset_pos': {'color': 'orange'},
        },
    }

    use_custom_stoploss = False

    low_offset = DecimalParameter(0.80, 1.20, default=0.958, space='buy', optimize=True, load=True)
    high_offset = DecimalParameter(0.80, 1.20, default=1.012, space='sell', optimize=True, load=True)
    sma_len_buy = IntParameter(5, 50, default=30, space='buy', optimize=True, load=True)
    sma_len_sell = IntParameter(5, 50, default=30, space='sell', optimize=True, load=True)

    startup_candle_count = max(sma_len_buy.value, sma_len_sell.value)

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        # Make sure you have the longest interval first - these conditions are evaluated from top to bottom.
        if current_time - timedelta(minutes=1200) > trade.open_date_utc and current_profit < -0.05:
            return -0.001

        # return maximum stoploss value, keeping current stoploss price unchanged
        return 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # required for graphing
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        if self.config['runmode'].value == 'hyperopt':
            for len in range(5, 51):
                dataframe[f'sma_{len}'] = ta.SMA(dataframe, timeperiod=len)
        else:
            dataframe[f'sma_{self.sma_len_buy.value}'] = ta.SMA(dataframe, timeperiod=self.sma_len_buy.value)
            dataframe[f'sma_{self.sma_len_sell.value}'] = ta.SMA(dataframe, timeperiod=self.sma_len_sell.value)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sma = f'sma_{self.sma_len_buy.value}'
        dataframe.loc[
            (
                    (dataframe['close'] < (dataframe[sma] * self.low_offset.value)) &
                    (dataframe['volume'] > 0)
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sma = f'sma_{self.sma_len_sell.value}'
        dataframe.loc[
            (
                    (dataframe['close'] > (dataframe[sma] * self.high_offset.value)) &
                    (dataframe['volume'] > 0)
            ),
            'sell'] = 1
        return dataframe