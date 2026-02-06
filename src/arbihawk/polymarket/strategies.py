"""
Polymarket Trading Strategies

Multiple strategies for profiting from prediction markets:
1. Arbitrage - Buy YES + NO when sum < 1.0
2. Market Making - Provide liquidity, earn fees
3. Momentum - Trade on price trends
4. News/Event - React to breaking news faster than market
5. Whale Following - Copy large trader movements
"""

import aiohttp
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import json
from pathlib import Path


class StrategyType(Enum):
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"
    MOMENTUM = "momentum"
    NEWS_DRIVEN = "news_driven"
    WHALE_FOLLOWING = "whale_following"


@dataclass
class Trade:
    """A trade record."""
    trade_id: str
    strategy: StrategyType
    market_id: str
    market_title: str
    trade_type: str  # 'buy_yes', 'buy_no', 'sell_yes', 'sell_no'
    amount: float
    price: float
    expected_profit: float
    timestamp: datetime
    status: str = "pending"  # pending, executed, settled
    actual_profit: float = 0.0
    notes: str = ""


@dataclass
class Market:
    """Market data."""
    market_id: str
    title: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    timestamp: datetime
    outcome: Optional[str] = None


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str, min_confidence: float = 0.6):
        self.name = name
        self.min_confidence = min_confidence
        self.trades: List[Trade] = []
        self.total_pnl = 0.0
        self.trade_count = 0
    
    @abstractmethod
    async def analyze(self, market: Market) -> Optional[Trade]:
        """Analyze a market and return a trade if opportunity exists."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics."""
        return {
            'name': self.name,
            'total_pnl': self.total_pnl,
            'trade_count': self.trade_count,
            'win_rate': sum(1 for t in self.trades if t.actual_profit > 0) / max(len(self.trades), 1)
        }


class ArbitrageStrategy(BaseStrategy):
    """Pure arbitrage: Buy YES + NO when sum < 1.0"""
    
    def __init__(self, min_spread: float = 0.01, max_position: float = 1.0):
        super().__init__("Arbitrage", min_confidence=0.9)
        self.min_spread = min_spread
        self.max_position = max_position
    
    async def analyze(self, market: Market) -> Optional[Trade]:
        combined = market.yes_price + market.no_price
        
        if combined >= 1.0:
            return None
        
        spread = 1.0 - combined
        if spread < self.min_spread:
            return None
        
        position_size = min(self.max_position, market.liquidity * 0.1)
        expected_profit = position_size * spread
        
        return Trade(
            trade_id=f"arb_{market.market_id}_{datetime.utcnow().timestamp()}",
            strategy=StrategyType.ARBITRAGE,
            market_id=market.market_id,
            market_title=market.title,
            trade_type="buy_both",
            amount=position_size,
            price=combined,
            expected_profit=expected_profit,
            timestamp=datetime.utcnow(),
            notes=f"YES: ${market.yes_price}, NO: ${market.no_price}, Spread: {spread:.4f}"
        )


class MomentumStrategy(BaseStrategy):
    """Trade on price momentum/trends."""
    
    def __init__(self, lookback_periods: int = 5, momentum_threshold: float = 0.05):
        super().__init__("Momentum", min_confidence=0.55)
        self.lookback_periods = lookback_periods
        self.momentum_threshold = momentum_threshold
        self.price_history: Dict[str, List[float]] = {}
    
    def update_price_history(self, market: Market):
        """Track price history for momentum calculation."""
        if market.market_id not in self.price_history:
            self.price_history[market.market_id] = []
        
        self.price_history[market.market_id].append(market.yes_price)
        
        # Keep only recent history
        if len(self.price_history[market.market_id]) > self.lookback_periods + 1:
            self.price_history[market.market_id].pop(0)
    
    async def analyze(self, market: Market) -> Optional[Trade]:
        self.update_price_history(market)
        
        history = self.price_history.get(market.market_id, [])
        if len(history) < self.lookback_periods:
            return None
        
        # Calculate momentum (% change over lookback)
        old_price = history[0]
        new_price = history[-1]
        momentum = (new_price - old_price) / old_price if old_price > 0 else 0
        
        # Trade on strong momentum
        if abs(momentum) < self.momentum_threshold:
            return None
        
        # Buy if momentum is positive, short if negative
        trade_type = "buy_yes" if momentum > 0 else "buy_no"
        confidence = min(abs(momentum) * 10, 0.8)  # Scale confidence
        
        if confidence < self.min_confidence:
            return None
        
        position_size = 0.5  # Conservative sizing
        expected_profit = position_size * abs(momentum) * 0.5
        
        return Trade(
            trade_id=f"mom_{market.market_id}_{datetime.utcnow().timestamp()}",
            strategy=StrategyType.MOMENTUM,
            market_id=market.market_id,
            market_title=market.title,
            trade_type=trade_type,
            amount=position_size,
            price=market.yes_price if momentum > 0 else market.no_price,
            expected_profit=expected_profit,
            timestamp=datetime.utcnow(),
            notes=f"Momentum: {momentum:.2%}, Direction: {'UP' if momentum > 0 else 'DOWN'}"
        )


