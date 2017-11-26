import pytest
from flexmock import flexmock

from coinrat_bittrex import synchronizer_plugin, market_plugin
from coinrat_bittrex.synchronizer import BittrexSynchronizer
from coinrat_bittrex.market import BittrexMarket


def test_synchronizer_plugin():
    storage = flexmock()

    assert 'coinrat_bittrex' == synchronizer_plugin.get_name()
    assert ['bittrex'] == synchronizer_plugin.get_available_synchronizers()
    assert isinstance(synchronizer_plugin.get_synchronizer('bittrex', storage), BittrexSynchronizer)
    with pytest.raises(ValueError):
        synchronizer_plugin.get_synchronizer('gandalf', storage)


def test_market_plugin():
    assert 'coinrat_bittrex' == market_plugin.get_name()
    assert ['bittrex'] == market_plugin.get_available_markets()
    assert isinstance(market_plugin.get_market('bittrex'), BittrexMarket)
    with pytest.raises(ValueError):
        market_plugin.get_market('gandalf')