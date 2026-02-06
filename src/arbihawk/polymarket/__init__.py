"""
Polymarket Trading Module

Provides multiple trading strategies for Polymarket prediction markets.
"""

from .scanner import PolymarketScanner, Market
from .strategies import (
    Trade,
    StrategyType,
    ArbitrageStrategy,
    MomentumStrategy,
    MarketMakingStrategy,
    NewsDrivenStrategy,
    MultiStrategyTrader
)
from .trader import PaperTrader

__all__ = [
    'PolymarketScanner',
    'Market',
    'Trade',
    'StrategyType',
    'ArbitrageStrategy',
    'MomentumStrategy',
    'MarketMakingStrategy',
    'NewsDrivenStrategy',
    'MultiStrategyTrader',
    'PaperTrader'
]
