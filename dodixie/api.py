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

"""A module containing the abstract definition of a wrapper API for interfacing with cryptocurrency exchanges.

An implementation of this API for any particular exchange will extend the ExchangeAPI abstract class. Different
exchanges will have APIs of differing integrity and completeness, so not all functionality will be equally supported
across implementations. In a case where an underlying logic error occurs or where there is an error originating from the
underlying exchange API, an ExchangeAPIError will be raised. Some implementations may provide extra functionality not
defined in this module.

Terminology:
    the exchange: the platform to which this API provides access on which fiat currencies and / or cryptocurrencies can
                  be exchanged between members
    the member: the entity whose accounts and orders are being accessed and / or modified by this API; not all APIs
                require a specific "member" to be defined for some operations to work (eg. for public API calls)
    pair: a pairing of two currencies which can be exchanged; "buying" a pair refers to buying the pair's base currency
          using its quote currency and "selling" a pair refers to selling the pair's base currency for the pair's quote
          currency
    quote currency: the currency in a pair in which the value of the base currency is "quoted"
    base currency: the currency in a pair whose value is quoted in the quote currency
    margin trading: trading using funds borrowed from the exchange or from other members
"""

from abc import ABC, abstractmethod
from collections import namedtuple
from decimal import Decimal

from .utils import *

__all__ = [
    'ExchangeAPIError',
    'NonexistentPairError',
    'NotSupportedError',
    'InsufficientInformationError',
    'PairInfo',
    'Ticker',
    'OrderBook',
    'Bid',
    'Ask',
    'Balance',
    'ExchangeAPI'
]

class ExchangeAPIError(RuntimeError):
    """An error resulting from an interaction with an exchange's API."""
    pass

class NonexistentPairError(ExchangeAPIError):
    """An error resulting from a caller of this API providing a currency pair that is not present on the exchange (but
    still syntactically correct)."""
    pass

class NotSupportedError(ExchangeAPIError):
    """An error indicating that a caller of this API requested an operation that is not supported (by this API and / or
    by the underlying exchange API)."""
    pass

class InsufficientInformationError(ExchangeAPIError):
    """An error indicating that a caller of this API requested information or information was required which could not
    be determined."""
    pass

"""A named tuple representing information for a particular currency pair.

base_ulp: the unit of the last place (the smallest representable amount) of the base currency
quote_ulp: the unit of the last place (the smallest representable amount) of the quote currency
base_volume: the 24-hour volume of the base currency for this currency pair
quote_volume: the 24-hour volume of the quote currency for this currency pair
percent_change: the percentage change of the value of this pair from 24 hours ago, represented as a decimal
"""
PairInfo = namedtuple("PairInfo", ("base_ulp", "quote_ulp", "base_volume", "quote_volume", "percent_change"))

"""A named tuple representing the ticker values for a particular currency pair.

highest_bid: the highest bid for this currency pair
lowest_ask: the lowest ask for this currency pair
last: the rate of the last trade made for this currency pair
"""
Ticker = namedtuple("Ticker", ("highest_bid", "lowest_ask", "last"))

"""A named tuple representing the order book for a particular currency pair.

bids: a list of Bid objects in descending order by rate for this currency pair
asks: a list of Ask objects in ascending order by rate for this currency pair
"""
OrderBook = namedtuple("OrderBook", ("bids", "asks"))

"""A named tuple representing a single bid for a particular currency pair.

rate: the rate, in the quote currency, offered for one unit of the base currency
amount: the amount, in the base currency, being requested in this bid
"""
Bid = namedtuple("Bid", ("rate", "amount"))

"""A named tuple representing a single ask for a particular currency pair.

rate: the rate, in the quote currency, requested for one unit of the base currency
amount: the amount, in the base currency, being offered in this ask
"""
Ask = namedtuple("Ask", ("rate", "amount"))

"""A named tuple representing the balance of a particular account.

available: the amount in the account available for placing orders
on_orders: the amount in the account currently on order and as such is not available
"""
Balance = namedtuple("Balance", ("available", "on_orders"))

