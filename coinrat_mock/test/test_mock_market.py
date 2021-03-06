import datetime
from decimal import Decimal
from uuid import UUID

import pytest

from coinrat.domain import CurrentUtcDateTimeFactory
from coinrat.domain.pair import Pair
from coinrat.domain.order import Order, ORDER_TYPE_LIMIT, DIRECTION_BUY, DIRECTION_SELL, \
    NotEnoughBalanceToPerformOrderException
from coinrat_mock.market import MockMarket

BTC_USD_PAIR = Pair('USD', 'BTC')


def test_market():
    market = MockMarket(
        CurrentUtcDateTimeFactory(),
        {
            'mocked_market_name': 'yolo',
            'mocked_base_currency_balance': Decimal('1001'),
            'mocked_base_currency': 'WTF',
            'mocked_transaction_maker_fee': Decimal('0.001'),
            'mocked_transaction_taker_fee': Decimal('0.001'),
        }
    )
    assert 'yolo' == market.name
    assert Decimal('0.004') == market.get_pair_market_info(BTC_USD_PAIR).minimal_order_size
    assert '1001.00000000 WTF' == str(market.get_balance('WTF'))
    assert '0.00000000 LOL' == str(market.get_balance('LOL'))
    assert Decimal('0.001') == market.transaction_taker_fee
    assert Decimal('0.001') == market.transaction_maker_fee
    order = create_order(pair=Pair('WTF', 'BTC'), quantity=Decimal('0.1001'))
    assert order == market.place_order(order)
    assert market.cancel_order('xxx') is None

    assert str(market.get_balances()) == '[0.00000000 WTF, 0.00000000 LOL, 0.09999990 BTC]'


def test_market_processes_orders():
    market = MockMarket(CurrentUtcDateTimeFactory(), {'mocked_market_name': 'yolo_market'})

    assert market.get_balance('USD').available_amount == Decimal('1000')

    with pytest.raises(NotEnoughBalanceToPerformOrderException):
        market.place_order(create_order())

    assert market.get_balance('USD').available_amount == Decimal('1000')

    market.place_order(create_order(quantity=Decimal('0.1')))
    assert market.get_balance('USD').available_amount == Decimal('0')
    assert market.get_balance('BTC').available_amount == Decimal('0.09975')

    with pytest.raises(NotEnoughBalanceToPerformOrderException):
        market.place_order(create_order(direction=DIRECTION_SELL, quantity=Decimal('0.1')))

    market.place_order(create_order(direction=DIRECTION_SELL, quantity=Decimal('0.09975')))
    assert market.get_balance('USD').available_amount == Decimal('995.00625')  # fee applied twice
    assert market.get_balance('BTC').available_amount == Decimal('0')


def test_market_get_order_status():
    market = MockMarket(CurrentUtcDateTimeFactory(), {'mocked_market_name': 'yolo_market'})
    status = market.get_order_status(create_order())
    assert 'Order Id: "16fd2706-8baf-433b-82eb-8c7fada847da", OPEN, Closed at: "", Remaining quantity: "0"' \
           == str(status)


def test_get_tradable_pairs():
    market = MockMarket(CurrentUtcDateTimeFactory(), {'mocked_market_name': 'yolo_market'})
    pairs = market.get_all_tradable_pairs()
    assert len(pairs) > 0


def create_order(
    direction: str = DIRECTION_BUY,
    quantity: Decimal = Decimal('1'),
    rate: Decimal = Decimal('10000'),
    pair: Pair = BTC_USD_PAIR
) -> Order:
    return Order(
        UUID('16fd2706-8baf-433b-82eb-8c7fada847da'),
        UUID('99fd2706-8baf-433b-82eb-8c7fada847da'),
        'dummy_market_name',
        direction,
        datetime.datetime(2017, 11, 26, 10, 11, 12, tzinfo=datetime.timezone.utc),
        pair,
        ORDER_TYPE_LIMIT,
        quantity,
        rate
    )


def test_mock_market_current_price():
    market = MockMarket(CurrentUtcDateTimeFactory(), {'mocked_market_name': 'yolo_market'})
    with pytest.raises(KeyError):
        market.get_current_price(BTC_USD_PAIR)
    market.mock_current_price(BTC_USD_PAIR, Decimal('9854.458'))
    assert market.get_current_price(BTC_USD_PAIR) == Decimal('9854.458')
