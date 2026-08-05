"""Exact raw-unit conversions shared by Robinhood accounting scripts."""
from decimal import Decimal, getcontext

getcontext().prec = 90
Q192 = Decimal(2) ** 192


def raw_to_units(raw, decimals):
    return Decimal(int(raw)) / (Decimal(10) ** int(decimals))


def v3_quote_per_token(sqrt_price_x96, token_is_token1, token_decimals, quote_decimals):
    raw_ratio = Decimal(int(sqrt_price_x96)) ** 2 / Q192  # token1_raw/token0_raw
    if raw_ratio <= 0:
        raise ValueError("sqrtPriceX96 must be positive")
    directed = (Decimal(1) / raw_ratio) if token_is_token1 else raw_ratio
    return directed * (Decimal(10) ** (int(token_decimals) - int(quote_decimals)))
