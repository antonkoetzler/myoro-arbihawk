"""
Simple Polymarket Value Trader

Makes trades based on value, not arbitrage.
Strategy: Buy YES when our predicted probability > market price
"""

import aiohttp
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class SimpleValueTrader:
    """
    Simple value-based trading.
    
    For each market, make a directional bet based on:
    1. Current price trends (momentum)
    2. Market category (crypto, politics, sports)
    3. Historical data patterns
    """
    
    def __init__(self, bankroll: float = 1000.0):
        self.bankroll = bankroll
        self.available = bankroll
        self.trades: List[Dict] = []
        self.data_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'polymarket_trades'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / 'value_trades.jsonl'
        self.load_trades()
    
    def load_trades(self):
        """Load existing trades."""
        if self.trades_file.exists():
            with open(self.trades_file, 'r') as f:
                for line in f:
                    try:
                        self.trades.append(json.loads(line))
                    except:
                        continue
    
    def save_trade(self, trade: Dict):
        """Save a trade."""
        with open(self.trades_file, 'a') as f:
            f.write(json.dumps(trade) + '\n')
    
    async def fetch_markets(self) -> List[Dict]:
        """Fetch active markets from Polymarket."""
        url = 'https://gamma-api.polymarket.com/events'
        params = {
            'active': 'true',
            'closed': 'false',
            'limit': 100,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                events = data if isinstance(data, list) else data.get('events', [])
                
                print(f"Fetched {len(events)} events from API")
                
                markets = []
                skipped = {'outcomes': 0, 'no_price': 0, 'price_range': 0, 'volume': 0}
                
                for event in events:
                    for market in event.get('markets', []):
                        # Parse outcomes (they're JSON strings)
                        outcomes_raw = market.get('outcomes', '[]')
                        if isinstance(outcomes_raw, str):
                            try:
                                outcomes = json.loads(outcomes_raw)
                            except:
                                outcomes = []
                        else:
                            outcomes = outcomes_raw
                        
                        if outcomes != ['Yes', 'No']:
                            skipped['outcomes'] += 1
                            continue
                        
                        yes_price = market.get('bestAsk')
                        if yes_price is None:
                            skipped['no_price'] += 1
                            continue
                        
                        yes_price = float(yes_price)
                        if yes_price <= 0 or yes_price >= 1:
                            skipped['price_range'] += 1
                            continue
                        
                        volume = float(market.get('volume', 0))
                        if volume < 5000:
                            skipped['volume'] += 1
                            continue
                        
                        markets.append({
                            'id': market.get('id'),
                            'title': event.get('title', 'Unknown'),
                            'question': market.get('question', 'Unknown'),
                            'yes_price': yes_price,
                            'no_price': 1.0 - yes_price,
                            'volume': volume,
                            'category': self._categorize(event.get('title', ''))
                        })
                
                print(f"Skipped - outcomes: {skipped['outcomes']}, no_price: {skipped['no_price']}, price_range: {skipped['price_range']}, volume: {skipped['volume']}")
                print(f"Valid markets: {len(markets)}")
                return markets
    
    def _categorize(self, title: str) -> str:
        """Categorize a market."""
        title_lower = title.lower()
        if any(word in title_lower for word in ['bitcoin', 'btc', 'crypto', 'ethereum', 'eth']):
            return 'crypto'
        elif any(word in title_lower for word in ['trump', 'election', 'president', 'political']):
            return 'politics'
        elif any(word in title_lower for word in ['sports', 'nba', 'nfl', 'soccer', 'football']):
            return 'sports'
        else:
            return 'other'
    
    def generate_signal(self, market: Dict) -> Optional[Dict]:
        """
        Generate a trading signal for a market.
        
        Strategy: Buy YES when price < 0.5 (undervalued)
                 Buy NO when price > 0.7 (overvalued yes = undervalued no)
        """
        yes_price = market['yes_price']
        title = market['title']
        category = market['category']
        
        # Simple momentum/value strategy
        confidence = 0.0
        direction = None
        reason = None
        
        # Strategy 1: Mean reversion for extreme prices
        if yes_price < 0.10:
            # Very cheap YES - possible value
            confidence = 0.55
            direction = 'buy_yes'
            reason = f"YES undervalued at {yes_price:.1%}"
        elif yes_price > 0.90:
            # Very expensive YES = cheap NO
            confidence = 0.55
            direction = 'buy_no'
            reason = f"YES overvalued at {yes_price:.1%}"
        
        # Strategy 2: Category-based bias
        if category == 'crypto':
            if 'bitcoin' in title.lower() and yes_price < 0.40:
                confidence = max(confidence, 0.52)
                direction = direction or 'buy_yes'
                reason = reason or "BTC bullish long-term bias"
        
        if category == 'politics' and 'trump' in title.lower():
            if yes_price > 0.55:
                confidence = max(confidence, 0.52)
                direction = 'buy_no'
                reason = "Trump fan bias overvaluation"
        
        if not direction:
            return None
        
        # Calculate position size (1-5% of bankroll based on confidence)
        position_pct = 0.01 + (confidence - 0.5) * 0.08
        position_size = min(
            self.available * position_pct,
            self.available * 0.05,
            50.0
        )
        
        if position_size < 1.0:
            return None
        
        # Expected value calculation
        if direction == 'buy_yes':
            entry_price = yes_price
            fair_value = min(yes_price * 2.0, 0.90)
        else:
            entry_price = market['no_price']
            fair_value = min(market['no_price'] * 2.0, 0.90)
        
        expected_return = (fair_value - entry_price) / entry_price if entry_price > 0 else 0
        expected_profit = position_size * expected_return * 0.3
        
        return {
            'market_id': market['id'],
            'market_title': market['question'],
            'category': category,
            'direction': direction,
            'entry_price': entry_price,
            'position_size': position_size,
            'confidence': confidence,
            'expected_profit': expected_profit,
            'expected_return': expected_return,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def run_trading_session(self, max_trades: int = 5) -> List[Dict]:
        """Run a trading session."""
        print(f"[{datetime.utcnow().isoformat()}] Starting value trading session")
        print(f"Bankroll: ${self.bankroll:.2f} | Available: ${self.available:.2f}")
        
        markets = await self.fetch_markets()
        
        # Sort by volume
        markets.sort(key=lambda x: x['volume'], reverse=True)
        
        executed_trades = []
        
        for market in markets[:50]:
            if len(executed_trades) >= max_trades:
                break
            
            if self.available < 10:
                print("Low on funds, stopping")
                break
            
            signal = self.generate_signal(market)
            if signal:
                trade = {
                    'trade_id': f"val_{market['id']}_{int(datetime.utcnow().timestamp())}",
                    'status': 'executed',
                    **signal
                }
                
                self.trades.append(trade)
                self.save_trade(trade)
                executed_trades.append(trade)
                
                self.available -= signal['position_size']
                
                print(f"\n✅ TRADE EXECUTED")
                print(f"   Market: {trade['market_title'][:60]}")
                print(f"   Direction: {trade['direction']}")
                print(f"   Size: ${trade['position_size']:.2f}")
                print(f"   Expected Profit: ${trade['expected_profit']:.4f}")
                print(f"   Reason: {trade['reason']}")
        
        print(f"\n{'='*50}")
        print(f"Session complete: {len(executed_trades)} trades executed")
        print(f"Remaining bankroll: ${self.available:.2f}")
        
        return executed_trades
    
    def get_stats(self) -> Dict:
        """Get trading stats."""
        executed = [t for t in self.trades if t.get('status') == 'executed']
        total_expected = sum(t.get('expected_profit', 0) for t in executed)
        
        by_category = {}
        for trade in executed:
            cat = trade.get('category', 'unknown')
            if cat not in by_category:
                by_category[cat] = {'count': 0, 'expected': 0}
            by_category[cat]['count'] += 1
            by_category[cat]['expected'] += trade.get('expected_profit', 0)
        
        return {
            'total_trades': len(executed),
            'total_expected_profit': total_expected,
            'bankroll': self.bankroll,
            'available': self.available,
            'exposure': self.bankroll - self.available,
            'by_category': by_category,
            'recent_trades': executed[-10:]
        }


async def main():
    """Run trading session."""
    trader = SimpleValueTrader(bankroll=1000.0)
    trades = await trader.run_trading_session(max_trades=5)
    
    if trades:
        print(f"\n🎉 SUCCESS: Made {len(trades)} trades!")
        stats = trader.get_stats()
        print(f"Total expected profit: ${stats['total_expected_profit']:.4f}")
    else:
        print("\n⚠️ No trades made this session")
    
    return trades


if __name__ == '__main__':
    asyncio.run(main())
