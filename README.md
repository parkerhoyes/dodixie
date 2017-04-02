# Dodixie v0.0.0

Dodixie is a Python 3.x library for interfacing with cryptocurrency exchanges
(currently only Poloniex is supported). This library exposes a high-level,
abstract API that internally leverages Poloniex's trading API to make trades,
analyze market data, place loans, or make deposits / withdrawals.

The following assumptions about the Poloniex API were made during the
development of this library. After thorough testing, it appears as though all of
these assumptions are correct; however, they are not documented by Poloniex.

- The unit of least precision (ULP) of all currencies on Poloniex is 0.00000001.
- API calls that take a time range (eg. `returnTradeHistory`) are inclusive on
  both the start and end of the range.
- A trade's fees are always rounded up to the nearest ULP.
- If the `returnTradeHistory` commands limit output to 50000 trades, the trades
  returned are chronologically contiguous (but not necessarily chronologically
  ordered). Otherwise, if the output is not 50000 trades, `returnTradeHistory`
  excludes no trades from the time range specified.

## Disclaimers

This project is not officially sanctioned by Poloniex.

Cryptocurrency trading is very risky as it is, without adding bots to the mix.
Using a trading API / bot should only be done by those with an advanced
understanding of Python and how Poloniex's API works. **In no event will the
authors of this library be held liable for any damages arising from the use of
this library.** You've been warned.

That being said, if you encounter any issues with this library, or with the
Poloniex API, please submit an issue so I can fix it (or create a work-around in
the case of an API problem) as soon as possible.

## Development Cycle

This repository will follow a Git branching model similar to that described in
[Vincent Driessen's *A successful Git branching
model*](http://nvie.com/posts/a-successful-git-branching-model/) and a
versioning scheme similar to that defined by [Semantic Versioning
2.0.0](http://semver.org/) (though perhaps less strict).

## License

This library is distributed under the terms of the very permissive [Zlib
License](https://opensource.org/licenses/Zlib). The exact text of this license
is reproduced in the `LICENSE.txt` file as well as at the top of every source
file in this repository.
