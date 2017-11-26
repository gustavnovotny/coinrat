import datetime, time
import logging
from typing import Union, Tuple, List
from decimal import Decimal

import math

from coinrat.domain import Strategy, CandleStorage, Order, OrderStorage, Signal, Pair, \
    CANDLE_STORAGE_FIELD_CLOSE, SIGNAL_SELL, SIGNAL_BUY, Market, \
    StrategyConfigurationException, NotEnoughBalanceToPerformOrderException

STRATEGY_NAME = 'double_crossover'


class DoubleCrossoverStrategy(Strategy):
    """
    @link http://www.financial-spread-betting.com/course/using-two-moving-averages.html
    """

    def __init__(
        self,
        pair: Pair,
        candle_storage: CandleStorage,
        order_storage: OrderStorage,
        long_average_interval: datetime.timedelta,
        short_average_interval: datetime.timedelta,
        delay: int = 30,
        number_of_runs: Union[int, None] = None
    ) -> None:
        assert short_average_interval < long_average_interval

        self._pair = pair
        self._candle_storage = candle_storage
        self._order_storage = order_storage
        self._long_average_interval = long_average_interval
        self._short_average_interval = short_average_interval
        self._delay = delay
        self._number_of_runs = number_of_runs
        self._previous_sign = None
        self._strategy_ticker = 0

    def run(self, markets: List[Market]) -> None:
        if len(markets) != 1:
            message = 'This strategy works only with one market, {} given.'.format(len(markets))
            raise StrategyConfigurationException(message)

        market = markets[0]

        while self._number_of_runs is None or self._number_of_runs > 0:
            self._check_if_orders_processed()
            self._check_and_trade(market)

            if self._number_of_runs is not None:  # pragma: no cover
                self._number_of_runs -= 1

            self._strategy_ticker += 1
            time.sleep(self._delay)

    def _check_if_orders_processed(self):
        pass  # Todo: implement

    def _check_and_trade(self, market: Market):
        signal = self._check_for_signal(market)
        if signal is not None:
            order = self._react_on_market_by_signal(market, signal)
            if order is not None:
                self._order_storage.save_order(order)

    def _check_for_signal(self, market: Market) -> Union[Signal, None]:
        long_average, short_average = self._get_averages(market)
        current_sign = self._calculate_sign_of_change(long_average, short_average)

        logging.info(
            '[{}] Previous_sign: {}, Current-sign: {}, Long-now: {}, Short-now: {}'.format(
                self._strategy_ticker,
                self._previous_sign,
                current_sign,
                long_average,
                short_average
            )
        )

        if current_sign == 0:  # In equal situation, we are waiting for next price movement to decide
            return None

        signal = None
        if self._previous_sign is not None and current_sign != self._previous_sign:
            signal = self._create_signal(current_sign)

        self._previous_sign = current_sign
        return signal

    @staticmethod
    def _create_signal(current_sign: int) -> Signal:
        assert current_sign in [-1, 1]
        if current_sign == 1:
            return Signal(SIGNAL_BUY)
        return Signal(SIGNAL_SELL)

    @staticmethod
    def _calculate_sign_of_change(long_average: Decimal, short_average: Decimal) -> int:
        diff = short_average - long_average
        if diff == 0:
            return 0

        return int(math.copysign(1, diff))

    def _get_averages(self, market: Market) -> Tuple[Decimal, Decimal]:
        now = datetime.datetime.now().astimezone(datetime.timezone.utc)  # Todo: DateTimeFactory
        long_interval = (now - self._long_average_interval, now)
        long_average = self._candle_storage.mean(
            market.name,
            self._pair,
            CANDLE_STORAGE_FIELD_CLOSE,
            long_interval
        )
        short_interval = (now - self._short_average_interval, now)
        short_average = self._candle_storage.mean(
            market.name,
            self._pair,
            CANDLE_STORAGE_FIELD_CLOSE,
            short_interval
        )

        return long_average, short_average

    def _react_on_market_by_signal(self, market: Market, signal: Signal) -> Union[Order, None]:
        try:
            if signal.is_buy():
                return market.buy_max_available(self._pair)
            elif signal.is_sell():
                return market.sell_max_available(self._pair)
            else:
                raise ValueError('Unknown signal: "{}"'.format(signal))  # pragma: no cover

        except NotEnoughBalanceToPerformOrderException as e:
            # Intentionally, this strategy does not need state of order,
            # just ignores buy/sell and waits for next signal.
            logging.warning(e)
