"""
Trading service that orchestrates the complete trading workflow.

Coordinates signal generation, execution, and position management.
"""

import pandas as pd
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path

from data.database import Database
from data.stock_features import StockFeatureEngineer
from models.trading_predictor import TradingPredictor, TradingModelManager
from engine.trade_signal import TradeSignalEngine
from .portfolio_manager import PortfolioManager
from .execution import PaperTradingExecutor
import config


class TradingService:
    """
    Main service for trading operations.
    
    Orchestrates:
    - Signal generation from all strategies
    - Order execution via paper trading
    - Position management and updates
    - Performance tracking
    
    Example usage:
        service = TradingService(db)
        results = service.run_trading_cycle(limit_per_strategy=5)
    """
    
    def __init__(self, db: Database, log_callback: Optional[Callable[[str, str], None]] = None):
        self.db = db
        self.log_callback = log_callback
        
        # Initialize components
        self.portfolio = PortfolioManager(db)
        self.executor = PaperTradingExecutor(db, self.portfolio)
        self.model_manager = TradingModelManager(db)
        self.feature_engineer = StockFeatureEngineer(db)
        
        # Load models
        self._momentum_predictor: Optional[TradingPredictor] = None
        self._swing_predictor: Optional[TradingPredictor] = None
        self._volatility_predictor: Optional[TradingPredictor] = None
        
        self._load_models()
        
        # Initialize signal engine
        self.signal_engine = TradeSignalEngine(
            db=db,
            momentum_predictor=self._momentum_predictor,
            swing_predictor=self._swing_predictor,
            volatility_predictor=self._volatility_predictor
        )
        
        # Trading config
        trading_config = getattr(config, 'TRADING_CONFIG', {})
        self.enabled = trading_config.get('enabled', False)
    
    def _log(self, level: str, message: str) -> None:
        """Log a message."""
        if self.log_callback:
            self.log_callback(level, f"[TRADING] {message}")
    
    def _load_models(self) -> None:
        """Load trading models."""
        self._momentum_predictor = self.model_manager.get_model('momentum')
        self._swing_predictor = self.model_manager.get_model('swing')
        self._volatility_predictor = self.model_manager.get_model('volatility')
    
    def reload_models(self) -> None:
        """Reload models from disk."""
        self.model_manager.invalidate_cache()
        self._load_models()
        
        # Update signal engine with new models
        self.signal_engine.momentum_predictor = self._momentum_predictor
        self.signal_engine.swing_predictor = self._swing_predictor
        self.signal_engine.volatility_predictor = self._volatility_predictor
    
    def get_current_prices(self) -> Dict[str, float]:
        """Get current prices for all watchlist symbols."""
        prices = {}
        
        trading_config = getattr(config, 'TRADING_CONFIG', {})
        watchlist = trading_config.get('watchlist', {})
        
        all_symbols = watchlist.get('stocks', []) + watchlist.get('crypto', [])
        
        for symbol in all_symbols:
            # Get latest price from database
            price_df = self.db.get_price_history(symbol=symbol, limit=1)
            
            if not price_df.empty:
                prices[symbol] = float(price_df.iloc[0]['close'])
        
        return prices
    
    def find_signals(self, limit_per_strategy: int = 5) -> pd.DataFrame:
        """
        Find trading signals from all strategies.
        
        Args:
            limit_per_strategy: Maximum signals per strategy
            
        Returns:
            DataFrame of signals
        """
        return self.signal_engine.find_all_signals(limit_per_strategy)
    
    def execute_signals(self, signals: pd.DataFrame, 
                        max_executions: int = 3) -> List[Dict[str, Any]]:
        """
        Execute trading signals.
        
        Args:
            signals: DataFrame of signals to execute
            max_executions: Maximum number of trades to execute
            
        Returns:
            List of execution results
        """
        if signals.empty:
            return []
        
        results = []
        executed = 0
        
        for _, signal in signals.iterrows():
            if executed >= max_executions:
                break
            
            symbol = signal['symbol']
            direction = signal['direction']
            entry_price = signal['entry_price']
            stop_loss = signal.get('stop_loss')
            take_profit = signal.get('take_profit')
            asset_type = signal.get('asset_type', 'stock')
            strategy = signal.get('strategy', 'manual')
            
            # Calculate position size
            quantity = self.portfolio.calculate_position_size(
                signal.to_dict(), entry_price
            )
            
            if quantity <= 0:
                self._log("warning", f"Skipping {symbol}: position size is 0")
                continue
            
            # Execute order
            result = self.executor.execute_market_order(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                price=entry_price,
                asset_type=asset_type,
                strategy=strategy,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            results.append(result)
            
            if result['success']:
                executed += 1
                self._log("info", 
                    f"Opened {direction} position: {symbol} x{quantity:.4f} @ ${entry_price:.2f}")
            else:
                self._log("warning", f"Failed to open {symbol}: {result.get('reason', 'Unknown')}")
        
        return results
    
    def update_positions(self) -> Dict[str, Any]:
        """
        Update all open positions with current prices and check stop-loss/take-profit.
        
        Returns:
            Dict with update results
        """
        current_prices = self.get_current_prices()
        
        # Update position prices
        updated = self.executor.update_position_prices(current_prices)
        
        # Check stop-loss/take-profit
        closed = self.executor.check_stop_loss_take_profit(current_prices)
        
        # Log closed positions
        for close_result in closed:
            if close_result['success']:
                symbol = close_result['symbol']
                pnl = close_result.get('pnl', 0)
                reason = close_result.get('reason', 'unknown')
                self._log("info", f"Closed {symbol}: {reason}, P&L: ${pnl:.2f}")
        
        return {
            'positions_updated': updated,
            'positions_closed': len(closed),
            'close_results': closed,
            'current_prices': current_prices
        }
    
    def run_trading_cycle(self, limit_per_strategy: int = 5,
                          max_executions: int = 3) -> Dict[str, Any]:
        """
        Run a complete trading cycle.
        
        Steps:
        1. Update existing positions
        2. Find new signals
        3. Execute top signals
        4. Record portfolio snapshot
        
        Args:
            limit_per_strategy: Max signals per strategy
            max_executions: Max new positions to open
            
        Returns:
            Dict with cycle results
        """
        self._log("info", "Starting trading cycle...")
        
        if not self.enabled:
            self._log("warning", "Trading is disabled in config")
            return {
                'success': False,
                'reason': 'Trading disabled',
                'timestamp': datetime.now().isoformat()
            }
        
        results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'update_results': None,
            'signals_found': 0,
            'signals_executed': 0,
            'execution_results': [],
            'portfolio_value': 0,
            'pnl': {}
        }
        
        try:
            # Step 1: Update existing positions
            self._log("info", "Updating positions...")
            update_results = self.update_positions()
            results['update_results'] = update_results
            
            # Step 2: Find signals
            self._log("info", "Finding signals...")
            signals = self.find_signals(limit_per_strategy)
            results['signals_found'] = len(signals)
            
            if not signals.empty:
                self._log("info", f"Found {len(signals)} signals")
                
                # Step 3: Execute signals
                self._log("info", "Executing signals...")
                execution_results = self.execute_signals(signals, max_executions)
                results['execution_results'] = execution_results
                results['signals_executed'] = sum(1 for r in execution_results if r.get('success'))
            else:
                self._log("info", "No signals found")
            
            # Step 4: Record portfolio snapshot
            self.portfolio.record_portfolio_snapshot()
            
            # Get current state
            results['portfolio_value'] = self.portfolio.get_portfolio_value()
            results['pnl'] = self.portfolio.get_pnl()
            
            self._log("success", 
                f"Trading cycle complete: {results['signals_executed']} trades, "
                f"Portfolio: ${results['portfolio_value']:.2f}")
            
        except Exception as e:
            self._log("error", f"Trading cycle error: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary."""
        positions = self.portfolio.get_positions()
        pnl = self.portfolio.get_pnl()
        
        return {
            'cash_balance': self.portfolio.get_balance(),
            'portfolio_value': self.portfolio.get_portfolio_value(),
            'available_cash': self.portfolio.get_available_cash(),
            'positions_count': len(positions),
            'realized_pnl': pnl['realized'],
            'unrealized_pnl': pnl['unrealized'],
            'total_pnl': pnl['total']
        }
    
    def get_positions_detail(self) -> List[Dict[str, Any]]:
        """Get detailed position information."""
        positions = self.portfolio.get_positions()
        
        if positions.empty:
            return []
        
        result = []
        for _, pos in positions.iterrows():
            entry_price = float(pos['entry_price'])
            current_price = float(pos.get('current_price', entry_price))
            quantity = float(pos['quantity'])
            direction = pos['direction']
            
            if direction == 'long':
                unrealized_pnl = (current_price - entry_price) * quantity
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                unrealized_pnl = (entry_price - current_price) * quantity
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            result.append({
                'id': pos['id'],
                'symbol': pos['symbol'],
                'asset_type': pos.get('asset_type', 'stock'),
                'strategy': pos.get('strategy', 'manual'),
                'direction': direction,
                'quantity': quantity,
                'entry_price': entry_price,
                'current_price': current_price,
                'unrealized_pnl': unrealized_pnl,
                'pnl_pct': pnl_pct,
                'stop_loss': float(pos['stop_loss']) if pd.notna(pos.get('stop_loss')) else None,
                'take_profit': float(pos['take_profit']) if pd.notna(pos.get('take_profit')) else None,
                'opened_at': pos['opened_at']
            })
        
        return result
    
    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trade history."""
        trades = self.db.get_trades(limit=limit)
        
        if trades.empty:
            return []
        
        result = []
        for _, trade in trades.iterrows():
            result.append({
                'id': trade['id'],
                'symbol': trade['symbol'],
                'asset_type': trade.get('asset_type', 'stock'),
                'strategy': trade.get('strategy', 'manual'),
                'direction': trade['direction'],
                'order_type': trade.get('order_type', 'market'),
                'quantity': float(trade['quantity']),
                'price': float(trade['price']),
                'pnl': float(trade['pnl']) if pd.notna(trade.get('pnl')) else None,
                'timestamp': trade['timestamp']
            })
        
        return result
    
    def get_performance(self) -> Dict[str, Any]:
        """Get overall performance metrics."""
        return self.portfolio.get_performance_metrics()
    
    def get_performance_by_strategy(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics by strategy."""
        return self.portfolio.get_performance_by_strategy()
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of trading models."""
        return self.model_manager.get_model_status()
    
    def get_current_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get current trading signals without executing.
        
        Returns:
            List of signal dicts
        """
        signals = self.find_signals(limit_per_strategy=limit)
        
        if signals.empty:
            return []
        
        return signals.head(limit).to_dict('records')
    
    def close_position_manual(self, symbol: str) -> Dict[str, Any]:
        """
        Manually close a position.
        
        Args:
            symbol: Symbol to close
            
        Returns:
            Close result
        """
        current_prices = self.get_current_prices()
        
        if symbol not in current_prices:
            return {
                'success': False,
                'reason': f'No current price for {symbol}'
            }
        
        result = self.executor.close_position(symbol, current_prices[symbol], 'manual')
        
        if result['success']:
            self._log("info", f"Manually closed {symbol}: P&L ${result.get('pnl', 0):.2f}")
        
        return result
    
    def initialize_portfolio(self, starting_balance: Optional[float] = None) -> None:
        """Initialize portfolio with starting balance."""
        self.portfolio.initialize(starting_balance)
        self._log("info", f"Portfolio initialized with ${self.portfolio.starting_balance:.2f}")
