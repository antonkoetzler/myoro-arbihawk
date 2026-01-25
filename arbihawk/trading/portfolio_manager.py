"""
Portfolio manager for trading positions and P&L tracking.

Similar to VirtualBankroll pattern from betting system.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from data.database import Database
import config


class PortfolioManager:
    """
    Manages trading portfolio: cash balance, positions, P&L.
    
    Features:
    - Track cash balance
    - Track active positions (from positions table)
    - Calculate portfolio value (cash + positions at current prices)
    - Calculate P&L (realized + unrealized)
    - Position sizing strategies
    
    Example usage:
        manager = PortfolioManager(db)
        manager.initialize(starting_balance=10000)
        size = manager.calculate_position_size(signal, price)
    """
    
    # Position sizing strategies
    SIZING_FIXED = 'fixed'
    SIZING_PERCENTAGE = 'percentage'
    SIZING_RISK_BASED = 'risk_based'
    
    def __init__(self, db: Database):
        self.db = db
        
        # Load config
        trading_config = getattr(config, 'TRADING_CONFIG', {})
        portfolio_config = trading_config.get('portfolio', {})
        position_sizing_config = trading_config.get('position_sizing', {})
        
        # Portfolio settings
        self.starting_balance = portfolio_config.get('starting_balance', 10000.0)
        self.cash_reserve_ratio = portfolio_config.get('cash_reserve', 0.15)
        
        # Position sizing settings
        self.sizing_strategy = position_sizing_config.get('strategy', self.SIZING_RISK_BASED)
        self.risk_per_trade = position_sizing_config.get('risk_per_trade', 0.02)  # 2%
        self.max_position_size = position_sizing_config.get('max_position_size', 0.05)  # 5%
        self.max_positions = position_sizing_config.get('max_positions', 12)
        self.fixed_size = position_sizing_config.get('fixed_size', 500.0)  # For fixed strategy
        
        # Cache
        self._cash_balance: Optional[float] = None
        self._positions_cache: Optional[pd.DataFrame] = None
    
    def initialize(self, starting_balance: Optional[float] = None) -> None:
        """Initialize portfolio with starting balance."""
        balance = starting_balance or self.starting_balance
        
        # Check if portfolio already exists
        portfolio = self.db.get_portfolio(limit=1)
        
        if portfolio.empty:
            # Create initial portfolio record
            self.db.insert_portfolio({
                'timestamp': datetime.now().isoformat(),
                'cash_balance': balance,
                'total_value': balance,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0
            })
        
        self._cash_balance = None  # Reset cache
    
    def get_balance(self) -> float:
        """Get current cash balance."""
        if self._cash_balance is None:
            portfolio = self.db.get_portfolio(limit=1)
            if portfolio.empty:
                self.initialize()
                portfolio = self.db.get_portfolio(limit=1)
            
            if not portfolio.empty:
                self._cash_balance = float(portfolio.iloc[0]['cash_balance'])
            else:
                self._cash_balance = self.starting_balance
        
        return self._cash_balance
    
    def get_positions(self) -> pd.DataFrame:
        """Get active (open) positions."""
        return self.db.get_positions(status='open')
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get specific position by symbol."""
        positions = self.db.get_positions(symbol=symbol)
        
        if positions.empty:
            return None
        
        row = positions.iloc[0]
        
        # Map database fields to trading system fields
        entry_price = float(row.get('avg_entry_price', row.get('entry_price', 0)))
        
        return {
            'id': row['id'],
            'symbol': row['symbol'],
            'asset_type': row.get('asset_type', 'stock'),
            'strategy': row.get('strategy'),
            'direction': 'long',  # Default to long, we only track long positions currently
            'quantity': float(row['quantity']),
            'entry_price': entry_price,
            'current_price': float(row.get('current_price', entry_price)),
            'stop_loss': float(row['stop_loss']) if pd.notna(row.get('stop_loss')) else None,
            'take_profit': float(row['take_profit']) if pd.notna(row.get('take_profit')) else None,
            'unrealized_pnl': float(row.get('unrealized_pnl', 0)),
            'opened_at': row.get('timestamp', row.get('opened_at'))
        }
    
    def get_portfolio_value(self) -> float:
        """
        Get total portfolio value (cash + positions at current prices).
        """
        cash = self.get_balance()
        positions = self.get_positions()
        
        if positions.empty:
            return cash
        
        positions_value = 0.0
        for _, pos in positions.iterrows():
            quantity = float(pos['quantity'])
            current_price = float(pos.get('current_price', pos['entry_price']))
            direction = pos['direction']
            
            if direction == 'long':
                positions_value += quantity * current_price
            else:
                # For short positions, value is (2 * entry - current) * quantity
                entry_price = float(pos['entry_price'])
                positions_value += (2 * entry_price - current_price) * quantity
        
        return cash + positions_value
    
    def get_pnl(self) -> Dict[str, float]:
        """
        Get profit and loss (realized + unrealized).
        
        Returns:
            Dict with 'realized', 'unrealized', 'total' P&L
        """
        # Get realized P&L from closed trades
        trades = self.db.get_trades()
        realized_pnl = 0.0
        
        if not trades.empty:
            realized_pnl = trades['pnl'].sum() if 'pnl' in trades.columns else 0.0
        
        # Get unrealized P&L from open positions
        positions = self.get_positions()
        unrealized_pnl = 0.0
        
        if not positions.empty:
            for _, pos in positions.iterrows():
                quantity = float(pos['quantity'])
                entry_price = float(pos['entry_price'])
                current_price = float(pos.get('current_price', entry_price))
                direction = pos['direction']
                
                if direction == 'long':
                    unrealized_pnl += (current_price - entry_price) * quantity
                else:
                    unrealized_pnl += (entry_price - current_price) * quantity
        
        return {
            'realized': float(realized_pnl),
            'unrealized': float(unrealized_pnl),
            'total': float(realized_pnl + unrealized_pnl)
        }
    
    def get_available_cash(self) -> float:
        """
        Get available cash for trading (excluding reserve).
        """
        total_cash = self.get_balance()
        portfolio_value = self.get_portfolio_value()
        
        # Reserve is based on total portfolio value
        reserve = portfolio_value * self.cash_reserve_ratio
        
        return max(0, total_cash - reserve)
    
    def calculate_position_size(self, signal: Dict[str, Any], 
                                 current_price: float) -> float:
        """
        Calculate position size based on strategy and constraints.
        
        Args:
            signal: Signal dict with 'stop_loss', 'entry_price', etc.
            current_price: Current market price
            
        Returns:
            Quantity to buy/sell
        """
        portfolio_value = self.get_portfolio_value()
        available_cash = self.get_available_cash()
        
        # Check position count limit
        open_positions = len(self.get_positions())
        if open_positions >= self.max_positions:
            return 0.0
        
        # Calculate max position value (as percentage of portfolio)
        max_position_value = portfolio_value * self.max_position_size
        
        if self.sizing_strategy == self.SIZING_FIXED:
            # Fixed dollar amount per trade
            position_value = min(self.fixed_size, max_position_value, available_cash)
            
        elif self.sizing_strategy == self.SIZING_PERCENTAGE:
            # Percentage of portfolio
            percentage = self.risk_per_trade  # Reuse this config
            position_value = min(portfolio_value * percentage, max_position_value, available_cash)
            
        elif self.sizing_strategy == self.SIZING_RISK_BASED:
            # Risk-based: Size based on stop-loss distance
            entry_price = signal.get('entry_price', current_price)
            stop_loss = signal.get('stop_loss')
            
            if stop_loss is None:
                # Fall back to percentage-based
                position_value = min(portfolio_value * self.risk_per_trade, 
                                    max_position_value, available_cash)
            else:
                # Calculate position size based on risk
                risk_per_share = abs(entry_price - stop_loss)
                risk_amount = portfolio_value * self.risk_per_trade
                
                if risk_per_share > 0:
                    max_shares = risk_amount / risk_per_share
                    position_value = min(max_shares * current_price, 
                                        max_position_value, available_cash)
                else:
                    position_value = min(portfolio_value * self.risk_per_trade,
                                        max_position_value, available_cash)
        else:
            # Default to percentage
            position_value = min(portfolio_value * self.risk_per_trade,
                                max_position_value, available_cash)
        
        if position_value <= 0 or current_price <= 0:
            return 0.0
        
        # Calculate quantity
        quantity = position_value / current_price
        
        return quantity
    
    def can_open_position(self, symbol: str, quantity: float, 
                          price: float) -> tuple[bool, str]:
        """
        Check if position can be opened.
        
        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        # Check if already have position in this symbol
        existing = self.get_position(symbol)
        if existing is not None:
            return False, f"Already have open position in {symbol}"
        
        # Check position count
        open_positions = len(self.get_positions())
        if open_positions >= self.max_positions:
            return False, f"Maximum positions ({self.max_positions}) reached"
        
        # Check funds
        required_funds = quantity * price
        available = self.get_available_cash()
        
        if required_funds > available:
            return False, f"Insufficient funds: need ${required_funds:.2f}, have ${available:.2f}"
        
        # Check max position size
        portfolio_value = self.get_portfolio_value()
        max_allowed = portfolio_value * self.max_position_size
        
        if required_funds > max_allowed:
            return False, f"Position too large: ${required_funds:.2f} exceeds max ${max_allowed:.2f}"
        
        return True, "OK"
    
    def update_cash_balance(self, delta: float) -> None:
        """
        Update cash balance by delta amount.
        
        Args:
            delta: Amount to add (positive) or subtract (negative)
        """
        current = self.get_balance()
        new_balance = current + delta
        
        if new_balance < 0:
            raise ValueError(f"Cannot reduce balance below 0: current={current}, delta={delta}")
        
        # Update in database
        self.db.insert_portfolio({
            'timestamp': datetime.now().isoformat(),
            'cash_balance': new_balance,
            'total_value': self.get_portfolio_value() + delta,  # Approximate
            'realized_pnl': self.get_pnl()['realized'],
            'unrealized_pnl': self.get_pnl()['unrealized']
        })
        
        self._cash_balance = new_balance
    
    def record_portfolio_snapshot(self) -> int:
        """
        Record current portfolio state as a snapshot.
        
        Returns:
            Record ID
        """
        pnl = self.get_pnl()
        
        return self.db.insert_portfolio({
            'timestamp': datetime.now().isoformat(),
            'cash_balance': self.get_balance(),
            'total_value': self.get_portfolio_value(),
            'realized_pnl': pnl['realized'],
            'unrealized_pnl': pnl['unrealized']
        })
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate portfolio performance metrics.
        
        Returns:
            Dict with ROI, win rate, Sharpe ratio, etc.
        """
        trades = self.db.get_trades()
        
        if trades.empty:
            return {
                'roi': 0.0,
                'total_return': 0.0,
                'win_rate': 0.0,
                'profit': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }
        
        # Calculate metrics
        total_trades = len(trades)
        
        if 'pnl' in trades.columns:
            pnl_values = trades['pnl'].fillna(0)
            winning = trades[trades['pnl'] > 0]
            losing = trades[trades['pnl'] < 0]
            
            winning_trades = len(winning)
            losing_trades = len(losing)
            profit = pnl_values.sum()
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_win = winning['pnl'].mean() if len(winning) > 0 else 0
            avg_loss = losing['pnl'].mean() if len(losing) > 0 else 0
            
            # Simple Sharpe approximation (returns / std of returns)
            returns = pnl_values / self.starting_balance
            sharpe = returns.mean() / returns.std() if returns.std() > 0 else 0
            
            # Calculate drawdown from portfolio history
            portfolio_history = self.db.get_portfolio()
            max_drawdown = 0.0
            
            if not portfolio_history.empty and 'total_value' in portfolio_history.columns:
                values = portfolio_history['total_value'].values
                peak = values[0]
                for value in values:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak if peak > 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)
        else:
            profit = 0
            winning_trades = 0
            losing_trades = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            sharpe = 0
            max_drawdown = 0
        
        # ROI
        current_value = self.get_portfolio_value()
        total_return = current_value - self.starting_balance
        roi = total_return / self.starting_balance if self.starting_balance > 0 else 0
        
        return {
            'roi': roi,
            'total_return': total_return,
            'win_rate': win_rate,
            'profit': float(profit),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': max_drawdown,
            'current_value': current_value,
            'starting_balance': self.starting_balance
        }
    
    def get_performance_by_strategy(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics broken down by strategy.
        """
        trades = self.db.get_trades()
        
        if trades.empty or 'strategy' not in trades.columns:
            return {}
        
        strategies = trades['strategy'].unique()
        results = {}
        
        for strategy in strategies:
            strategy_trades = trades[trades['strategy'] == strategy]
            
            if 'pnl' in strategy_trades.columns:
                pnl_values = strategy_trades['pnl'].fillna(0)
                winning = strategy_trades[strategy_trades['pnl'] > 0]
                losing = strategy_trades[strategy_trades['pnl'] < 0]
                
                results[strategy] = {
                    'total_trades': len(strategy_trades),
                    'winning_trades': len(winning),
                    'losing_trades': len(losing),
                    'profit': float(pnl_values.sum()),
                    'win_rate': len(winning) / len(strategy_trades) if len(strategy_trades) > 0 else 0,
                    'avg_pnl': float(pnl_values.mean())
                }
            else:
                results[strategy] = {
                    'total_trades': len(strategy_trades),
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'profit': 0,
                    'win_rate': 0,
                    'avg_pnl': 0
                }
        
        return results
    
    def invalidate_cache(self) -> None:
        """Clear cached values."""
        self._cash_balance = None
        self._positions_cache = None
