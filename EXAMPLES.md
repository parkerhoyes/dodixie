# Example Uses of Dodixie

## Instantiation of `PoloniexAPI`

The `PoloniexAPI` object is a wrapper for the Poloniex API and stores
information like your API key and secret (if you're using the trading API) and
data that has been cached (like the trading history for a pair).

A PoloniexAPI object can be created like so:

```
>>> from dodixie.poloniex import *
>>> polo = PoloniexAPI(api_key="your_api_key",
                       secret="your_api_secret",
                       confirm=True,
                       print_calls=True)
```

The `api_key` and `secret` arguments are optional. You only need to specify them
if you plan to use methods that use the Trading API, like
`PoloniexAPI.place_buy_order(...)`.

The arguments `confirm` and `print_calls` are also optional and will default to
`False`. The argument `confirm` takes a boolean which determines whether the API
should ask for your confirmation, via the console, before making any calls to
the Trading API; this option is highly recommended if you're still learning how
to use this library. The `print_calls` argument, if True, will cause the API to
print the arguments to and results of all calls to both the Public and Trading
Poloniex APIs; this is useful for debugging purposes.

## Getting Account Balance

Getting your account balance is simple with the `PoloniexAPI` object. The
`PoloniexAPI.get_balance(...)` method offers many different filters to get your
balance by currency, account (exchange, margin, or lending), or by availability
(on order or not on order).

If a currency is not specified as the first parameter, or if it is `None`, then
this method will return a dictionary containing your balance for all currencies
that have a nonzero balance; otherwise, it will return a single balance for that
currency.

For example:

```
>>> polo.get_balance()
{'ETH': Decimal('99.99999999'), 'BTC': Decimal('42.00000000')}
>>> polo.get_balance('ETH')
Decimal('99.99999999')
>>> polo.get_balance(availability='on_order', account='exchange')
{'ETH': Decimal('50.00000000')}
```

Additional Note: The method `PoloniexAPI.get_valuation(...)` is also quite
useful. It works very similar to `get_balance`, except it estimates the value of
your holdings for each currency in a quote currency of your choosing.

## Placing an Order

Placing orders can be done easily with the `PoloniexAPI.place_buy_order(...)`
and `PoloniexAPI.place_sell_order(...)` methods. Each of these methods takes a
`pair`, `rate`, `amount`, and optional `order_subtype` parameter, in that order.
The `pair` parameter should be a string of the form `'ABC/XYZ'` where `ABC` is
the base currency and `XYZ` is the quote currency. The `rate` and `amount`
parameters may be ints, strings, or `Decimal` objects (**never use `float`s to
store the quantity of a currency**). The `order_subtype` parameter may be either
`'exchange'` or `'margin'` and defaults to `'exchange'`. Each of these methods
will return a `PoloniexAPI.Order` object.

For example, to place a bid to buy 100.0 ETH at a rate of 0.05 BTC (not on
margin), you may use the following:

```
>>> order = polo.place_buy_order('ETH/BTC', "0.05", "100.0")
```

You can get information on the order or cancel it like so:

```
>>> order.describe()
<PoloniexAPI.Order>
    Order Type: buy
    Order Subtype: exchange
    Pair: ETH/BTC
    Rate: 0.05000000 BTC
    Amount: 100.00000000 ETH
    Total: 5.00000000 BTC
    Is Open: Yes
    Amount Outstanding: 100.00000000 ETH
>>> order.cancel()
```

## Getting Your Open Orders

`PoloniexAPI.Order` objects for all of your open orders can be easily retrieved
using the `PoloniexAPI.get_open_orders(...)` method. This method takes an
optional `pair` parameter; if specified, a list of all of your orders for that
pair will be returned, otherwise a dictionary containing all of your orders for
all pairs will be returned.

```
>>> orders = polo.get_open_orders()
>>> orders['ETH/BTC'][0].describe()
<PoloniexAPI.Order>
    Order Type: buy
    Order Subtype: exchange
    Pair: ETH/BTC
    Rate: 0.05000000 BTC
    Amount: 100.00000000 ETH
    Total: 5.00000000 BTC
    Is Open: Yes
    Amount Outstanding: 100.00000000 ETH
```

## Retrieving The Public Trade History

Trades are represented by the `PoloniexAPI.Trade` object. The
`PoloniexAPI.get_public_trade_history(...)` method will return a list of all
trades that occurred within an optional time range for the specified pair. The
`pair` parameter specifies the pair, and the optional `start` and `end`
parameters should be UNIX timestamps (as ints, in seconds). The default for
`start` is 24 hours ago and the default for `end` is the current time. The order
of the trades in the list returned is undefined.

For example, the following code will get a list of all trades of ETH/BTC that
occurred in the last 10 seconds, in chronological order (thanks to the last
line):

```
>>> import time
>>> trades = polo.get_public_trade_history('ETH/BTC', int(time.time()) - 10)
>>> trades.sort(key=lambda trade: trade.get_timestamp())
```

## Retrieve Your Private Trade History

You can also get your personal trade history using the method
`PoloniexAPI.get_trade_history(...)`. This method works almost exacly like
`PoloniexAPI.get_public_trade_history(...)`, except it only returns the trades
that you have made, not the trades that everyone has made.

The following code will get all purchases of Namecoin for Bitcoin you've made
since the beginning of time, and then describe the most recent one (this will
fail if you've made no trades of NMC/BTC):

```
>>> trades = polo.get_trade_history('NMC/BTC', 0)
>>> max(trades, key=lambda trade: trade.get_timestamp()).describe()
<PoloniexAPI.Trade>
    Trade Type: buy
    Pair: NMC/BTC
    Rate: 0.00030140 BTC
    Amount: 1.00250627 NMC
    Total: 0.00030215 BTC
    Fee: 0.00250627 NMC
    Timestamp: 2016-11-20T20:51:16Z
```

# Conclusion

There are a few other useful methods provided by this library, like
`PoloniexAPI.Order.modify(...)`. That method, along with all other methods
provided by this library, are documented extensively in `/dodixie/api.py`.
