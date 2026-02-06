"""
Paper Trader for Polymarket Arbitrage

Logs trades without execution. For real trading, integrate Gamma SDK.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from dataclasses import asdict

from .strategies import Trade as ArbitrageOpportunity


class PaperTrader:
    """Simulate trades and log results."""
    
    def __init__(self, bankroll: float = 10.0, data_dir: str = None):
        self.bankroll = bankroll
        self.daily_pnl = 0.0
        self.trade_count = 0
        
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'polymarket'
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / 'trades.jsonl'
    
    def execute_arbitrage(self, opp: ArbitrageOpportunity) -> Dict:
        """Simulate executing an arbitrage trade."""
        # Calculate optimal position size (10% of available liquidity, max $1)
        max_position = min(opp.liquidity * 0.1, self.bankroll * 0.3, 1.0)
        
        expected_profit = max_position * opp.spread
        
        trade_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'arbitrage',
            'market_id': opp.market_id,
            'market_title': opp.market_title,
            'yes_price': opp.yes_price,
            'no_price': opp.no_price,
            'combined_price': opp.combined_price,
            'spread': opp.spread,
            'position_size': max_position,
            'expected_profit': expected_profit,
            'status': 'paper_trade'
        }
        
        # Log to file
        with open(self.trades_file, 'a') as f:
            f.write(json.dumps(trade_record) + '\n')
        
        self.daily_pnl += expected_profit
        self.trade_count += 1
        
        return trade_record
    
    def scan_and_trade(self, opportunities: List[ArbitrageOpportunity]) -> List[Dict]:
        """Execute all opportunities."""
        executed = []
        for opp in opportunities:
            trade = self.execute_arbitrage(opp)
            executed.append(trade)
        return executed
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'bankroll': self.bankroll,
            'daily_pnl': self.daily_pnl,
            'trade_count': self.trade_count,
            'timestamp': datetime.utcnow().isoformat()
        }
