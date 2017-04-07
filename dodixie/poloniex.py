# License for the Dodixie project, originally found here:
# https://github.com/parkerhoyes/dodixie
#
# Copyright (C) 2017 Parker Hoyes <contact@parkerhoyes.com>
#
# This software is provided "as-is", without any express or implied warranty. In
# no event will the authors be held liable for any damages arising from the use of
# this software.
#
# Permission is granted to anyone to use this software for any purpose, including
# commercial applications, and to alter it and redistribute it freely, subject to
# the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not claim
#    that you wrote the original software. If you use this software in a product,
#    an acknowledgment in the product documentation would be appreciated but is
#    not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import calendar
from decimal import Decimal
import hashlib
import hmac
import json
import re
import time
import urllib.parse
import urllib.request

from . import api
from .utils import *

__all__ = [
    'OrderNotFoundError',
    'PoloniexAPI'
]

# The minimum time delay, in seconds, between requests to the Poloniex API
_REQUEST_DELAY = 0.25

_PAIR_REGEXP = re.compile(r"^[A-Z]+/[A-Z]+$")
_CURRENCY_REGEXP = re.compile(r"^[A-Z]+$")
_POLONIEX_ULP = Decimal("0.00000001")

def _round_ceil_ulp(n):
    if n % _POLONIEX_ULP == 0:
        return Decimal(int(n / _POLONIEX_ULP)) * _POLONIEX_ULP
    return Decimal(int((n - n % _POLONIEX_ULP) / _POLONIEX_ULP) + 1) * _POLONIEX_ULP

def _encode_pair(pair):
    base, quote = pair.split('/')
    return quote + '_' + base

def _decode_pair(pair):
    quote, base = pair.split('_')
    return base + '/' + quote

def _decode_timestamp(timestamp):
    return calendar.timegm(time.strptime(timestamp, '%Y-%m-%d %H:%M:%S'))

class OrderNotFoundError(api.ExchangeAPIError):
    pass

