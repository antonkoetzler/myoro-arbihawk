"""
Trade signal engine for identifying trading opportunities.

Generates signals for momentum, swing, and volatility breakout strategies.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

import config
from data.database import Database
from data.stock_features import StockFeatureEngineer

if TYPE_CHECKING:
    from models.trading_predictor import TradingPredictor


class TradeSignalEngine:
    """
    Identifies trade signals based on ML predictions and technical analysis.
    
    Generates signals for momentum, swing, and volatility breakout strategies.
    """
    
    def __init__(self, db: Database,
                 momentum_predictor: Optional['TradingPredictor'] = None,
                 swing_predictor: Optional['TradingPredictor'] = None,
                 volatility_predictor: Optional['TradingPredictor'] = None):
        """
        Initialize trade signal engine.
        
        Args:
            db: Database instance
            momentum_predictor: Trained predictor for momentum strategy
            swing_predictor: Trained predictor for swing strategy
            volatility_predictor: Trained predictor for volatility strategy
        """
        self.db = db
        self.feature_engineer = StockFeatureEngineer(db)
        
        self.momentum_predictor = momentum_predictor
        self.swing_predictor = swing_predictor
        self.volatility_predictor = volatility_predictor
        
        # Load config
        trading_config = getattr(config, 'TRADING_CONFIG', {})
        strategies_config = trading_config.get('strategies', {})
        
        # Confidence thresholds
        self.momentum_confidence = strategies_config.get('momentum', {}).get('min_confidence', 0.6)
        self.swing_confidence = strategies_config.get('swing', {}).get('min_confidence', 0.65)
        self.volatility_confidence = strategies_config.get('volatility', {}).get('min_confidence', 0.65)
        
        # Risk/reward thresholds
        self.min_risk_reward = strategies_config.get('momentum', {}).get('min_risk_reward', 2.0)
    
    def calculate_ev(self, probability: float, expected_return: float, 
                     risk: float) -> float:
        """
        Calculate Expected Value for a trade signal.
        
        Args:
            probability: Predicted probability of success
            expected_return: Expected return if successful (e.g., 0.05 for 5%)
            risk: Risk/loss if unsuccessful (e.g., 0.02 for 2%)
            
        Returns:
            Expected value of the trade
        """
        ev = (probability * expected_return) - ((1 - probability) * risk)
        return ev
    
    def calculate_risk_reward(self, entry: float, stop_loss: float, 
                              take_profit: float, direction: str = 'long') -> float:
        """
        Calculate risk/reward ratio.
        
        Args:
            entry: Entry price
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            direction: 'long' or 'short'
            
        Returns:
            Risk/reward ratio (reward / risk)
        """
        if direction == 'long':
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
        else:
            risk = abs(stop_loss - entry)
            reward = abs(entry - take_profit)
        
        if risk == 0:
            return 0.0
        
        return reward / risk
    
    def _get_latest_price(self, symbol: str, asset_type: str) -> Optional[Dict[str, Any]]:
        """Get latest price data for a symbol."""
        df = self.db.get_price_history(symbol=symbol, asset_type=asset_type, limit=1)
        
        if df.empty:
            return None
        
        row = df.iloc[0]
        return {
            'symbol': symbol,
            'asset_type': asset_type,
            'close': float(row['close']),
            'high': float(row['high']),
            'low': float(row['low']),
            'open': float(row['open']),
            'volume': float(row['volume']) if pd.notna(row['volume']) else 0,
            'timestamp': row['timestamp']
        }
    
    def _calculate_stop_loss(self, entry: float, atr: float, 
                              direction: str = 'long', multiplier: float = 2.0) -> float:
        """Calculate stop-loss based on ATR."""
        if direction == 'long':
            return entry - (atr * multiplier)
        else:
            return entry + (atr * multiplier)
    
    def _calculate_take_profit(self, entry: float, stop_loss: float,
                                risk_reward: float = 2.0, 
                                direction: str = 'long') -> float:
        """Calculate take-profit based on risk/reward ratio."""
        risk = abs(entry - stop_loss)
        reward = risk * risk_reward
        
        if direction == 'long':
            return entry + reward
        else:
            return entry - reward
    
    def find_momentum_signals(self, symbols: Optional[List[str]] = None,
                              asset_type: Optional[str] = None,
                              lookback_days: int = 20) -> pd.DataFrame:
        """
        Find momentum trading opportunities.
        
        Momentum criteria:
        - Top performers by recent returns
        - ML predicts continuation (confidence > threshold)
        - Volume confirmation
        - Risk-reward > minimum
        
        Args:
            symbols: List of symbols to analyze (default: from config)
            asset_type: Filter by 'stock' or 'crypto'
            lookback_days: Days to look back for momentum calculation
            
        Returns:
            DataFrame of momentum signals
        """
        if self.momentum_predictor is None or not self.momentum_predictor.is_trained:
            return pd.DataFrame()
        
        # Get symbols from config if not provided
        if symbols is None:
            trading_config = getattr(config, 'TRADING_CONFIG', {})
            watchlist = trading_config.get('watchlist', {})
            if asset_type == 'stock':
                symbols = watchlist.get('stocks', [])
            elif asset_type == 'crypto':
                symbols = watchlist.get('crypto', [])
            else:
                symbols = watchlist.get('stocks', []) + watchlist.get('crypto', [])
        
        if not symbols:
            return pd.DataFrame()
        
        signals = []
        
        for symbol in symbols:
            # Determine asset type for this symbol
            sym_asset_type = asset_type
            if sym_asset_type is None:
                trading_config = getattr(config, 'TRADING_CONFIG', {})
                if symbol in trading_config.get('watchlist', {}).get('crypto', []):
                    sym_asset_type = 'crypto'
                else:
                    sym_asset_type = 'stock'
            
            # Get features
            features = self.feature_engineer.compute_features_for_symbol(
                symbol, sym_asset_type, 'momentum'
            )
            
            if features is None:
                continue
            
            # Get prediction
            features_df = pd.DataFrame([features])
            probs = self.momentum_predictor.predict_probabilities(features_df)
            
            if probs.empty:
                continue
            
            up_prob = probs['up'].iloc[0]
            confidence = max(up_prob, 1 - up_prob)
            direction = 'long' if up_prob >= 0.5 else 'short'
            
            if confidence < self.momentum_confidence:
                continue
            
            # Get latest price
            price_data = self._get_latest_price(symbol, sym_asset_type)
            if price_data is None:
                continue
            
            entry_price = price_data['close']
            
            # Get ATR for stop-loss calculation
            atr = features.get('atr', entry_price * 0.02)  # Default 2% if no ATR
            
            # Calculate stop-loss and take-profit
            stop_loss = self._calculate_stop_loss(entry_price, atr, direction)
            take_profit = self._calculate_take_profit(entry_price, stop_loss, self.min_risk_reward, direction)
            
            # Calculate risk/reward
            risk_reward = self.calculate_risk_reward(entry_price, stop_loss, take_profit, direction)
            
            if risk_reward < self.min_risk_reward:
                continue
            
            # Calculate expected value
            expected_return = abs(take_profit - entry_price) / entry_price
            risk = abs(entry_price - stop_loss) / entry_price
            ev = self.calculate_ev(confidence, expected_return, risk)
            
            # Check momentum score (from features)
            momentum_score = features.get('return_20d', 0)
            
            signals.append({
                'symbol': symbol,
                'asset_type': sym_asset_type,
                'strategy': 'momentum',
                'direction': direction,
                'confidence': confidence,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': risk_reward,
                'expected_value': ev,
                'momentum_score': momentum_score,
                'atr': atr,
                'timestamp': datetime.now().isoformat()
            })
        
        if not signals:
            return pd.DataFrame()
        
        result = pd.DataFrame(signals)
        result = result.sort_values('expected_value', ascending=False)
        
        return result
    
    def find_swing_signals(self, symbols: Optional[List[str]] = None,
                           asset_type: Optional[str] = None) -> pd.DataFrame:
        """
        Find swing trading opportunities.
        
        Swing criteria:
        - RSI oversold in uptrend OR RSI overbought in downtrend
        - MACD bullish/bearish crossover
        - Price at support/resistance (MA levels)
        - ML confirms direction (confidence > threshold)
        - Risk-reward > minimum
        
        Args:
            symbols: List of symbols to analyze
            asset_type: Filter by 'stock' or 'crypto'
            
        Returns:
            DataFrame of swing signals
        """
        if self.swing_predictor is None or not self.swing_predictor.is_trained:
            return pd.DataFrame()
        
        # Get symbols from config if not provided
        if symbols is None:
            trading_config = getattr(config, 'TRADING_CONFIG', {})
            watchlist = trading_config.get('watchlist', {})
            if asset_type == 'stock':
                symbols = watchlist.get('stocks', [])
            elif asset_type == 'crypto':
                symbols = watchlist.get('crypto', [])
            else:
                symbols = watchlist.get('stocks', []) + watchlist.get('crypto', [])
        
        if not symbols:
            return pd.DataFrame()
        
        signals = []
        
        for symbol in symbols:
            # Determine asset type for this symbol
            sym_asset_type = asset_type
            if sym_asset_type is None:
                trading_config = getattr(config, 'TRADING_CONFIG', {})
                if symbol in trading_config.get('watchlist', {}).get('crypto', []):
                    sym_asset_type = 'crypto'
                else:
                    sym_asset_type = 'stock'
            
            # Get features
            features = self.feature_engineer.compute_features_for_symbol(
                symbol, sym_asset_type, 'swing'
            )
            
            if features is None:
                continue
            
            # Check swing entry conditions
            rsi_oversold = features.get('rsi_oversold', 0)
            rsi_overbought = features.get('rsi_overbought', 0)
            macd_bullish = features.get('macd_bullish_cross', 0)
            macd_bearish = features.get('macd_bearish_cross', 0)
            uptrend = features.get('uptrend', 0)
            downtrend = features.get('downtrend', 0)
            near_bb_lower = features.get('near_bb_lower', 0)
            near_bb_upper = features.get('near_bb_upper', 0)
            
            # Determine potential entry
            has_entry_signal = False
            direction = None
            entry_reason = []
            
            # Long entry: RSI oversold in uptrend, or MACD bullish cross, or near BB lower
            if (rsi_oversold and uptrend) or macd_bullish or (near_bb_lower and uptrend):
                has_entry_signal = True
                direction = 'long'
                if rsi_oversold and uptrend:
                    entry_reason.append('RSI oversold in uptrend')
                if macd_bullish:
                    entry_reason.append('MACD bullish crossover')
                if near_bb_lower and uptrend:
                    entry_reason.append('Near Bollinger lower band')
            
            # Short entry: RSI overbought in downtrend, or MACD bearish cross, or near BB upper
            elif (rsi_overbought and downtrend) or macd_bearish or (near_bb_upper and downtrend):
                has_entry_signal = True
                direction = 'short'
                if rsi_overbought and downtrend:
                    entry_reason.append('RSI overbought in downtrend')
                if macd_bearish:
                    entry_reason.append('MACD bearish crossover')
                if near_bb_upper and downtrend:
                    entry_reason.append('Near Bollinger upper band')
            
            if not has_entry_signal:
                continue
            
            # Get prediction
            features_df = pd.DataFrame([features])
            probs = self.swing_predictor.predict_probabilities(features_df)
            
            if probs.empty:
                continue
            
            up_prob = probs['up'].iloc[0]
            
            # Verify ML agrees with technical direction
            ml_direction = 'long' if up_prob >= 0.5 else 'short'
            confidence = up_prob if direction == 'long' else (1 - up_prob)
            
            if ml_direction != direction or confidence < self.swing_confidence:
                continue
            
            # Get latest price
            price_data = self._get_latest_price(symbol, sym_asset_type)
            if price_data is None:
                continue
            
            entry_price = price_data['close']
            
            # Get ATR for stop-loss calculation
            atr = features.get('atr', entry_price * 0.02)
            
            # Calculate stop-loss and take-profit
            stop_loss = self._calculate_stop_loss(entry_price, atr, direction, multiplier=1.5)
            take_profit = self._calculate_take_profit(entry_price, stop_loss, self.min_risk_reward, direction)
            
            # Calculate risk/reward
            risk_reward = self.calculate_risk_reward(entry_price, stop_loss, take_profit, direction)
            
            if risk_reward < self.min_risk_reward:
                continue
            
            # Calculate expected value
            expected_return = abs(take_profit - entry_price) / entry_price
            risk = abs(entry_price - stop_loss) / entry_price
            ev = self.calculate_ev(confidence, expected_return, risk)
            
            signals.append({
                'symbol': symbol,
                'asset_type': sym_asset_type,
                'strategy': 'swing',
                'direction': direction,
                'confidence': confidence,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': risk_reward,
                'expected_value': ev,
                'rsi': features.get('rsi', 50),
                'entry_reason': ', '.join(entry_reason),
                'atr': atr,
                'timestamp': datetime.now().isoformat()
            })
        
        if not signals:
            return pd.DataFrame()
        
        result = pd.DataFrame(signals)
        result = result.sort_values('expected_value', ascending=False)
        
        return result
    
    def find_volatility_signals(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Find crypto volatility breakout opportunities.
        
        Volatility criteria:
        - Low volatility (Bollinger squeeze detected)
        - ML predicts breakout (confidence > threshold)
        - Volume increase confirmation
        - Risk-reward > minimum
        
        Args:
            symbols: List of crypto symbols to analyze (default: from config)
            
        Returns:
            DataFrame of volatility breakout signals
        """
        if self.volatility_predictor is None or not self.volatility_predictor.is_trained:
            return pd.DataFrame()
        
        # Get crypto symbols from config if not provided
        if symbols is None:
            trading_config = getattr(config, 'TRADING_CONFIG', {})
            symbols = trading_config.get('watchlist', {}).get('crypto', [])
        
        if not symbols:
            return pd.DataFrame()
        
        signals = []
        
        for symbol in symbols:
            # Get features
            features = self.feature_engineer.compute_features_for_symbol(
                symbol, 'crypto', 'volatility'
            )
            
            if features is None:
                continue
            
            # Check volatility breakout conditions
            bb_squeeze = features.get('bb_squeeze', 0)
            low_volatility = features.get('low_volatility', 0)
            volume_surge = features.get('volume_surge', 0)
            
            # Need squeeze or low volatility condition
            if not (bb_squeeze or low_volatility):
                continue
            
            # Get prediction
            features_df = pd.DataFrame([features])
            probs = self.volatility_predictor.predict_probabilities(features_df)
            
            if probs.empty:
                continue
            
            breakout_prob = probs['breakout'].iloc[0]
            
            if breakout_prob < self.volatility_confidence:
                continue
            
            # Get latest price
            price_data = self._get_latest_price(symbol, 'crypto')
            if price_data is None:
                continue
            
            entry_price = price_data['close']
            
            # Determine breakout direction from bias
            breakout_bias_up = features.get('breakout_bias_up', 0)
            direction = 'long' if breakout_bias_up else 'short'
            
            # Get ATR for stop-loss calculation
            atr = features.get('atr', entry_price * 0.03)  # Default 3% for crypto
            
            # Calculate stop-loss and take-profit (wider for breakout)
            stop_loss = self._calculate_stop_loss(entry_price, atr, direction, multiplier=1.0)
            take_profit = self._calculate_take_profit(entry_price, stop_loss, self.min_risk_reward * 1.5, direction)
            
            # Calculate risk/reward
            risk_reward = self.calculate_risk_reward(entry_price, stop_loss, take_profit, direction)
            
            if risk_reward < self.min_risk_reward:
                continue
            
            # Calculate expected value
            expected_return = abs(take_profit - entry_price) / entry_price
            risk = abs(entry_price - stop_loss) / entry_price
            ev = self.calculate_ev(breakout_prob, expected_return, risk)
            
            signals.append({
                'symbol': symbol,
                'asset_type': 'crypto',
                'strategy': 'volatility',
                'direction': direction,
                'confidence': breakout_prob,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': risk_reward,
                'expected_value': ev,
                'bb_squeeze': bool(bb_squeeze),
                'volume_surge': bool(volume_surge),
                'atr': atr,
                'timestamp': datetime.now().isoformat()
            })
        
        if not signals:
            return pd.DataFrame()
        
        result = pd.DataFrame(signals)
        result = result.sort_values('expected_value', ascending=False)
        
        return result
    
    def find_all_signals(self, limit_per_strategy: int = 5) -> pd.DataFrame:
        """
        Find signals from all strategies.
        
        Args:
            limit_per_strategy: Maximum signals to return per strategy
            
        Returns:
            DataFrame of all signals sorted by expected value
        """
        all_signals = []
        
        # Momentum signals
        if self.momentum_predictor is None:
            pass  # Model not loaded - skip silently
        elif not self.momentum_predictor.is_trained:
            pass  # Model not trained - skip silently
        else:
            momentum = self.find_momentum_signals()
            if not momentum.empty:
                all_signals.append(momentum.head(limit_per_strategy))
        
        # Swing signals
        if self.swing_predictor is None:
            pass  # Model not loaded - skip silently
        elif not self.swing_predictor.is_trained:
            pass  # Model not trained - skip silently
        else:
            swing = self.find_swing_signals()
            if not swing.empty:
                all_signals.append(swing.head(limit_per_strategy))
        
        # Volatility signals (crypto only)
        if self.volatility_predictor is None:
            pass  # Model not loaded - skip silently
        elif not self.volatility_predictor.is_trained:
            pass  # Model not trained - skip silently
        else:
            volatility = self.find_volatility_signals()
            if not volatility.empty:
                all_signals.append(volatility.head(limit_per_strategy))
        
        if not all_signals:
            return pd.DataFrame()
        
        result = pd.concat(all_signals, ignore_index=True)
        result = result.sort_values('expected_value', ascending=False)
        
        return result
    
    def get_recommendations(self, limit: int = 10) -> pd.DataFrame:
        """Get top trade recommendations from all strategies."""
        signals = self.find_all_signals(limit_per_strategy=limit)
        
        if signals.empty:
            return pd.DataFrame()
        
        return signals.head(limit)
