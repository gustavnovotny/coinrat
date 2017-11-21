from decimal import Decimal

import datetime
from typing import Union, List

ORDER_TYPE_LIMIT = 'limit'
ORDER_TYPE_MARKET = 'market'


class Balance:
    def __init__(self, currency: str, available_amount: Decimal) -> None:
        assert isinstance(available_amount, Decimal)

        self._currency = currency
        self._available_amount = available_amount

    @property
    def currency(self):
        return self._currency

    @property
    def available_amount(self) -> Decimal:
        return self._available_amount

    def __repr__(self):
        return '{0:.8f} {1}'.format(self._available_amount, self._currency)


class MinuteCandle:
    def __init__(
        self,
        time: datetime.datetime,
        open_price: Decimal,
        close_price: Decimal,
        low_price: Decimal,
        high_price: Decimal
    ) -> None:
        assert isinstance(open_price, Decimal)
        assert isinstance(close_price, Decimal)
        assert isinstance(low_price, Decimal)
        assert isinstance(high_price, Decimal)

        assert time.second == 0
        assert time.microsecond == 0

        self._time = time
        self._open = open_price
        self._close = close_price
        self._low = low_price
        self._high = high_price

    @property
    def time(self) -> datetime.datetime:
        return self._time

    @property
    def open(self) -> Decimal:
        return self._open

    @property
    def close(self) -> Decimal:
        return self._close

    @property
    def low(self) -> Decimal:
        return self._low

    @property
    def high(self) -> Decimal:
        return self._high

    @property
    def average_price(self) -> Decimal:
        return (self._low + self._high) / 2

    def __repr__(self):
        return '{0} O:{1:.8f} C:{2:.8f} L:{3:.8f} H:{2:.8f}' \
            .format(self._time.isoformat(), self._open, self._close, self._low, self._high)


class MarketPair:
    def __init__(self, left: str, right: str) -> None:
        self._left = left
        self._right = right

    @property
    def left(self) -> str:
        return self._left

    @property
    def right(self) -> str:
        return self._right

    def __repr__(self):
        return '{}-{}'.format(self._left, self._right)


class Order:
    def __init__(self, pair: MarketPair, order_type: str, quantity: Decimal, rate: Union[Decimal, None] = None) -> None:
        assert order_type in [ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET]
        assert isinstance(quantity, Decimal)

        if order_type == ORDER_TYPE_LIMIT:
            assert isinstance(rate, Decimal)
        if order_type == ORDER_TYPE_MARKET:
            assert rate is None

        self._pair = pair
        self._type = order_type
        self._quantity = quantity
        self._rate = rate

    @property
    def pair(self) -> MarketPair:
        return self._pair

    @property
    def type(self) -> str:
        return self._type

    @property
    def rate(self) -> Union[Decimal, None]:
        return self._rate

    @property
    def quantity(self) -> Decimal:
        return self._quantity


class MarketStorage:
    def write_candle(self, market: str, candle: MinuteCandle) -> None:
        pass

    def write_candles(self, market: str, candles: List[MinuteCandle]) -> None:
        pass


class Market:
    def transaction_fee_coefficient(self):
        pass

    def get_balance(self, currency: str) -> Decimal:
        pass

    def create_sell_order(self, order: Order) -> str:
        pass

    def create_buy_order(self, order: Order) -> str:
        pass

    def cancel_order(self, order_id: str) -> None:
        pass

    def buy_max_available(self, pair: MarketPair) -> str:
        pass

    def sell_max_available(self, pair: MarketPair) -> str:
        pass


class MarketStateSynchronizer:
    def synchronize(self, pair: MarketPair) -> None:
        pass