"""
Paper trading executor for simulated order execution.

Handles market orders, limit orders, stop-loss, and take-profit orders.
"""

import random
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from data.database import Database


class OrderType(Enum):
    MARKET = 'market'
    LIMIT = 'limit'
    STOP_LOSS = 'stop_loss'
    TAKE_PROFIT = 'take_profit'


class OrderStatus(Enum):
    PENDING = 'pending'
    FILLED = 'filled'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'


class PaperTradingExecutor:
    """
    Executes paper trades with realistic simulation.
    
    Features:
    - Market orders: Immediate fill at current price + slippage
    - Limit orders: Fill if price reached
    - Stop-loss orders: Fill if price drops below threshold
    - Take-profit orders: Fill if price rises above threshold
    - Slippage simulation
    - Partial fills for large orders (optional)
    
    Example usage:
        executor = PaperTradingExecutor(db, portfolio_manager)
        result = executor.execute_market_order('AAPL', 'long', 10, 150.00)
    """
    
    def __init__(self, db: Database, portfolio_manager):
        self.db = db
        self.portfolio = portfolio_manager
        
        # Execution simulation settings
        self.slippage_min = 0.001  # 0.1%
        self.slippage_max = 0.005  # 0.5%
        self.enable_slippage = True
        
        # Pending orders (in-memory for simplicity)
        self._pending_orders: List[Dict[str, Any]] = []
    
    def _apply_slippage(self, price: float, direction: str, 
                         order_type: OrderType) -> float:
        """
        Apply slippage to price.
        
        Args:
            price: Base price
            direction: 'long' or 'short'
            order_type: Type of order
            
        Returns:
            Price with slippage applied
        """
        if not self.enable_slippage:
            return price
        
        # Market orders have higher slippage
        if order_type == OrderType.MARKET:
            slippage_pct = random.uniform(self.slippage_min, self.slippage_max)
        else:
            slippage_pct = random.uniform(self.slippage_min / 2, self.slippage_max / 2)
        
        # Slippage direction: worse for the trader
        if direction == 'long':
            # Buying: price goes up
            return price * (1 + slippage_pct)
        else:
            # Selling/shorting: price goes down
            return price * (1 - slippage_pct)
    
    def execute_market_order(self, symbol: str, direction: str,
                              quantity: float, price: float,
                              asset_type: str = 'stock',
                              strategy: str = 'manual',
                              stop_loss: Optional[float] = None,
                              take_profit: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute a market order (immediate fill).
        
        Args:
            symbol: Stock/crypto symbol
            direction: 'long' or 'short'
            quantity: Number of shares/units
            price: Current market price
            asset_type: 'stock' or 'crypto'
            strategy: Strategy name for tracking
            stop_loss: Optional stop-loss price
            take_profit: Optional take-profit price
            
        Returns:
            Dict with execution result
        """
        # Apply slippage
        fill_price = self._apply_slippage(price, direction, OrderType.MARKET)
        
        # Check if we can open position
        can_open, reason = self.portfolio.can_open_position(symbol, quantity, fill_price)
        
        if not can_open:
            return {
                'success': False,
                'status': OrderStatus.REJECTED.value,
                'reason': reason,
                'symbol': symbol,
                'direction': direction,
                'quantity': quantity,
                'price': price
            }
        
        # Calculate position value
        position_value = quantity * fill_price
        
        # Update cash balance (reduce for long, reserve for short)
        self.portfolio.update_cash_balance(-position_value)
        
        # Open position in database
        position_id = self.db.open_position({
            'symbol': symbol,
            'asset_type': asset_type,
            'strategy': strategy,
            'direction': direction,
            'quantity': quantity,
            'entry_price': fill_price,
            'current_price': fill_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'status': 'open',
            'opened_at': datetime.now().isoformat()
        })
        
        # Record trade
        trade_id = self.db.insert_trade({
            'symbol': symbol,
            'asset_type': asset_type,
            'strategy': strategy,
            'direction': direction,
            'order_type': OrderType.MARKET.value,
            'quantity': quantity,
            'price': fill_price,
            'position_id': position_id,
            'pnl': 0.0,  # No P&L on open
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'success': True,
            'status': OrderStatus.FILLED.value,
            'trade_id': trade_id,
            'position_id': position_id,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'requested_price': price,
            'fill_price': fill_price,
            'slippage': (fill_price - price) / price if price > 0 else 0,
            'position_value': position_value,
            'timestamp': datetime.now().isoformat()
        }
    
    def close_position(self, symbol: str, price: float,
                       reason: str = 'manual') -> Dict[str, Any]:
        """
        Close an existing position.
        
        Args:
            symbol: Symbol to close
            price: Current market price
            reason: Reason for closing ('manual', 'stop_loss', 'take_profit')
            
        Returns:
            Dict with close result
        """
        # Get position
        position = self.portfolio.get_position(symbol)
        
        if position is None:
            return {
                'success': False,
                'status': 'error',
                'reason': f'No open position for {symbol}'
            }
        
        direction = position['direction']
        quantity = position['quantity']
        entry_price = position['entry_price']
        asset_type = position.get('asset_type', 'stock')
        strategy = position.get('strategy', 'manual')
        
        # Apply slippage (opposite direction for close)
        close_direction = 'short' if direction == 'long' else 'long'
        fill_price = self._apply_slippage(price, close_direction, OrderType.MARKET)
        
        # Calculate P&L
        if direction == 'long':
            pnl = (fill_price - entry_price) * quantity
        else:
            pnl = (entry_price - fill_price) * quantity
        
        # Update cash balance (add back position value + P&L)
        position_value = quantity * entry_price
        self.portfolio.update_cash_balance(position_value + pnl)
        
        # Close position in database
        self.db.close_position(position['id'], fill_price, pnl)
        
        # Record closing trade
        trade_id = self.db.insert_trade({
            'symbol': symbol,
            'asset_type': asset_type,
            'strategy': strategy,
            'direction': 'sell' if direction == 'long' else 'buy',
            'order_type': reason,
            'quantity': quantity,
            'price': fill_price,
            'position_id': position['id'],
            'pnl': pnl,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'success': True,
            'status': OrderStatus.FILLED.value,
            'trade_id': trade_id,
            'position_id': position['id'],
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'entry_price': entry_price,
            'fill_price': fill_price,
            'pnl': pnl,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
    
    def create_limit_order(self, symbol: str, direction: str,
                            quantity: float, limit_price: float,
                            asset_type: str = 'stock',
                            strategy: str = 'manual',
                            stop_loss: Optional[float] = None,
                            take_profit: Optional[float] = None) -> Dict[str, Any]:
        """
        Create a limit order (filled when price reaches limit).
        
        Args:
            symbol: Symbol
            direction: 'long' or 'short'
            quantity: Quantity
            limit_price: Price to fill at
            asset_type: Asset type
            strategy: Strategy name
            stop_loss: Optional stop-loss
            take_profit: Optional take-profit
            
        Returns:
            Order creation result
        """
        order = {
            'id': len(self._pending_orders) + 1,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'limit_price': limit_price,
            'asset_type': asset_type,
            'strategy': strategy,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'order_type': OrderType.LIMIT.value,
            'status': OrderStatus.PENDING.value,
            'created_at': datetime.now().isoformat()
        }
        
        self._pending_orders.append(order)
        
        return {
            'success': True,
            'status': OrderStatus.PENDING.value,
            'order_id': order['id'],
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'limit_price': limit_price
        }
    
    def check_pending_orders(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Check pending orders and fill if conditions met.
        
        Args:
            current_prices: Dict mapping symbol to current price
            
        Returns:
            List of filled/updated orders
        """
        results = []
        orders_to_remove = []
        
        for order in self._pending_orders:
            symbol = order['symbol']
            
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            direction = order['direction']
            limit_price = order['limit_price']
            
            should_fill = False
            
            if order['order_type'] == OrderType.LIMIT.value:
                # Limit buy: fill if price <= limit
                # Limit sell: fill if price >= limit
                if direction == 'long' and current_price <= limit_price:
                    should_fill = True
                elif direction == 'short' and current_price >= limit_price:
                    should_fill = True
            
            if should_fill:
                # Execute the order
                result = self.execute_market_order(
                    symbol=symbol,
                    direction=direction,
                    quantity=order['quantity'],
                    price=limit_price,  # Use limit price
                    asset_type=order['asset_type'],
                    strategy=order['strategy'],
                    stop_loss=order.get('stop_loss'),
                    take_profit=order.get('take_profit')
                )
                
                result['order_id'] = order['id']
                result['order_type'] = order['order_type']
                results.append(result)
                orders_to_remove.append(order)
        
        # Remove filled orders
        for order in orders_to_remove:
            self._pending_orders.remove(order)
        
        return results
    
    def check_stop_loss_take_profit(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Check open positions for stop-loss/take-profit triggers.
        
        Args:
            current_prices: Dict mapping symbol to current price
            
        Returns:
            List of closed positions
        """
        results = []
        positions = self.portfolio.get_positions()
        
        if positions.empty:
            return results
        
        for _, pos in positions.iterrows():
            symbol = pos['symbol']
            
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            direction = pos['direction']
            stop_loss = pos.get('stop_loss')
            take_profit = pos.get('take_profit')
            
            close_reason = None
            
            # Check stop-loss
            if stop_loss is not None:
                if direction == 'long' and current_price <= stop_loss:
                    close_reason = 'stop_loss'
                elif direction == 'short' and current_price >= stop_loss:
                    close_reason = 'stop_loss'
            
            # Check take-profit
            if take_profit is not None and close_reason is None:
                if direction == 'long' and current_price >= take_profit:
                    close_reason = 'take_profit'
                elif direction == 'short' and current_price <= take_profit:
                    close_reason = 'take_profit'
            
            if close_reason:
                result = self.close_position(symbol, current_price, close_reason)
                results.append(result)
        
        return results
    
    def update_position_prices(self, current_prices: Dict[str, float]) -> int:
        """
        Update current prices for open positions.
        
        Args:
            current_prices: Dict mapping symbol to current price
            
        Returns:
            Number of positions updated
        """
        positions = self.portfolio.get_positions()
        updated = 0
        
        if positions.empty:
            return updated
        
        for _, pos in positions.iterrows():
            symbol = pos['symbol']
            
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            entry_price = pos['entry_price']
            direction = pos['direction']
            quantity = pos['quantity']
            
            # Calculate unrealized P&L
            if direction == 'long':
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity
            
            # Update in database
            self.db.update_position_price(
                pos['id'], 
                current_price, 
                unrealized_pnl
            )
            updated += 1
        
        return updated
    
    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """Cancel a pending order."""
        for order in self._pending_orders:
            if order['id'] == order_id:
                self._pending_orders.remove(order)
                return {
                    'success': True,
                    'status': OrderStatus.CANCELLED.value,
                    'order_id': order_id
                }
        
        return {
            'success': False,
            'status': 'error',
            'reason': f'Order {order_id} not found'
        }
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders."""
        return self._pending_orders.copy()