class PoloniexAPI(api.ExchangeAPI):
    class Trade(api.ExchangeAPI.Trade):
        def __init__(self, api, global_trade_id):
            self._api = api
            self._global_trade_id = global_trade_id
        # Definitions of abstract methods
        @property
        def api(self):
            return self._api
        def get_trade_type_or_none(self):
            if 'trade_type' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['trade_type']
            return None
        def get_pair_or_none(self):
            if 'pair' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['pair']
            return None
        def get_rate_or_none(self):
            if 'rate' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['rate']
            return None
        def get_amount_or_none(self):
            if 'amount' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['amount']
            return None
        def get_total_or_none(self):
            if 'total' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['total']
            return None
        def get_fee_or_none(self):
            # TODO It appears as though Poloniex lists the fee in the base currency when buying and the quote currency
            # when selling. This should be accounted for.
            if 'fee' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['fee']
            return None
        def get_timestamp_or_none(self):
            if 'timestamp' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['timestamp']
            return None
        # Subclass specific methods
        def __hash__(self):
            return hash(self._global_trade_id)
        @property
        def global_trade_id(self):
            return self._global_trade_id
        def get_trade_id(self):
            trade_id = self.get_trade_id_or_none()
            if trade_id is None:
                raise api.InsufficientInformationError("Trade ID is unknown")
            return trade_id
        def get_trade_id_or_none(self):
            if 'trade_id' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['trade_id']
            return None
        def get_order(self):
            order = self.get_order_or_none()
            if order is None:
                raise api.InsufficientInformationError("Order handle is unavailable")
            return order
        def get_order_or_none(self):
            if 'order' in self._api._persistent_cache['trades'][self._global_trade_id]:
                return self._api._persistent_cache['trades'][self._global_trade_id]['order']
            return None
    class Order(api.ExchangeAPI.Order):
        def __init__(self, api, order_number):
            self._api = api
            self._order_number = order_number
        # Definitions of abstract methods
        @property
        def api(self):
            return self._api
        def get_order_type_or_none(self):
            if 'order_type' in self._api._persistent_cache['orders'][self._order_number]:
                return self._api._persistent_cache['orders'][self._order_number]['order_type']
            return None
        def get_order_subtype_or_none(self):
            if 'order_subtype' in self._api._persistent_cache['orders'][self._order_number]:
                return self._api._persistent_cache['orders'][self.order_number]['order_subtype']
            return None
        def get_pair_or_none(self):
            if 'pair' in self._api._persistent_cache['orders'][self._order_number]:
                return self._api._persistent_cache['orders'][self.order_number]['pair']
            return None
        def get_rate_or_none(self):
            if 'rate' in self._api._persistent_cache['orders'][self._order_number]:
                return self._api._persistent_cache['orders'][self.order_number]['rate']
            return None
        def get_amount_or_none(self):
            if 'amount' in self._api._persistent_cache['orders'][self._order_number]:
                return self._api._persistent_cache['orders'][self.order_number]['amount']
            return None
        def get_total_or_none(self):
            if 'total' in self._api._persistent_cache['orders'][self._order_number]:
                return self._api._persistent_cache['orders'][self.order_number]['total']
            return None
        def is_open_or_none(self):
            if self._api._live_cache is not None and 'open_orders' in self._api._live_cache:
                for open_orders in self._api._live_cache['open_orders'].values():
                    if self in open_orders:
                        return True
                return False
            pair = self.get_pair_or_none()
            if pair is not None:
                return self in self._api.get_open_orders(pair=pair)
            else:
                for open_orders in self._api.get_open_orders().values():
                    if self in open_orders:
                        return True
                return False
        # Subclass specific methods
        def __hash__(self):
            return hash(self._order_number)
        @property
        def order_number(self):
            return self._order_number
    def __init__(self, api_key=None, secret=None, min_nonce=None, confirm=False, print_calls=False):
        """Create a new wrapper for the PoloniexAPI which optionally stores the credentials for a member.

        By default, the live cache is disabled.

        Args:
            api_key: the member's API key as a string or None
            secret: the member's secret as a string, bytes object, or None
            min_nonce: the minimum nonce to provide when calling the trading API
            confirm: True if the user should be asked for confirmation via the console for every trading API call, or
                     False otherwise
            print_calls: True if all API calls and their results should be printed to console, False otherwise
        """
        if api_key is not None and not isinstance(api_key, str):
            raise TypeError("api_key must be None or of type str")
        self.api_key = api_key
        if secret is not None and not isinstance(secret, (str, bytes)):
            raise TypeError("secret must be None or of type str or bytes")
        self.secret = secret.encode() if isinstance(secret, str) else secret
        if min_nonce is not None and not isinstance(min_nonce, int):
            raise ValueError("min_nonce must be None or of type int")
        if min_nonce is None:
            min_nonce = int(time.time())
        self.confirm = confirm
        self.print_calls = print_calls
        self._min_nonce = min_nonce
        self._last_request = time.time()
        # The persistent cache caches data that doesn't change over time (eg. trade or order history).
        self._persistent_cache = {'trades': {}, 'orders': {}, 'public_trade_history': {}, 'trade_history': {}}
        # The live cache caches data that may change over time (eg. tickers). Set to None if disabled.
        self._live_cache = None
        # The pool used to intern trade handles (globalTradeID: PoloniexAPI.Trade)
        self._trade_pool = {}
        # The pool used to intern order handles (orderNumber: PoloniexAPI.Trade)
        self._order_pool = {}
    def _request(self, request):
        while True:
            now = time.time()
            if self._last_request + _REQUEST_DELAY <= now:
                break
            delay = self._last_request + _REQUEST_DELAY - now
            if delay > 0:
                time.sleep(delay)
        response = urllib.request.urlopen(request)
        self._last_request = time.time()
        return json.loads(response.read().decode())
    def _get_trade(self, global_trade_id, trade_type, pair, rate, amount, total, fee, timestamp, trade_id, order):
        if global_trade_id in self._trade_pool:
            trade = self._trade_pool[global_trade_id]
        else:
            trade = PoloniexAPI.Trade(self, global_trade_id)
            self._trade_pool[global_trade_id] = trade
            self._persistent_cache['trades'][global_trade_id] = {}
        if trade_type is not None:
            self._persistent_cache['trades'][global_trade_id]['trade_type'] = trade_type
        if pair is not None:
            self._persistent_cache['trades'][global_trade_id]['pair'] = pair
        if rate is not None:
            self._persistent_cache['trades'][global_trade_id]['rate'] = rate
        if amount is not None:
            self._persistent_cache['trades'][global_trade_id]['amount'] = amount
        if total is not None:
            self._persistent_cache['trades'][global_trade_id]['total'] = total
        if fee is not None:
            self._persistent_cache['trades'][global_trade_id]['fee'] = fee
        if timestamp is not None:
            self._persistent_cache['trades'][global_trade_id]['timestamp'] = timestamp
        if trade_id is not None:
            self._persistent_cache['trades'][global_trade_id]['trade_id'] = trade_id
        if order is not None:
            self._persistent_cache['trades'][global_trade_id]['order'] = order
        return trade
    def _parse_then_get_trade(self, pair, raw_trade, order):
        amount = Decimal(str(raw_trade['amount']))
        return self._get_trade(int(raw_trade['globalTradeID']),
                trade_type=raw_trade['type'],
                pair=pair,
                rate=Decimal(str(raw_trade['rate'])),
                amount=amount,
                total=Decimal(str(raw_trade['total'])),
                fee=_round_ceil_ulp(amount * Decimal(str(raw_trade['fee']))) if 'fee' in raw_trade else None,
                timestamp=_decode_timestamp(raw_trade['date']),
                trade_id=int(raw_trade['tradeID']),
                order=order)
    def _get_order(self, order_number, order_type=None, order_subtype=None, pair=None, rate=None, amount=None,
            total=None):
        if order_number in self._order_pool:
            order = self._order_pool[order_number]
        else:
            order = PoloniexAPI.Order(self, order_number)
            self._order_pool[order_number] = order
            self._persistent_cache['orders'][order_number] = {}
        if order_type is not None:
            self._persistent_cache['orders'][order_number]['order_type'] = order_type
        if order_subtype is not None:
            self._persistent_cache['orders'][order_number]['order_subtype'] = order_subtype
        if pair is not None:
            self._persistent_cache['orders'][order_number]['pair'] = pair
        if rate is not None:
            self._persistent_cache['orders'][order_number]['rate'] = rate
        if amount is not None:
            self._persistent_cache['orders'][order_number]['amount'] = amount
        if total is not None:
            self._persistent_cache['orders'][order_number]['total'] = total
        return order
    def query_public_api(self, command, args={}):
        if not isinstance(command, str):
            raise TypeError("command must be of type str")
        if not isinstance(args, dict):
            raise TypeError("args must be of type dict")
        args_list = [('command', command)]
        for key in sorted(args.keys()):
            args_list.append((key, args[key]))
        args_encoded = urllib.parse.urlencode(args_list)
        del args_list
        if self.print_calls:
            log('API', "Calling https://poloniex.com/public with " + args_encoded + "\n")
        response = self._request(urllib.request.Request('https://poloniex.com/public?' + args_encoded))
        if self.print_calls:
            log('API', "Response: " + json.dumps(response) + "\n")
        if 'error' in response:
            if response['error'] in ["Invalid currency pair.", "Invalid currencyPair parameter."]:
                raise api.NonexistentPairError("Nonexistent currency pair")
            raise api.ExchangeAPIError("Command '" + command + "' of the public API resulted in an error" + ': ' +
                    response['error'])
        if 'success' in response and response['success'] != 1:
            raise api.ExchangeAPIError("Command '" + command + "' of the public API resulted in success != 1" + (': ' +
                    response['message'] if 'message' in response else ''))
        return response
    def query_trading_api(self, command, args={}):
        if not isinstance(command, str):
            raise TypeError("command must be of type str")
        if not isinstance(args, dict):
            raise TypeError("args must be of type dict")
        args_list = [('command', command), ('nonce', self._min_nonce)]
        for key in sorted(args.keys()):
            args_list.append((key, args[key]))
        post_data = urllib.parse.urlencode(args_list).encode()
        del args_list
        sign = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
        headers = {'Sign': sign, 'Key': self.api_key}
        if self.confirm:
            log('API', "Attempting to perform Poloniex Trading API request with the following arguments:\n")
            log('API', post_data.decode() + "\n")
            if not user_confirm('API', "Would you like to perform this API request?"):
                log('API', "API request cancelled.\n")
                raise RuntimeError("API request cancelled by user")
            if self.print_calls:
                log('API', "Calling https://poloniex.com/tradingApi\n")
        else:
            if self.print_calls:
                log('API', "Calling https://poloniex.com/tradingApi with " + post_data.decode() + "\n")
        self._min_nonce += 1
        response = self._request(urllib.request.Request('https://poloniex.com/tradingApi', post_data, headers))
        if self.print_calls:
            log('API', "Response: " + json.dumps(response) + "\n")
        if 'error' in response:
            if response['error'] in ["Invalid currency pair.", "Invalid currencyPair parameter."]:
                raise api.NonexistentPairError("Nonexistent currency pair")
            if response['error'] == "Order not found, or you are not the person who placed it.":
                raise OrderNotFoundError("Order not found, or you are not the person who placed it.")
            raise api.ExchangeAPIError("Command '" + command + "' of the trading API resulted in an error" + ': ' +
                    response['error'])
        if 'success' in response and response['success'] != 1:
            raise api.ExchangeAPIError("Command '" + command + "' of the trading API resulted in success != 1" + (': ' +
                    response['message'] if 'message' in response else ''))
        return response
    def enable_live_cache(self):
        if self._live_cache is None:
            self._live_cache = {'orders': {}, 'balance': {}, 'detailed_balance': {}, 'order_trades': {}}
    def disable_live_cache(self):
        self._live_cache = None
    def clear_live_cache(self):
        self.disable_live_cache()
        self.enable_live_cache()
    def is_live_cache_enabled(self):
        return self._live_cache is not None
    def get_currencies(self):
        if 'currencies' not in self._persistent_cache:
            self._persistent_cache['currencies'] = self._get_currencies()
        return self._persistent_cache['currencies']
    def _get_currencies(self):
        response = self.query_public_api('returnCurrencies')
        return list(response.keys())
    def get_pair_info(self, pair=None):
        if pair is not None:
            if not isinstance(pair, str):
                raise TypeError("pair must be None or of type str")
            if _PAIR_REGEXP.match(pair) is None:
                raise ValueError("Malformed pair")
        if self._live_cache is None:
            return self._get_pair_info(pair)
        if 'pair_info' not in self._live_cache:
            self._live_cache['pair_info'] = self._get_pair_info(None)
        if pair is None:
            return self._live_cache['pair_info']
        if pair in self._live_cache['pair_info']:
            return self._live_cache['pair_info'][pair]
        else:
            raise NonexistentPairError("Nonexistent currency pair '" + pair + "'")
    def _get_pair_info(self, pair=None):
        raw_ticker = self.query_public_api('returnTicker')
        pair_info = {}
        for p in raw_ticker:
            pair_info[_decode_pair(p)] = api.PairInfo(base_ulp=_POLONIEX_ULP,
                    quote_ulp=_POLONIEX_ULP,
                    base_volume=Decimal(str(raw_ticker[p]['baseVolume'])),
                    quote_volume=Decimal(str(raw_ticker[p]['quoteVolume'])),
                    percent_change=Decimal(str(raw_ticker[p]['percentChange'])))
        if pair is None:
            return pair_info
        if pair in pair_info:
            return pair_info[pair]
        else:
            raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'")
    def get_ticker(self, pair=None):
        if pair is not None:
            if not isinstance(pair, str):
                raise TypeError("pair must be None or of type str")
            if _PAIR_REGEXP.match(pair) is None:
                raise ValueError("Malformed pair")
        if self._live_cache is None:
            return self._get_ticker(pair)
        if 'ticker' not in self._live_cache:
            self._live_cache['ticker'] = self._get_ticker(None)
        if pair is None:
            return self._live_cache['ticker']
        if pair in self._live_cache['ticker']:
            return self._live_cache['ticker'][pair]
        else:
            raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'")
    def _get_ticker(self, pair=None):
        raw_ticker = self.query_public_api('returnTicker')
        ticker = {}
        for p in raw_ticker:
            ticker[_decode_pair(p)] = api.Ticker(highest_bid=Decimal(str(raw_ticker[p]['highestBid'])),
                    lowest_ask=Decimal(str(raw_ticker[p]['lowestAsk'])),
                    last=Decimal(str(raw_ticker[p]['last'])))
        if pair is None:
            return ticker
        if pair in ticker:
            return ticker[pair]
        else:
            raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'")
    def get_order_book(self, pair=None, depth=10):
        if pair is not None:
            if not isinstance(pair, str):
                raise TypeError("pair must be None or of type str")
            if _PAIR_REGEXP.match(pair) is None:
                raise ValueError("Malformed pair")
        if not isinstance(depth, int):
            raise TypeError("depth must be of type int")
        if depth <= 0:
            raise ValueError("depth must be a positive integer")
        if self._live_cache is None:
            return self._get_order_book(pair, depth)
        if 'order_book' not in self._live_cache or self._live_cache['order_book']['depth'] < depth:
            self._live_cache['order_book'] = {'order_book': self._get_order_book(None, depth), 'depth': depth}
        if pair is None:
            return self._cache['order_book']['order_book']
        if pair in self._cache['order_book']['order_book']:
            return self._cache['order_book']['order_book'][pair]
        else:
            raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'")
    def _get_order_book(self, pair=None, depth=10):
        raw_order_book = self.query_public_api('returnOrderBook', {'currencyPair': _encode_pair(pair) if pair is not
                None else 'all', 'depth': depth})
        if pair is not None:
            order_book = api.OrderBook(bids=[], asks=[])
            for bid in raw_order_book['bids']:
                order_book.bids.append(api.Bid(rate=Decimal(str(bid[0])), amount=Decimal(str(bid[1]))))
            for ask in raw_order_book['asks']:
                order_book.asks.append(api.Ask(rate=Decimal(str(ask[0])), amount=Decimal(str(ask[1]))))
            return order_book
        order_books = {}
        for raw_p in raw_order_book:
            p = _decode_pair(raw_p)
            order_books[p] = api.OrderBook(bids=[], asks=[])
            for bid in raw_order_book[raw_p]['bids']:
                order_books[p].bids.append(api.Bid(rate=Decimal(str(bid[0])), amount=Decimal(str(bid[1]))))
            for ask in raw_order_book[raw_p]['asks']:
                order_books[p].asks.append(api.Ask(rate=Decimal(str(ask[0])), amount=Decimal(str(ask[1]))))
        return order_books
    def get_public_trade_history(self, pair, start=None, end=None):
        if pair is not None:
            if not isinstance(pair, str):
                raise TypeError("pair must be None or of type str")
            if _PAIR_REGEXP.match(pair) is None:
                raise ValueError("Malformed pair")
        if start is not None and not isinstance(start, int):
            raise ValueError("start must be None or of type int")
        if end is not None and not isinstance(end, int):
            raise ValueError("end must be None or of type int")
        if start is None or end is None:
            now = int(time.time())
            if start is None:
                start = now - 86400 # 24 hours ago
            if end is None:
                end = now + 3 # 3 seconds from now just to make sure its getting the latest data
            del now
        if pair not in self._persistent_cache['public_trade_history']:
            try:
                trades = self._get_public_trade_history(pair, start, end)
                if len(trades) == 50000:
                    start = min(trades, key=lambda trade: trade.get_timestamp()).get_timestamp()
                    end = max(trades, key=lambda trade: trade.get_timestamp()).get_timestamp()
                self._persistent_cache['public_trade_history'][pair] = {
                    'times_cached': IntRanges((start, end)),
                    'trades': set(trades)
                }
                if len(trades) == 50000:
                    raise api.ExchangeAPIError(
                            "Reached maximum number of trades that may be retrieved in a single call: 50000")
                return trades
            except api.NonexistentPairError:
                raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'") from None
        if not self._persistent_cache['public_trade_history'][pair]['times_cached'].includes_range(start, end):
            # TODO This can be optimized - much of the data retrieved by this call may already be cached
            trades = self._get_public_trade_history(pair, start, end)
            if len(trades) == 50000:
                start = min(trades, key=lambda trade: trade.get_timestamp()).get_timestamp()
                end = max(trades, key=lambda trade: trade.get_timestamp()).get_timestamp()
            self._persistent_cache['public_trade_history'][pair]['trades'].update(trades)
            self._persistent_cache['public_trade_history'][pair]['times_cached'].add_range(start, end)
            if len(trades) == 50000:
                raise api.ExchangeAPIError(
                        "Reached maximum number of trades that may be retrieved in a single call: 50000")
        return [trade for trade in self._persistent_cache['public_trade_history'][pair]['trades'] if start <=
                trade.get_timestamp() <= end]
    def _get_public_trade_history(self, pair, start=None, end=None):
        params = {'currencyPair': _encode_pair(pair)}
        if start is not None:
            params['start'] = start
            params['end'] = end
        try:
            response = self.query_public_api('returnTradeHistory', params)
        except api.NonexistentPairError:
            raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'") from None
        return [self._parse_then_get_trade(pair, raw_trade, None) for raw_trade in response]
    def get_trade_history(self, pair, start=None, end=None):
        if not isinstance(pair, str):
            raise TypeError("pair must be of type str")
        if _PAIR_REGEXP.match(pair) is None:
            raise ValueError("Malformed pair")
        if start is not None and not isinstance(start, int):
            raise ValueError("start must be None or of type int")
        if end is not None and not isinstance(end, int):
            raise ValueError("end must be None or of type int")
        if start is None or end is None:
            now = int(time.time())
            if start is None:
                start = now - 86400 # 24 hours ago
            if end is None:
                end = now + 3 # 3 seconds from now just to make sure its getting the latest data
            del now
        if pair not in self._persistent_cache['trade_history']:
            try:
                trades = self._get_trade_history(pair, start, end)
                if len(trades) == 50000:
                    start = min(trades, key=lambda trade: trade.get_timestamp())
                    end = max(trades, key=lambda trade: trade.get_timestamp())
                self._persistent_cache['trade_history'][pair] = {
                    'times_cached': IntRanges((start, end)),
                    'trades': set(trades)
                }
                if len(trades) == 50000:
                    raise api.ExchangeAPIError(
                            "Reached maximum number of trades that may be retrieved in a single call: 50000")
                return trades
            except api.NonexistentPairError:
                raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'") from None
        if not self._persistent_cache['trade_history'][pair]['times_cached'].includes_range(start, end):
            # TODO This can be optimized - much of the data retrieved by this call may already be cached
            trades = self._get_trade_history(pair, start, end)
            if len(trades) == 50000:
                start = min(trades, key=lambda trade: trade.get_timestamp())
                end = max(trades, key=lambda trade: trade.get_timestamp())
            self._persistent_cache['trade_history'][pair]['trades'].update(trades)
            self._persistent_cache['trade_history'][pair]['times_cached'].add_range(start, end)
            if len(trades) == 50000:
                raise api.ExchangeAPIError(
                        "Reached maximum number of trades that may be retrieved in a single call: 50000")
        return [trade for trade in self._persistent_cache['trade_history'][pair]['trades'] if start <=
                trade.get_timestamp() <= end]
    def _get_trade_history(self, pair, start=None, end=None):
        params = {'currencyPair': _encode_pair(pair)}
        if start is not None:
            params['start'] = start
            params['end'] = end
        try:
            response = self.query_trading_api('returnTradeHistory', params)
        except api.NonexistentPairError:
            raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'") from None
        trades = [self._parse_then_get_trade(pair, raw_trade, self._get_order(int(raw_trade['orderNumber']),
                order_type=raw_trade['type'],
                order_subtype=raw_trade['category'],
                pair=pair,
                rate=Decimal(str(raw_trade['rate'])),
                amount=Decimal(str(raw_trade['amount'])),
                total=Decimal(str(raw_trade['total'])))) for raw_trade in response]
        if len(trades) == 50000:
            raise api.ExchangeAPIError("Reached maximum number of trades that may be retrieved in a single call: 50000")
        return trades
    def get_balance(self, currency=None, availability='all', account='all'):
        """Get the account balance of the exchange member for all currencies or for a single currency. Funds are
        included in the calculated balance if and only if all of the following conditions are met:

        - The funds are of the specified currency
        - One of the following conditions is met:
            - availability is 'all'
            - availability is 'available' and the funds are available (not on orders)
            - availability is 'on_order' and the funds are on orders
            - account is 'all' or the funds are in the specified account ('exchange', 'margin', or 'lending')

        If currency is None, then a dictionary is returned mapping all currencies with a nonzero balance to the balance
        that this function would otherwise return if the respective currency was specified.

        Args:
            currency: the symbol of the currency for which the account balance is to be retreieved, or None to retrieve
            the balance for all currencies
            availability: the state in which the funds must be ('available', or 'on_order') or 'all' to include funds
                          regardless of whether or not they are on order
            account: the account that the funds must be in ('exchange', 'margin', or 'lending') or 'all' to include all
                     accounts
        Returns:
            a dictionary mapping all currencies that have a nonzero balance to their balance if currency is None, or
            just the balance of the specified currency if currency is not None
        Raises:
            ExchangeAPIError: if an error occurs
        """
        if currency is not None:
            if not isinstance(currency, str):
                raise ValueError("currency must be None or of type str")
            if _CURRENCY_REGEXP.match(currency) is None:
                raise ValueError("Malformed currency")
        if availability not in ['all', 'available', 'on_order']:
            raise ValueError("availability must be one of 'all', 'available', or 'on_order'")
        if account not in ['all', 'exchange', 'margin', 'lending']:
            raise ValueError("account must be one of 'all', 'exchange', 'margin', or 'lending'")
        if self._live_cache is None:
            balances = self._get_balance(availability, account)
        else:
            if availability not in self._live_cache['balance']:
                self._live_cache['balance'][availability] = {}
            if account not in self._live_cache['balance'][availability]:
                self._live_cache['balance'][availability][account] = self._get_balance(availability, account)
            balances = self._live_cache['balance'][availability][account]
        if currency is None:
            return balances
        if currency in balances:
            return balances[currency]
        else:
            return Decimal(0)
    def _get_balance(self, availability, account):
        response = self.query_trading_api('returnCompleteBalances', {'account': account if account is not None else
                'all'})
        if availability == 'all':
            if account == 'all':
                response = self.query_trading_api('returnCompleteBalances', {'account': 'all'})
                balances = {}
                for c in response:
                    balances[c] = Decimal(str(response[c]['available'])) + Decimal(str(response[c]['onOrders']))
            elif account == 'exchange':
                response = self.query_trading_api('returnCompleteBalances')
                balances = {}
                for c in response:
                    balances[c] = Decimal(str(response[c]['available'])) + Decimal(str(response[c]['onOrders']))
            elif account == 'margin':
                raise api.NotSupportedError("Getting the total margin account balance is not supported")
            else: # account == 'lending'
                raise api.NotSupportedError("Getting the total lending account balance is not supported")
        elif availability == 'available':
            if account == 'all':
                response = self.query_trading_api('returnAvailableAccountBalances')
                balances = {}
                for a in response:
                    for c in response[a]:
                        if c not in balances:
                            balances[c] = Decimal(0)
                        balances[c] += Decimal(str(response[a][c]))
            elif account == 'exchange':
                response = self.query_trading_api('returnAvailableAccountBalances', {'account': 'exchange'})
                balances = {}
                for c in response['exchange']:
                    balances[c] = Decimal(str(response['exchange'][c]))
            elif account == 'margin':
                response = self.query_trading_api('returnAvailableAccountBalances', {'account': 'margin'})
                balances = {}
                for c in response['margin']:
                    balances[c] = Decimal(str(response['margin'][c]))
            else: # account == 'lending'
                response = self.query_trading_api('returnAvailableAccountBalances', {'account': 'lending'})
                balances = {}
                for c in response['lending']:
                    balances[c] = Decimal(str(response['lending'][c]))
        else: # availability == 'on_order'
            if account == 'all':
                response = self.query_trading_api('returnCompleteBalances', {'account': 'all'})
                balances = {}
                for c in response:
                    balances[c] = Decimal(str(response[c]['onOrders']))
            elif account == 'exchange':
                response = self.query_trading_api('returnCompleteBalances')
                balances = {}
                for c in response:
                    balances[c] = Decimal(str(response[c]['onOrders']))
            elif account == 'margin':
                raise api.NotSupportedError("Getting the margin account balance on order is not supported")
            else: # account == 'lending'
                raise api.NotSupportedError("Getting the lending account balance on order is not supported")
        to_remove = []
        for c in balances:
            if balances[c] == 0:
                to_remove.append(c)
        for c in to_remove:
            del balances[c]
        return balances
    def get_open_orders(self, pair=None):
        if pair is not None:
            if not isinstance(pair, str):
                raise TypeError("pair must be None or of type str")
            if _PAIR_REGEXP.match(pair) is None:
                raise ValueError("Malformed pair")
        if self._live_cache is None:
            return self._get_open_orders(pair)
        if 'open_orders' not in self._live_cache:
            self._live_cache['open_orders'] = self._get_open_orders()
        if pair is None:
            return self._live_cache['open_orders']
        if pair in self._live_cache['open_orders']:
            return self._live_cache['open_orders'][pair]
        else:
            raise api.NonexistentPairError("Nonexistent currency pair '" + pair + "'")
    def _get_open_orders(self, pair=None):
        response = self.query_trading_api('returnOpenOrders', {'currencyPair': _encode_pair(pair) if pair is not None
                else 'all'})
        if pair is None:
            open_orders = {}
            for raw_p in response:
                p = _decode_pair(raw_p)
                open_orders[p] = []
                for raw_order in response[raw_p]:
                    open_orders[p].append(self._get_order(int(raw_order['orderNumber']),
                            order_type=raw_order['type'],
                            # TODO What if it's a lending order?
                            order_subtype='margin' if raw_order['margin'] == 1 else 'exchange',
                            pair=p,
                            rate=Decimal(str(raw_order['rate'])),
                            amount=Decimal(str(raw_order['amount'])),
                            total=Decimal(str(raw_order['total']))))
            return open_orders
        else:
            open_orders = []
            for raw_order in response:
                open_orders.append(self._get_order(int(raw_order['orderNumber']),
                        order_type=raw_order['type'],
                        # TODO What if it's a lending order?
                        order_subtype='margin' if raw_order['margin'] == 1 else 'exchange',
                        pair=pair,
                        rate=Decimal(str(raw_order['rate'])),
                        amount=Decimal(str(raw_order['amount'])),
                        total=Decimal(str(raw_order['total']))))
            return open_orders
    def get_order_trades(self, order):
        if not isinstance(order, PoloniexAPI.Order):
            raise TypeError("order must be of type PoloniexAPI.Order")
        if self._live_cache is None:
            return self._get_order_trades(order)
        if order not in self._live_cache['order_trades']:
            self._live_cache['order_trades'][order] = self._get_order_trades(order)
        return self._live_cache['order_trades'][order]
    def _get_order_trades(self, order):
        try:
            response = self.query_trading_api('returnOrderTrades', {'orderNumber': str(order.order_number)})
            return [self._parse_then_get_trade(_decode_pair(raw_trade['currencyPair']), raw_trade, order) for raw_trade in
                    response]
        except OrderNotFoundError:
            return []
    def place_buy_order(self, pair, rate, amount, order_subtype='exchange', lending_rate="0.02"):
        if not isinstance(pair, str):
            raise TypeError("pair must be of type str")
        if _PAIR_REGEXP.match(pair) is None:
            raise ValueError("Malformed pair")
        rate = Decimal(str(rate))
        if rate < 0:
            raise ValueError("rate must be >= 0")
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("amount must be > 0")
        if order_subtype == 'exchange':
            response = self.query_trading_api('buy', {'currencyPair': _encode_pair(pair), 'rate': "{:f}".format(rate),
                    'amount': "{:f}".format(amount)})
            order = self._get_order(int(response['orderNumber']),
                    order_type='buy',
                    order_subtype='exchange',
                    pair=pair,
                    rate=rate,
                    amount=amount,
                    total=None) # TODO Calculate total
            if self._live_cache is not None and 'open_orders' in self._live_cache:
                self._live_cache['open_orders'][pair].append(order)
            return order
        if order_subtype == 'margin':
            lending_rate = Decimal(str(lending_rate))
            response = self.query_trading_api('marginBuy', {'currencyPair': _encode_pair(pair), 'rate':
                    "{:f}".format(rate), 'amount': "{:f}".format(amount), 'lendingRate': "{:f}".format(lending_rate)})
            order = self._get_order(int(response['orderNumber']),
                    order_type='buy',
                    order_subtype='margin',
                    pair=pair,
                    rate=rate,
                    amount=amount,
                    total=None) # TODO Calculate total
            if self._live_cache is not None and 'open_orders' in self._live_cache:
                self._live_cache['open_orders'][pair].append(order)
            return order
        else:
            raise ValueError("order_subtype must be 'exchange' or 'margin'")
    def place_sell_order(self, pair, rate, amount, order_subtype='exchange', lending_rate="0.02"):
        if not isinstance(pair, str):
            raise TypeError("pair must be of type str")
        if _PAIR_REGEXP.match(pair) is None:
            raise ValueError("Malformed pair")
        rate = Decimal(str(rate))
        if rate < 0:
            raise ValueError("rate must be >= 0")
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("amount must be > 0")
        if order_subtype == 'exchange':
            response = self.query_trading_api('sell', {'currencyPair': _encode_pair(pair), 'rate': "{:f}".format(rate),
                    'amount': "{:f}".format(amount)})
            order = self._get_order(int(response['orderNumber']),
                    order_type='sell',
                    order_subtype='exchange',
                    pair=pair,
                    rate=rate,
                    amount=amount,
                    total=None) # TODO Calculate total
            if self._live_cache is not None and 'open_orders' in self._live_cache:
                self._live_cache['open_orders'][pair].append(order)
            return order
        if order_subtype == 'margin':
            lending_rate = Decimal(str(lending_rate))
            response = self.query_trading_api('marginSell', {'currencyPair': _encode_pair(pair), 'rate':
                    "{:f}".format(rate), 'amount': "{:f}".format(amount), 'lendingRate': "{:f}".format(lending_rate)})
            order = self._get_order(int(response['orderNumber']),
                    order_type='sell',
                    order_subtype='margin',
                    pair=pair,
                    rate=rate,
                    amount=amount,
                    total=None) # TODO Calculate total
            if self._live_cache is not None and 'open_orders' in self._live_cache:
                self._live_cache['open_orders'][pair].append(order)
            return order
        else:
            raise ValueError("order_subtype must be 'exchange' or 'margin'")
    def cancel_order(self, order):
        if not isinstance(order, PoloniexAPI.Order):
            raise TypeError("order must be of type PoloniexAPI.Order")
        self.query_trading_api('cancelOrder', {'orderNumber': str(order.order_number)})
        if self._live_cache is not None and 'open_orders' in self._live_cache:
            del self._live_cache['open_orders']
    def modify_order(self, order, new_rate=None, new_amount=None):
        if not isinstance(order, PoloniexAPI.Order):
            raise TypeError("order must be of type PoloniexAPI.Order")
        if new_rate is None and new_amount is None:
            return
        params = {'orderNumber': str(order.order_number)}
        if new_rate is not None:
            params['rate'] = "{:f}".format(Decimal(str(new_rate)))
        else:
            params['rate'] = "{:f}".format(order.rate)
        if new_amount is not None:
            params['amount'] = "{:f}".format(Decimal(str(new_amount)))
        self.query_trading_api('moveOrder', params)
        if self._live_cache is not None and 'open_orders' in self._live_cache:
            del self._live_cache['open_orders']