class MarketMakingStrategy(BaseStrategy):
    """Provide liquidity to earn fees."""
    
    def __init__(self, spread_target: float = 0.02, position_limit: float = 2.0):
        super().__init__("Market Making", min_confidence=0.7)
        self.spread_target = spread_target
        self.position_limit = position_limit
        self.positions: Dict[str, Dict[str, float]] = {}
    
    async def analyze(self, market: Market) -> Optional[Trade]:
        # Only trade markets with good liquidity
        if market.liquidity < 10000:
            return None
        
        # Calculate bid/ask spread
        mid_price = (market.yes_price + (1 - market.no_price)) / 2
        spread = abs(market.yes_price - (1 - market.no_price))
        
        # If spread is wide, provide liquidity
        if spread < self.spread_target:
            return None
        
        # Check position limits
        current_position = self.positions.get(market.market_id, {}).get('yes', 0)
        if abs(current_position) >= self.position_limit:
            return None
        
        position_size = min(0.5, self.position_limit - abs(current_position))
        
        # Expected profit from fees (assume 0.5% fee capture)
        expected_profit = position_size * 0.005
        
        return Trade(
            trade_id=f"mm_{market.market_id}_{datetime.utcnow().timestamp()}",
            strategy=StrategyType.MARKET_MAKING,
            market_id=market.market_id,
            market_title=market.title,
            trade_type="provide_liquidity",
            amount=position_size,
            price=mid_price,
            expected_profit=expected_profit,
            timestamp=datetime.utcnow(),
            notes=f"Spread: {spread:.4f}, Mid: ${mid_price:.4f}"
        )


class NewsDrivenStrategy(BaseStrategy):
    """Trade based on news/sentiment (placeholder for news integration)."""
    
    def __init__(self):
        super().__init__("News Driven", min_confidence=0.65)
        self.news_signals: Dict[str, float] = {}  # market_id -> sentiment score
    
    def update_news_signal(self, market_id: str, sentiment: float):
        """Update with news sentiment (-1 to 1)."""
        self.news_signals[market_id] = sentiment
    
    async def analyze(self, market: Market) -> Optional[Trade]:
        sentiment = self.news_signals.get(market.market_id, 0)
        
        if abs(sentiment) < 0.3:
            return None
        
        confidence = abs(sentiment)
        if confidence < self.min_confidence:
            return None
        
        trade_type = "buy_yes" if sentiment > 0 else "buy_no"
        position_size = 0.75
        expected_profit = position_size * abs(sentiment) * 0.3
        
        return Trade(
            trade_id=f"news_{market.market_id}_{datetime.utcnow().timestamp()}",
            strategy=StrategyType.NEWS_DRIVEN,
            market_id=market.market_id,
            market_title=market.title,
            trade_type=trade_type,
            amount=position_size,
            price=market.yes_price if sentiment > 0 else market.no_price,
            expected_profit=expected_profit,
            timestamp=datetime.utcnow(),
            notes=f"News sentiment: {sentiment:.2f}"
        )


