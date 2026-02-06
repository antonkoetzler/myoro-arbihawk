#!/usr/bin/env python3
"""
Enhanced Polymarket Trading Runner

Runs multiple strategies simultaneously and logs results.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arbihawk.polymarket import PolymarketScanner, MultiStrategyTrader


async def run_trading_session(bankroll: float = 100.0, max_trades: int = 10):
    """
    Run a trading session with multiple strategies.
    
    Args:
        bankroll: Starting bankroll for paper trading
        max_trades: Maximum trades to execute per session
    """
    print(f"[{datetime.utcnow().isoformat()}] Starting Polymarket trading session")
    print(f"Bankroll: ${bankroll:.2f}")
    
    # Initialize scanner and trader
    async with PolymarketScanner(min_liquidity=1000) as scanner:
        trader = MultiStrategyTrader(bankroll=bankroll)
        
        # Scan markets
        print("Scanning markets...")
        markets = await scanner.scan(limit=100)
        print(f"Found {len(markets)} active markets")
        
        if not markets:
            print("No markets found. Exiting.")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'markets_scanned': 0,
                'trades_executed': 0,
                'status': 'no_markets'
            }
        
        # Run strategies on markets
        print("Running strategies...")
        trades = await trader.run_strategies(markets)
        
        # Limit trades if needed
        if len(trades) > max_trades:
            print(f"Limiting to {max_trades} trades (found {len(trades)})")
            trades = trades[:max_trades]
        
        # Print results
        stats = trader.get_stats()
        
        print(f"\n{'='*50}")
        print(f"TRADING SESSION RESULTS")
        print(f"{'='*50}")
        print(f"Markets scanned: {len(markets)}")
        print(f"Trades executed: {len(trades)}")
        print(f"Total trades (all time): {stats['total_trades']}")
        print(f"Expected PnL: ${stats['total_expected_pnl']:.4f}")
        print(f"Available bankroll: ${stats['available_bankroll']:.2f}")
        print(f"\nStrategy Performance:")
        for name, strat_stats in stats['strategy_stats'].items():
            print(f"  {name}: {strat_stats['trade_count']} trades, ${strat_stats['total_pnl']:.4f} PnL")
        
        if trades:
            print(f"\nNew Trades:")
            for trade in trades:
                print(f"  [{trade.strategy.value}] {trade.market_title[:40]}: ${trade.amount:.2f} -> ${trade.expected_profit:.4f}")
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'markets_scanned': len(markets),
            'trades_executed': len(trades),
            'total_trades': stats['total_trades'],
            'expected_pnl': stats['total_expected_pnl'],
            'available_bankroll': stats['available_bankroll'],
            'strategy_stats': stats['strategy_stats'],
            'recent_trades': stats['recent_trades'],
            'status': 'success' if trades else 'no_trades'
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Polymarket trading strategies')
    parser.add_argument('--bankroll', type=float, default=100.0, help='Starting bankroll')
    parser.add_argument('--max-trades', type=int, default=10, help='Max trades per session')
    parser.add_argument('--json', action='store_true', help='Output JSON results')
    
    args = parser.parse_args()
    
    results = asyncio.run(run_trading_session(
        bankroll=args.bankroll,
        max_trades=args.max_trades
    ))
    
    if args.json:
        print(json.dumps(results, indent=2))
    
    # Exit with 0 always (cron-friendly)
    sys.exit(0)


if __name__ == '__main__':
    main()
