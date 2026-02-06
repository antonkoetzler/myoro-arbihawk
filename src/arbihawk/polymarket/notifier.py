#!/usr/bin/env python3
"""
Notification wrapper for WhatsApp integration.
"""

import sys
from pathlib import Path

def notify_trade(opp):
    """Send WhatsApp notification for trade."""
    # This will be called by scan runners
    # OpenClaw handles the actual WhatsApp sending via message tool
    msg = f"""💰 *POLYMARKET ARBITRAGE*

Market: {opp['market_title'][:50]}...
YES: ${opp['yes_price']:.3f} | NO: ${opp['no_price']:.3f}
Spread: {opp['spread']:.4f} ({opp['expected_profit_pct']:.1f}%)
Position: $1.00 (paper trade)

⏰ {opp.get('timestamp', 'now')}"""
    
    print(msg)
    return msg


def notify_summary(daily_pnl, trade_count):
    """Send daily summary."""
    msg = f"""📊 *DAILY SUMMARY - Polymarket*

💰 PnL: ${daily_pnl:.4f}
🔄 Trades: {trade_count}
📈 Win Rate: 100% (arbitrage)

Paper trading mode active.
Reply 'REAL' to enable live trading."""
    
    print(msg)
    return msg