class MultiStrategyTrader:
    """Run multiple strategies simultaneously."""
    
    def __init__(self, bankroll: float = 100.0, data_dir: Optional[Path] = None):
        self.bankroll = bankroll
        self.available_bankroll = bankroll
        self.data_dir = data_dir or Path(__file__).parent.parent.parent.parent / 'data' / 'polymarket'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize strategies
        self.strategies: List[BaseStrategy] = [
            ArbitrageStrategy(min_spread=0.005),
            MomentumStrategy(lookback_periods=3, momentum_threshold=0.03),
            MarketMakingStrategy(spread_target=0.015),
            NewsDrivenStrategy()
        ]
        
        self.trades: List[Trade] = []
        self.trades_file = self.data_dir / 'all_trades.jsonl'
        self.load_trades()
    
    def load_trades(self):
        """Load existing trades from file."""
        if self.trades_file.exists():
            with open(self.trades_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Convert back to Trade object
                        trade = Trade(
                            trade_id=data['trade_id'],
                            strategy=StrategyType(data['strategy']),
                            market_id=data['market_id'],
                            market_title=data['market_title'],
                            trade_type=data['trade_type'],
                            amount=data['amount'],
                            price=data['price'],
                            expected_profit=data['expected_profit'],
                            timestamp=datetime.fromisoformat(data['timestamp']),
                            status=data['status'],
                            actual_profit=data.get('actual_profit', 0),
                            notes=data.get('notes', '')
                        )
                        self.trades.append(trade)
                    except Exception:
                        continue
    
    def save_trade(self, trade: Trade):
        """Save a trade to file."""
        with open(self.trades_file, 'a') as f:
            f.write(json.dumps({
                'trade_id': trade.trade_id,
                'strategy': trade.strategy.value,
                'market_id': trade.market_id,
                'market_title': trade.market_title,
                'trade_type': trade.trade_type,
                'amount': trade.amount,
                'price': trade.price,
                'expected_profit': trade.expected_profit,
                'timestamp': trade.timestamp.isoformat(),
                'status': trade.status,
                'actual_profit': trade.actual_profit,
                'notes': trade.notes
            }) + '\n')
    
    async def run_strategies(self, markets: List[Market]) -> List[Trade]:
        """Run all strategies on all markets."""
        new_trades = []
        
        for market in markets:
            for strategy in self.strategies:
                try:
                    trade = await strategy.analyze(market)
                    if trade:
                        # Check bankroll
                        if trade.amount <= self.available_bankroll:
                            trade.status = "executed"
                            self.available_bankroll -= trade.amount
                            self.trades.append(trade)
                            new_trades.append(trade)
                            self.save_trade(trade)
                            strategy.trades.append(trade)
                            strategy.trade_count += 1
                            strategy.total_pnl += trade.expected_profit
                        else:
                            trade.status = "rejected"
                            trade.notes += " | Rejected: Insufficient bankroll"
                            self.save_trade(trade)
                except Exception as e:
                    print(f"Strategy {strategy.name} failed for {market.market_id}: {e}")
                    continue
        
        return new_trades
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive trading statistics."""
        total_pnl = sum(t.actual_profit for t in self.trades if t.status == 'settled')
        total_expected = sum(t.expected_profit for t in self.trades if t.status == 'executed')
        
        strategy_stats = {}
        for strategy in self.strategies:
            strategy_stats[strategy.name] = strategy.get_stats()
        
        return {
            'total_trades': len(self.trades),
            'executed_trades': len([t for t in self.trades if t.status == 'executed']),
            'total_pnl': total_pnl,
            'total_expected_pnl': total_expected,
            'bankroll': self.bankroll,
            'available_bankroll': self.available_bankroll,
            'strategy_stats': strategy_stats,
            'recent_trades': [
                {
                    'trade_id': t.trade_id,
                    'strategy': t.strategy.value,
                    'market_title': t.market_title[:50],
                    'trade_type': t.trade_type,
                    'amount': t.amount,
                    'expected_profit': t.expected_profit,
                    'timestamp': t.timestamp.isoformat(),
                    'status': t.status
                }
                for t in sorted(self.trades, key=lambda x: x.timestamp, reverse=True)[:10]
            ]
        }