class ExchangeAPI(ABC):
    class Trade(ABC):
        """A handle for a single trade made between two members of an exchange. This type is interned."""
        def info(self):
            """Generate a new ObjectInfo object that describes this object."""
            info = ObjectInfo(self.__class__.__qualname__)
            info.add_info("Trade Type", self.get_trade_type)
            info.add_info("Pair", self.get_pair)
            info.add_info("Rate", lambda: "{:f}".format(self.get_rate()) + ' ' + self.get_pair().split('/')[1])
            info.add_info("Amount", lambda: "{:f}".format(self.get_amount()) + ' ' + self.get_pair().split('/')[0])
            info.add_info("Total", lambda: "{:f}".format(self.get_total()) + ' ' + self.get_pair().split('/')[1])
            info.add_info("Fee", lambda: "{:f}".format(self.get_fee()) + ' ' + self.get_pair().split('/')[0])
            info.add_info("Timestamp", lambda: format_timestamp(self.get_timestamp()))
            return info
        def describe(self):
            """Print a description of this object to standard output."""
            print(self.info().format_multiline(), end="")
        def __eq__(self, other):
            return other is self
        @property
        @abstractmethod
        def api(self):
            """Get a reference to the ExchangeAPI object that was used to retrieve this trade."""
            pass
        def get_trade_type(self):
            """Get the type of this trade, "buy" or "sell".

            Returns:
                the type of this trade, "buy" or "sell"
            Raises:
                InsufficientInformationError: if the trade type is unknown
            """
            trade_type = self.get_trade_type_or_none()
            if trade_type is None:
                raise InsufficientInformationError("Trade type is unknown")
            return trade_type
        @abstractmethod
        def get_trade_type_or_none(self):
            """Get the type of this trade, "buy" or "sell".

            Returns:
                the type of this trade, "buy" or "sell", or None if the trade type is unknown
            """
            pass
        def get_pair(self):
            """Get the pair for which this trade was made.

            Returns:
                a string representing the pair for which this trade was made, in the format "X/Y" where X is the base
                currency symbol and Y is the quote currency symbol
            Raises:
                InsufficientInformationError: if the trade pair is unknown
            """
            pair = self.get_pair_or_none()
            if pair is None:
                raise InsufficientInformationError("Trade pair is unknown")
            return pair
        @abstractmethod
        def get_pair_or_none(self):
            """Get the pair for which this trade was made.

            Returns:
                a string representing the pair for which this trade was made, in the format "X/Y" where X is the base
                currency symbol and Y is the quote currency symbol, or None if the trade pair is unknown
            """
            pass
        def get_rate(self):
            """Get the rate, in the quote currency, at which this trade was made.

            Returns:
                the rate, in the quote currency, at which this trade was made
            Raises:
                InsufficientInformationError: if the trade rate is unknown
            """
            rate = self.get_rate_or_none()
            if rate is None:
                raise InsufficientInformationError("Trade rate is unknown")
            return rate
        @abstractmethod
        def get_rate_or_none(self):
            """Get the rate, in the quote currency, at which this trade was made.

            Returns:
                the rate, in the quote currency, at which this trade was made, or None if the trade rate is unknown
            """
            pass
        def get_amount(self):
            """Get the amount of the base currency for which this trade was made.

            Returns:
                the amount of the base currency for which this trade was made
            Raises:
                InsufficientInformationError: if the trade amount is unknown
            """
            amount = self.get_amount_or_none()
            if amount is None:
                raise InsufficientInformationError("Trade amount is unknown")
            return amount
        @abstractmethod
        def get_amount_or_none(self):
            """Get the amount of the base currency for which this trade was made.

            Returns:
                the amount of the base currency for which this trade was made, or None if the trade amount is unknown
            """
            pass
        def get_total(self):
            """Get the amount of the quote currency for which this trade was made.

            Returns:
                the amount of the quote currency for which this trade was made
            Raises:
                InsufficientInformationError: if the trade total is unknown
            """
            total = self.get_total_or_none()
            if total is None:
                raise InsufficientInformationError("Trade total is unknown")
            return total
        @abstractmethod
        def get_total_or_none(self):
            """Get the amount of the quote currency for which this trade was made, less the fee.

            Returns:
                the amount of the quote currency for which this trade was made, less the fee, or None if the trade total
                is unknown
            """
            pass
        def get_fee(self):
            """Get the fee charged for this trade, in the base currency.

            Returns:
                the fee charged for this trade, in the base currency
            Raises:
                InsufficientInformationError: if the trade fee is unknown
            """
            fee = self.get_fee_or_none()
            if fee is None:
                raise InsufficientInformationError("Trade fee is unknown")
            return fee
        @abstractmethod
        def get_fee_or_none(self):
            """Get the fee charged for this trade, in the base currency.

            Returns:
                the fee charged for this trade, in the base currency, or None if the trade fee is unknown
            """
            pass
        def get_timestamp(self):
            """Get the UNIX timestamp for the time at which this trade occurred.

            Returns:
                the time, in seconds, from the UNIX epoch to the time at which this trade occurred
            Raises:
                InsufficientInformationError: if the trade timestamp is unknown
            """
            timestamp = self.get_timestamp_or_none()
            if timestamp is None:
                raise InsufficientInformationError("Trade timestamp is unknown")
            return timestamp
        @abstractmethod
        def get_timestamp_or_none(self):
            """Get the UNIX timestamp for the time at which this trade occurred.

            Returns:
                the time, in seconds, from the UNIX epoch to the time at which this trade occurred, or None if the trade
                timestamp is unknown
            """
            pass
    class Order(ABC):
        """A class that serves as a handle object that provides an interface to information related to and operations
        that can be performed on a single order. This type is interned."""
        def info(self):
            """Generate a new ObjectInfo object that describes this object."""
            info = ObjectInfo(self.__class__.__qualname__)
            info.add_info("Order Type", self.get_order_type)
            info.add_info("Order Subtype", self.get_order_subtype)
            info.add_info("Pair", self.get_pair)
            info.add_info("Rate", lambda: "{:f}".format(self.get_rate()) + " " + self.get_pair().split('/')[1])
            info.add_info("Amount", lambda: "{:f}".format(self.get_amount()) + " " + self.get_pair().split('/')[0])
            info.add_info("Total", lambda: "{:f}".format(self.get_total()) + " " + self.get_pair().split('/')[1])
            info.add_info("Is Open", lambda: "Yes" if self.is_open() else "No")
            info.add_info("Amount Outstanding", lambda: "{:f}".format(self.get_amount_outstanding()) + " " +
                    self.get_pair().split('/')[0])
            return info
        def describe(self):
            """Print a description of this object to standard output."""
            print(self.info().format_multiline(), end="")
        def __eq__(self, other):
            return other is self
        @property
        @abstractmethod
        def api(self):
            """Get a reference to the ExchangeAPI object that was used to retrieve this order."""
            pass
        def get_order_type(self):
            """Get the order type, "buy" or "sell".

            Returns:
                the order type, "buy" or "sell"
            Raises:
                InsufficientInformationError: if the order type is unknown
            """
            order_type = self.get_order_type_or_none()
            if order_type is None:
                raise InsufficientInformationError("Order type is unknown")
            return order_type
        @abstractmethod
        def get_order_type_or_none(self):
            """Get the order type, "buy" or "sell".

            Returns:
                the order type, "buy" or "sell", or None if the order type is unknown
            """
            pass
        def get_order_subtype(self):
            """Get the order subtype, "exchange" or "margin".

            Returns:
                the order subtype, "exchange" or "margin"
            Raises:
                InsufficientInformationError: if the order subtype is unknown
            """
            order_subtype = self.get_order_subtype_or_none()
            if order_subtype is None:
                raise InsufficientInformationError("Order subtype is unknown")
            return order_subtype
        @abstractmethod
        def get_order_subtype_or_none(self):
            """Get the order subtype, "exchange" or "margin".

            Returns:
                the order subtype, "exchange" or "margin", or None if the order subtype is unknown
            """
            pass
        def get_pair(self):
            """Get the pair for which this order was placed.

            Returns:
                a string representing the pair for which this order was placed, in the format "X/Y" where X is the base
                currency symbol and Y is the quote currency symbol
            Raises:
                InsufficientInformationError: if the order pair is unknown
            """
            pair = self.get_pair_or_none()
            if pair is None:
                raise InsufficientInformationError("Order pair is unknown")
            return pair
        @abstractmethod
        def get_pair_or_none(self):
            """Get the pair for which this order was placed.

            Returns:
                a string representing the pair for which this order was placed, in the format "X/Y" where X is the base
                currency symbol and Y is the quote currency symbol, or None if the order pair is unknown
            """
            pass
        def get_rate(self):
            """Get the rate for which this order was placed.

            Returns:
                the rate, in the quote currency, for which this order was placed
            Raises:
                InsufficientInformationError: if the order rate is unknown
            """
            rate = self.get_rate_or_none()
            if rate is None:
                raise InsufficientInformationError("Order rate is unknown")
            return rate
        @abstractmethod
        def get_rate_or_none(self):
            """Get the rate, in the quote currency, for which this order was placed.

            Returns:
                the rate, in the quote currency, for which this order was placed, or None if the order rate is unknown
            """
            pass
        def get_amount(self):
            """Get the amount, in the base currency, that is currently outstanding on this order.

            Returns:
                the amount, in the base currency, that is currency outstanding on this order
            Raises:
                InsufficientInformationError: if the order amount is unknown
            """
            amount = self.get_amount_or_none()
            if amount is None:
                raise InsufficientInformationError("Order amount is unknown")
            return amount
        @abstractmethod
        def get_amount_or_none(self):
            """Get the amount, in the base currency, that is currently outstanding on this order.

            Returns:
                the amount, in the base currency, that is currency outstanding on this order, or None if the order
                amount is unknown
            """
            pass
        def get_total(self):
            """Get the amount, in the quote currency, that is currently outstanding on this order.

            Returns:
                the amount, in the quote currency, that is currency outstanding on this order
            Raises:
                InsufficientInformationError: if the order total is unknown
            """
            total = self.get_total_or_none()
            if total is None:
                raise InsufficientInformationError("Order total is unknown")
            return total
        @abstractmethod
        def get_total_or_none(self):
            """Get the amount, in the quote currency, that is currently outstanding on this order.

            Returns:
                the amount, in the quote currency, that is currency outstanding on this order, or None if the order
                total is unknown
            """
            pass
        def is_open(self):
            """Return True if this order is open, or False if it is closed.

            Raises:
                InsufficientInformationError: if the order's state is unknown
            """
            is_open = self.is_open_or_none()
            if is_open is None:
                raise InsufficientInformationError("Order state is unknown")
            return is_open
        @abstractmethod
        def is_open_or_none(self):
            """Return True if this order is open, False if it is closed, or None if the order's state is unknown."""
            pass
        def get_amount_outstanding(self):
            """Get the amount, in the base currency, currently outstanding on this order."""
            outstanding = self.get_amount()
            for trade in self.get_trades():
                outstanding -= trade.get_amount()
            return outstanding
        def get_trades(self):
            """Return the result of self.api.get_order_trades(self)."""
            return self.api.get_order_trades(self)
        def cancel(self):
            """Cancel this order."""
            self.api.cancel_order(self)
        def modify(self, new_rate=None, new_amount=None):
            """Modify this order's rate and / or this order's amount.

            Args:
                new_rate: the new rate for this order or None if the rate is not to be modified
                new_amount: the new amount for this order or None if the amount is not to be modified
            """
            self.api.modify_order(self, new_rate, new_amount)
    @abstractmethod
    def enable_live_cache(self):
        """Suggest that this object enable a cache which may cache any output received from the exchange API that
        changes over time (eg. the current ticker for a pair). This should not be enabled for a long period of time."""
        pass
    @abstractmethod
    def disable_live_cache(self):
        """Disable the live cache of the exchange API's results, if it is enabled (clearing the cache in the
        process)."""
        pass
    @abstractmethod
    def clear_live_cache(self):
        """Clear the live cache."""
        pass
    @abstractmethod
    def is_live_cache_enabled(self):
        """Return True if results from the exchange API that change over time may be cached, or False otherwise."""
        pass
    @abstractmethod
    def get_pair_info(self, pair=None):
        """Get a PairInfo object describing current information for the specified pair or all pairs.

        Args:
            pair: the pair for which to get information, or None to get information for all pairs available on this
                  exchange
        Returns:
            a PairInfo object describing current information for the specified pair or, if pair is None, a dictionary of
            the information for every pair available on this exchange where the keys are the pair strings and the values
            are the corresponding PairInfo objects
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_ticker(self, pair=None):
        """Get a Ticker object describing the currenct ticker data for the specified pair or all pairs.

        Args:
            pair: the pair for which to get ticker data, or None to get ticker data for all pairs available on this
                  exchange
        Returns:
            a Ticker object describing the currenct ticker data for the specified pair or, if pair is None, a dictionary
            of the ticker data for every pair available on this exchange where the keys are the pair strings and the
            values are the corresponding Ticker objects
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_order_book(self, pair=None, depth=10):
        """Get the order book for the specified pair or all pairs.

        Args:
            pair: the pair for which to get the order book or None to get a dictionary containing the order books for
            all pairs available on this exchange
            depth: the minimum number of bids & asks to get for each order book
        Returns:
            an OrderBook object representing the orders for the specified pair or, if pair is None, a dictionary
            containing the order books for all pairs available on this exchange where the keys are the pair strings and
            the values are the corresponding OrderBook objects
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_public_trade_history(self, pair, start=None, end=None):
        """Get the history of all trades that have been made on this exchange for the specified pair during the
        specified time period.

        Args:
            pair: a string representing the pair for which to get the public trade history
            start: the number of seconds since the UNIX epoch since which the public trade history is to be retrieved
                   or None to indicate 24 hours ago
            end: the number of seconds since the UNIX epoch until which trade history is to be retrieved or None to
                 indicate the end of trading history
        Returns:
            a list of all trades, in an undefined order, matching the specified parameters
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_trade_history(self, pair, start=None, end=None):
        """Get the history of the account holder's trades that have been made on this exchange for the specified pair
        during the specified time period.

        Args:
            pair: a string representing the pair for which to get the trade history
            start: the number of seconds since the UNIX epoch since which the account holder's trade history is to be
                   retrieved or None to indicate 24 hours ago
            end: the number of seconds since the UNIX epoch until which the account holder's trade history is to be
                 retrieved or None to indicate the end of trading history
        Returns:
            a list of all trades made by the member, in an undefined order, matching the specified parameters
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_balance(self, currency=None):
        """Get the account balance of the specified currency of the exchange member.

        Args:
            currency: the symbol of the currency for which the account balance is to be retreieved
        Returns:
            a number representing the quantity of the specified currency in the exchange member's account
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_detailed_balance(self, currency=None):
        """Get the account balance of the specified currency of the exchange member.

        Args:
            currency: the symbol of the currency for which the account balance is to be retreieved
        Returns:
            a Balance object describing the account balance of the specified currency of the exchange member
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_open_orders(self, pair=None):
        """Get a list of all outstanding (open) orders by the exchange member for the specified pair or all pairs.

        Args:
            pair: a string representing the pair for which a list of open orders is to be retreieved or None to get a
                  dictionary mapping all pairs available on this exchange to the list of open orders for that pair
        Returns:
            a list of Order objects representing all outstanding (open) orders by the exchange member for the specified
            pair or, if pair is None, a dictionary containing all such orders for all pairs available on this exchange
            where the keys represent the currency pair strings and the values are a corresponding list as described
            before
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def get_order_trades(self, order):
        """Get a list of all trades made to fill (or partially fill) the specified order.

        Args:
            order: an Order object representing the order for which to get all trades
        Returns:
            a list of Trade objects, in an unspecified order, of all trades made to fill (or partially fill) the
            specified order
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def place_buy_order(self, pair, rate, amount, account="exchange"):
        """Place a buy order defined by the specified pair, rate, amount, and account.

        Args:
            pair: a string representing the pair for which to place a buy order
            rate: the rate, in the quote currency, at which to place the buy order
            amount: the amount, in the base currency, that is to define the size of the order
            account="exchange": the account for which to place the order, "exchange" or "margin"
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def place_sell_order(self, pair, rate, amount, account="exchange"):
        """Place a buy order defined by the specified pair, rate, amount, and account.

        Args:
            pair: a string representing the pair for which to place the sell order
            rate: the rate, in the quote currency, at which to place the sell order
            amount: the amount, in the base currency, that is to define the size of the order
            account="exchange": the account for which to place the order, "exchange" or "margin"
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def cancel_order(self, order):
        """Cancel the specified order.

        Args:
            order: an Order object representing the order that is to be cancelled
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    @abstractmethod
    def modify_order(self, order, new_rate=None, new_amount=None):
        """Modify the specified order's rate and / or the order's amount.

        Args:
            new_rate: the new rate for the order or None if the rate is not to be modified
            new_amount: the new amount for the order or None if the amount is not to be modified
        Raises:
            ExchangeAPIError: if an error occurs
        """
        pass
    def get_volume_within(self, pair, start_time, end_time, min_rate, max_rate):
        """Get the total volume of all trades executed for the specified pair during a specified time period and rate
        range.

        Args:
            pair: the string representing the pair for which the volume is to be queried
            start_time: the number of seconds since the UNIX epoch that represents the start of the time period for
                        which volume is to be queried
            end_time: the number of seconds since the UNIX epoch that represents the end of the time period for
                      which volume is to be queried
            min_rate: the minimum rate, in the quote currency, of a trade that should be included in the results
            max_rate: the maximum rate, in the quote currency, of a trade that should be included in the results
        Returns:
            a tuple of the form (base_volume, quote_volume) where the base_volume is the total volume of the base
            currency exchanged in trades that matched the specified parameters and quote_volume is the total volume the
            quote currency exchanged in trades that matched the specified parameters
        Raises:
            ExchangeAPIError: if an error occurs
        """
        min_rate = Decimal(min_rate)
        if min_rate < 0:
            raise ValueError("min_rate must be >= 0")
        max_rate = Decimal(max_rate)
        if max_rate < min_rate:
            raise ValueError("max_rate must be >= min_rate")
        base_volume = Decimal(0)
        quote_volume = Decimal(0)
        for trade in self.get_public_trade_history(pair, start_time, end_time):
            if min_rate is not None and trade.get_rate() < min_rate:
                continue
            if max_rate is not None and trade.get_rate() > max_rate:
                continue
            base_volume += trade.get_amount()
            quote_volume += trade.get_total()
        return base_volume, quote_volume
