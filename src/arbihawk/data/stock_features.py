"""
Feature engineering for stock and crypto trading data.

Implements technical indicators and strategy-specific features for
momentum, swing, and volatility breakout trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Callable, Tuple, List
from datetime import datetime, timedelta

from .database import Database


class StockFeatureEngineer:
    """
    Extracts trading features from price history data.
    
    Implements technical indicators (RSI, MACD, MA, Bollinger, ATR) and
    strategy-specific features for momentum, swing, and volatility trading.
    
    Example usage:
        engineer = StockFeatureEngineer(db)
        X, labels, dates, symbols = engineer.create_training_data('momentum')
    """
    
    # Default parameters for technical indicators
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    SMA_SHORT = 20
    SMA_MEDIUM = 50
    SMA_LONG = 200
    EMA_FAST = 12
    EMA_SLOW = 26
    BOLLINGER_PERIOD = 20
    BOLLINGER_STD = 2
    ATR_PERIOD = 14
    VOLUME_SMA_PERIOD = 20
    
    # Prediction horizons
    MOMENTUM_HORIZON = 20  # Days to predict momentum continuation
    SWING_HORIZON = 10     # Days to predict swing direction
    VOLATILITY_HORIZON = 5 # Days to predict breakout
    
    def __init__(self, db: Database):
        self.db = db
        self._price_cache: Optional[pd.DataFrame] = None
        self._indicators_cache: Dict[str, pd.DataFrame] = {}
    
    def invalidate_cache(self) -> None:
        """Invalidate all cached data."""
        self._price_cache = None
        self._indicators_cache = {}
    
    def _load_price_data(self, symbols: Optional[List[str]] = None,
                         asset_type: Optional[str] = None,
                         from_date: Optional[str] = None) -> pd.DataFrame:
        """Load price history from database."""
        df = self.db.get_price_history(asset_type=asset_type, from_date=from_date)
        
        if df.empty:
            return df
        
        if symbols:
            df = df[df['symbol'].isin(symbols)]
        
        # Sort by symbol and timestamp
        df = df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
        
        return df
    
    # =========================================================================
    # TECHNICAL INDICATORS (vectorized implementations)
    # =========================================================================
    
    def compute_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        """
        Compute Relative Strength Index.
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        period = period or self.RSI_PERIOD
        
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.fillna(50)  # Default to neutral
    
    def compute_macd(self, prices: pd.Series, fast: int = None, 
                     slow: int = None, signal: int = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Compute MACD (Moving Average Convergence Divergence).
        
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        fast = fast or self.MACD_FAST
        slow = slow or self.MACD_SLOW
        signal = signal or self.MACD_SIGNAL
        
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def compute_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Compute Simple Moving Average."""
        return prices.rolling(window=period, min_periods=1).mean()
    
    def compute_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Compute Exponential Moving Average."""
        return prices.ewm(span=period, adjust=False).mean()
    
    def compute_bollinger_bands(self, prices: pd.Series, period: int = None,
                                 std_dev: float = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Compute Bollinger Bands.
        
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        period = period or self.BOLLINGER_PERIOD
        std_dev = std_dev or self.BOLLINGER_STD
        
        middle = prices.rolling(window=period, min_periods=1).mean()
        std = prices.rolling(window=period, min_periods=1).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def compute_atr(self, high: pd.Series, low: pd.Series, 
                    close: pd.Series, period: int = None) -> pd.Series:
        """
        Compute Average True Range.
        
        TR = max(H-L, |H-Cp|, |L-Cp|) where Cp is previous close
        """
        period = period or self.ATR_PERIOD
        
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        
        return atr
    
    def compute_volume_sma(self, volume: pd.Series, period: int = None) -> pd.Series:
        """Compute Volume Simple Moving Average."""
        period = period or self.VOLUME_SMA_PERIOD
        return volume.rolling(window=period, min_periods=1).mean()
    
    def _get_temporal_features(self, timestamp: str) -> Dict[str, float]:
        """
        Extract temporal features from timestamp.
        
        Args:
            timestamp: ISO format datetime string or date string
            
        Returns:
            Dict with temporal features:
            - day_of_week: 0=Monday, 6=Sunday
            - is_weekend: 1 if Saturday/Sunday, 0 otherwise
            - month: 1-12
            - day_of_month: 1-31
        """
        try:
            # Parse datetime string
            if isinstance(timestamp, str):
                dt = pd.to_datetime(timestamp, errors='coerce')
            else:
                dt = pd.to_datetime(timestamp, errors='coerce')
            
            if pd.isna(dt):
                # Default values if parsing fails
                return {
                    'day_of_week': 0.0,  # Monday
                    'is_weekend': 0.0,
                    'month': 6.0,  # June
                    'day_of_month': 15.0
                }
            
            day_of_week = dt.dayofweek  # 0=Monday, 6=Sunday
            month = dt.month  # 1-12
            day_of_month = dt.day  # 1-31
            
            # Weekend: Saturday (5) or Sunday (6)
            is_weekend = 1.0 if day_of_week >= 5 else 0.0
            
            return {
                'day_of_week': float(day_of_week),
                'is_weekend': is_weekend,
                'month': float(month),
                'day_of_month': float(day_of_month)
            }
        except Exception:
            # Default values on any error
            return {
                'day_of_week': 0.0,
                'is_weekend': 0.0,
                'month': 6.0,
                'day_of_month': 15.0
            }
    
    # =========================================================================
    # INDICATOR COMPUTATION FOR SYMBOL
    # =========================================================================
    
    def compute_indicators(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all technical indicators for a price DataFrame.
        
        Args:
            price_df: DataFrame with columns: timestamp, open, high, low, close, volume
            
        Returns:
            DataFrame with original columns plus all indicators
        """
        if price_df.empty:
            return price_df
        
        df = price_df.copy()
        close = df['close'].astype(float)
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        volume = df['volume'].astype(float)
        
        # RSI
        df['rsi'] = self.compute_rsi(close)
        
        # MACD
        macd, signal, hist = self.compute_macd(close)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_histogram'] = hist
        
        # Moving Averages
        df['sma_20'] = self.compute_sma(close, self.SMA_SHORT)
        df['sma_50'] = self.compute_sma(close, self.SMA_MEDIUM)
        df['sma_200'] = self.compute_sma(close, self.SMA_LONG)
        df['ema_12'] = self.compute_ema(close, self.EMA_FAST)
        df['ema_26'] = self.compute_ema(close, self.EMA_SLOW)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.compute_bollinger_bands(close)
        df['bollinger_upper'] = bb_upper
        df['bollinger_middle'] = bb_middle
        df['bollinger_lower'] = bb_lower
        df['bollinger_width'] = (bb_upper - bb_lower) / bb_middle
        
        # ATR
        df['atr'] = self.compute_atr(high, low, close)
        df['atr_normalized'] = df['atr'] / close  # Normalized ATR
        
        # Volume SMA
        df['volume_sma'] = self.compute_volume_sma(volume)
        df['volume_ratio'] = volume / df['volume_sma'].replace(0, np.nan)
        
        # Temporal features
        if 'timestamp' in df.columns:
            temporal_features = df['timestamp'].apply(lambda ts: self._get_temporal_features(ts))
            df['day_of_week'] = temporal_features.apply(lambda x: x['day_of_week'])
            df['is_weekend'] = temporal_features.apply(lambda x: x['is_weekend'])
            df['month'] = temporal_features.apply(lambda x: x['month'])
            df['day_of_month'] = temporal_features.apply(lambda x: x['day_of_month'])
        else:
            # Default values if no timestamp
            df['day_of_week'] = 0.0
            df['is_weekend'] = 0.0
            df['month'] = 6.0
            df['day_of_month'] = 15.0
        
        return df
    
    # =========================================================================
    # MOMENTUM FEATURES
    # =========================================================================
    
    def compute_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute momentum-specific features.
        
        Features:
        - Price changes: 1d, 5d, 20d, 60d
        - Volume changes: 1d, 5d, 20d
        - Volatility: 20d rolling std
        - RSI momentum
        """
        if df.empty:
            return df
        
        result = df.copy()
        close = df['close'].astype(float)
        volume = df['volume'].astype(float)
        
        # Price changes (returns)
        result['return_1d'] = close.pct_change(1)
        result['return_5d'] = close.pct_change(5)
        result['return_20d'] = close.pct_change(20)
        result['return_60d'] = close.pct_change(60)
        
        # Volume changes
        result['volume_change_1d'] = volume.pct_change(1)
        result['volume_change_5d'] = volume.pct_change(5)
        result['volume_change_20d'] = volume.pct_change(20)
        
        # Volatility (20-day rolling std of returns)
        result['volatility_20d'] = result['return_1d'].rolling(window=20, min_periods=5).std()
        
        # RSI momentum (change in RSI)
        if 'rsi' in result.columns:
            result['rsi_change_5d'] = result['rsi'].diff(5)
        
        # Price position relative to SMAs
        if 'sma_20' in result.columns:
            result['price_vs_sma20'] = (close - result['sma_20']) / result['sma_20']
        if 'sma_50' in result.columns:
            result['price_vs_sma50'] = (close - result['sma_50']) / result['sma_50']
        
        # Momentum rank features (will be filled during batch processing)
        result['momentum_score'] = result['return_20d'].fillna(0)

        # Form momentum: recent vs previous period return (improving/declining trend)
        return_5d_prev = close.pct_change(5).shift(5)  # return from 10d ago to 5d ago
        result['momentum_trend_5d'] = (result['return_5d'] - return_5d_prev).fillna(0)
        return_20d_prev = close.pct_change(20).shift(20)  # return from 40d ago to 20d ago
        result['momentum_trend_20d'] = (result['return_20d'] - return_20d_prev).fillna(0)
        
        return result
    
    # =========================================================================
    # SWING FEATURES
    # =========================================================================
    
    def compute_swing_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute swing trading-specific features.
        
        Features:
        - RSI levels (oversold/overbought zones)
        - MACD crossover signals
        - Price position relative to MAs
        - Bollinger Band position
        - Volume patterns
        """
        if df.empty:
            return df
        
        result = df.copy()
        close = df['close'].astype(float)
        
        # RSI zones
        if 'rsi' in result.columns:
            result['rsi_oversold'] = (result['rsi'] < 30).astype(int)
            result['rsi_overbought'] = (result['rsi'] > 70).astype(int)
            result['rsi_neutral'] = ((result['rsi'] >= 30) & (result['rsi'] <= 70)).astype(int)
        
        # MACD crossover detection
        if 'macd' in result.columns and 'macd_signal' in result.columns:
            macd_prev = result['macd'].shift(1)
            signal_prev = result['macd_signal'].shift(1)
            
            # Bullish crossover: MACD crosses above signal
            result['macd_bullish_cross'] = ((result['macd'] > result['macd_signal']) & 
                                            (macd_prev <= signal_prev)).astype(int)
            # Bearish crossover: MACD crosses below signal
            result['macd_bearish_cross'] = ((result['macd'] < result['macd_signal']) & 
                                            (macd_prev >= signal_prev)).astype(int)
            # MACD direction
            result['macd_above_signal'] = (result['macd'] > result['macd_signal']).astype(int)
        
        # Price position relative to MAs (support/resistance)
        if 'sma_20' in result.columns:
            result['above_sma20'] = (close > result['sma_20']).astype(int)
            result['distance_to_sma20'] = (close - result['sma_20']) / close
        if 'sma_50' in result.columns:
            result['above_sma50'] = (close > result['sma_50']).astype(int)
            result['distance_to_sma50'] = (close - result['sma_50']) / close
        if 'sma_200' in result.columns:
            result['above_sma200'] = (close > result['sma_200']).astype(int)
        
        # Bollinger Band position
        if 'bollinger_upper' in result.columns and 'bollinger_lower' in result.columns:
            bb_range = result['bollinger_upper'] - result['bollinger_lower']
            result['bb_position'] = (close - result['bollinger_lower']) / bb_range.replace(0, np.nan)
            result['near_bb_upper'] = (result['bb_position'] > 0.9).astype(int)
            result['near_bb_lower'] = (result['bb_position'] < 0.1).astype(int)
        
        # Volume patterns
        if 'volume_ratio' in result.columns:
            result['high_volume'] = (result['volume_ratio'] > 1.5).astype(int)
            result['low_volume'] = (result['volume_ratio'] < 0.5).astype(int)
        
        # Trend detection (simple: price above/below key MAs)
        if 'sma_20' in result.columns and 'sma_50' in result.columns:
            result['uptrend'] = ((close > result['sma_20']) & 
                                 (result['sma_20'] > result['sma_50'])).astype(int)
            result['downtrend'] = ((close < result['sma_20']) & 
                                   (result['sma_20'] < result['sma_50'])).astype(int)
        
        return result
    
    # =========================================================================
    # VOLATILITY BREAKOUT FEATURES (Crypto)
    # =========================================================================
    
    def compute_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute volatility breakout-specific features (primarily for crypto).
        
        Features:
        - Bollinger Band width (squeeze detection)
        - ATR normalized
        - Volume patterns
        - Historical volatility
        - Squeeze detection
        """
        if df.empty:
            return df
        
        result = df.copy()
        close = df['close'].astype(float)
        
        # Bollinger Band width for squeeze detection
        if 'bollinger_width' in result.columns:
            # Rolling percentile of BB width (lower = squeeze)
            result['bb_width_percentile'] = result['bollinger_width'].rolling(
                window=50, min_periods=10
            ).apply(lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-10), raw=False)
            
            # Squeeze detection: BB width below 20th percentile of recent history
            result['bb_squeeze'] = (result['bb_width_percentile'] < 0.2).astype(int)
        
        # ATR-based volatility
        if 'atr_normalized' in result.columns:
            result['atr_percentile'] = result['atr_normalized'].rolling(
                window=50, min_periods=10
            ).apply(lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-10), raw=False)
            
            result['low_volatility'] = (result['atr_percentile'] < 0.3).astype(int)
        
        # Historical volatility (annualized)
        if 'return_1d' in result.columns:
            result['hist_volatility'] = result['return_1d'].rolling(
                window=20, min_periods=5
            ).std() * np.sqrt(365)  # Annualized for crypto (365 days)
        else:
            returns = close.pct_change()
            result['hist_volatility'] = returns.rolling(
                window=20, min_periods=5
            ).std() * np.sqrt(365)
        
        # Volume surge detection
        if 'volume_ratio' in result.columns:
            result['volume_surge'] = (result['volume_ratio'] > 2.0).astype(int)
        
        # Breakout direction hints
        if 'bb_position' in result.columns:
            # Price position when squeeze releases
            result['breakout_bias_up'] = (result['bb_position'] > 0.5).astype(int)
            result['breakout_bias_down'] = (result['bb_position'] < 0.5).astype(int)
        
        return result
    
    # =========================================================================
    # TRAINING DATA CREATION
    # =========================================================================
    
    def _create_labels(self, df: pd.DataFrame, strategy: str, 
                       horizon: int) -> pd.Series:
        """
        Create labels for training.
        
        Args:
            df: DataFrame with price data
            strategy: 'momentum', 'swing', or 'volatility'
            horizon: Days to look ahead for label
            
        Returns:
            Series of labels (1 for up, 0 for down)
        """
        if df.empty:
            return pd.Series(dtype=int)
        
        close = df['close'].astype(float)
        
        # Future return
        future_return = close.shift(-horizon) / close - 1
        
        if strategy == 'momentum':
            # Momentum: predict if price will be higher after horizon days
            # Use a threshold to filter noise
            threshold = 0.02  # 2% move
            labels = (future_return > threshold).astype(int)
        elif strategy == 'swing':
            # Swing: predict direction (up/down)
            labels = (future_return > 0).astype(int)
        elif strategy == 'volatility':
            # Volatility: predict significant move (either direction)
            threshold = 0.05  # 5% move in either direction
            labels = (future_return.abs() > threshold).astype(int)
        else:
            labels = (future_return > 0).astype(int)
        
        return labels
    
    def create_training_data(self, strategy: str, 
                             symbols: Optional[List[str]] = None,
                             asset_type: Optional[str] = None,
                             lookback_days: int = 365,
                             log_callback: Optional[Callable[[str, str], None]] = None
                             ) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Create training dataset for a specific strategy.
        
        Args:
            strategy: 'momentum', 'swing', or 'volatility'
            symbols: List of symbols to include (optional)
            asset_type: 'stock' or 'crypto' (optional)
            lookback_days: Days of history to use
            log_callback: Logging callback function
            
        Returns:
            Tuple of (X, labels, dates, symbols) where:
            - X: DataFrame of features
            - labels: Series of labels (1=up, 0=down for direction; 1=breakout for volatility)
            - dates: Series of timestamps
            - symbols: Series of symbol names
        """
        if log_callback:
            log_callback("info", f"Creating training data for {strategy} strategy...")
        
        # Load price data
        from_date = (datetime.now() - timedelta(days=lookback_days + 200)).strftime('%Y-%m-%d')
        price_df = self._load_price_data(symbols=symbols, asset_type=asset_type, from_date=from_date)
        
        if price_df.empty:
            if log_callback:
                log_callback("warning", "No price data available")
            return pd.DataFrame(), pd.Series(dtype=int), pd.Series(), pd.Series()
        
        if log_callback:
            unique_symbols = price_df['symbol'].nunique()
            log_callback("info", f"  Loaded {len(price_df)} price records for {unique_symbols} symbols")
        
        # Determine prediction horizon
        horizons = {
            'momentum': self.MOMENTUM_HORIZON,
            'swing': self.SWING_HORIZON,
            'volatility': self.VOLATILITY_HORIZON
        }
        horizon = horizons.get(strategy, self.SWING_HORIZON)
        
        # Process each symbol
        all_features = []
        all_labels = []
        all_dates = []
        all_symbols = []
        
        grouped = price_df.groupby('symbol')
        total_symbols = len(grouped)
        
        for idx, (symbol, symbol_df) in enumerate(grouped):
            if log_callback and (idx + 1) % 5 == 0:
                log_callback("info", f"  Processing symbol {idx + 1}/{total_symbols}: {symbol}")
            
            # Need enough data for indicators and labels
            if len(symbol_df) < self.SMA_LONG + horizon + 10:
                continue
            
            # Sort by timestamp
            symbol_df = symbol_df.sort_values('timestamp').reset_index(drop=True)
            
            # Compute indicators
            df_with_indicators = self.compute_indicators(symbol_df)
            
            # Compute strategy-specific features
            if strategy == 'momentum':
                df_with_features = self.compute_momentum_features(df_with_indicators)
            elif strategy == 'swing':
                df_with_features = self.compute_swing_features(df_with_indicators)
            elif strategy == 'volatility':
                df_with_features = self.compute_momentum_features(df_with_indicators)
                df_with_features = self.compute_volatility_features(df_with_features)
            else:
                df_with_features = self.compute_swing_features(df_with_indicators)
            
            # Create labels
            labels = self._create_labels(df_with_features, strategy, horizon)
            
            # Select feature columns
            feature_cols = self._get_feature_columns(strategy)
            available_cols = [c for c in feature_cols if c in df_with_features.columns]
            
            if len(available_cols) < 5:
                continue
            
            # Get valid rows (no NaN in features, valid labels)
            X_symbol = df_with_features[available_cols]
            
            # Drop rows with NaN values and where labels are NaN
            valid_mask = ~(X_symbol.isnull().any(axis=1) | labels.isnull())
            # Also exclude last 'horizon' rows (no future label available)
            valid_mask.iloc[-horizon:] = False
            
            if valid_mask.sum() < 10:
                continue
            
            X_valid = X_symbol[valid_mask]
            labels_valid = labels[valid_mask]
            dates_valid = df_with_features.loc[valid_mask, 'timestamp']
            symbols_valid = pd.Series([symbol] * len(X_valid), index=X_valid.index)
            
            all_features.append(X_valid)
            all_labels.append(labels_valid)
            all_dates.append(dates_valid)
            all_symbols.append(symbols_valid)
        
        if not all_features:
            if log_callback:
                log_callback("warning", "No valid training data after processing")
            return pd.DataFrame(), pd.Series(dtype=int), pd.Series(), pd.Series()
        
        # Combine all data
        X = pd.concat(all_features, ignore_index=True)
        labels = pd.concat(all_labels, ignore_index=True)
        dates = pd.concat(all_dates, ignore_index=True)
        symbols = pd.concat(all_symbols, ignore_index=True)
        
        # Fill any remaining NaN with 0
        X = X.fillna(0)
        
        if log_callback:
            log_callback("info", f"  Training data ready: {len(X)} samples, {len(X.columns)} features")
            label_dist = labels.value_counts()
            log_callback("info", f"  Label distribution: {dict(label_dist)}")
        
        return X, labels, dates, symbols
    
    def _get_feature_columns(self, strategy: str) -> List[str]:
        """Get feature column names for a strategy."""
        # Base indicator features
        base_features = [
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'sma_20', 'sma_50', 'sma_200', 'ema_12', 'ema_26',
            'bollinger_upper', 'bollinger_middle', 'bollinger_lower', 'bollinger_width',
            'atr', 'atr_normalized', 'volume_sma', 'volume_ratio'
        ]
        
        # Temporal features (4 features)
        temporal_features = [
            'day_of_week', 'is_weekend', 'month', 'day_of_month'
        ]
        
        # Momentum features
        momentum_features = [
            'return_1d', 'return_5d', 'return_20d', 'return_60d',
            'volume_change_1d', 'volume_change_5d', 'volume_change_20d',
            'volatility_20d', 'rsi_change_5d',
            'price_vs_sma20', 'price_vs_sma50', 'momentum_score',
            'momentum_trend_5d', 'momentum_trend_20d'
        ]
        
        # Swing features
        swing_features = [
            'rsi_oversold', 'rsi_overbought', 'rsi_neutral',
            'macd_bullish_cross', 'macd_bearish_cross', 'macd_above_signal',
            'above_sma20', 'above_sma50', 'above_sma200',
            'distance_to_sma20', 'distance_to_sma50',
            'bb_position', 'near_bb_upper', 'near_bb_lower',
            'high_volume', 'low_volume', 'uptrend', 'downtrend'
        ]
        
        # Volatility features
        volatility_features = [
            'bb_width_percentile', 'bb_squeeze', 'atr_percentile', 'low_volatility',
            'hist_volatility', 'volume_surge', 'breakout_bias_up', 'breakout_bias_down'
        ]
        
        if strategy == 'momentum':
            return base_features + momentum_features + temporal_features
        elif strategy == 'swing':
            return base_features + swing_features + temporal_features
        elif strategy == 'volatility':
            return base_features + momentum_features + volatility_features + temporal_features
        else:
            return base_features + swing_features + temporal_features
    
    # =========================================================================
    # REAL-TIME FEATURE COMPUTATION
    # =========================================================================
    
    def compute_features_for_symbol(self, symbol: str, asset_type: str,
                                     strategy: str) -> Optional[pd.Series]:
        """
        Compute features for a single symbol (for real-time signal generation).
        
        Args:
            symbol: Stock/crypto symbol
            asset_type: 'stock' or 'crypto'
            strategy: Strategy name
            
        Returns:
            Series of features or None if insufficient data
        """
        # Load recent price data for this symbol
        from_date = (datetime.now() - timedelta(days=300)).strftime('%Y-%m-%d')
        price_df = self.db.get_price_history(symbol=symbol, asset_type=asset_type, from_date=from_date)
        
        if price_df.empty or len(price_df) < self.SMA_LONG:
            return None
        
        # Sort and compute indicators
        price_df = price_df.sort_values('timestamp').reset_index(drop=True)
        df = self.compute_indicators(price_df)
        
        # Compute strategy-specific features
        if strategy == 'momentum':
            df = self.compute_momentum_features(df)
        elif strategy == 'swing':
            df = self.compute_swing_features(df)
        elif strategy == 'volatility':
            df = self.compute_momentum_features(df)
            df = self.compute_volatility_features(df)
        
        # Get feature columns
        feature_cols = self._get_feature_columns(strategy)
        available_cols = [c for c in feature_cols if c in df.columns]
        
        # Return latest row features
        latest = df.iloc[-1][available_cols]
        # Convert to numeric first to avoid FutureWarning about downcasting object dtype
        numeric_latest = pd.to_numeric(latest, errors='coerce')
        return numeric_latest.fillna(0)
    
    def compute_features_batch(self, symbols: List[str], asset_type: str,
                                strategy: str) -> pd.DataFrame:
        """
        Compute features for multiple symbols (for batch signal generation).
        
        Args:
            symbols: List of symbols
            asset_type: 'stock' or 'crypto'
            strategy: Strategy name
            
        Returns:
            DataFrame with one row per symbol
        """
        results = []
        
        for symbol in symbols:
            features = self.compute_features_for_symbol(symbol, asset_type, strategy)
            if features is not None:
                features['symbol'] = symbol
                features['asset_type'] = asset_type
                results.append(features)
        
        if not results:
            return pd.DataFrame()
        
        return pd.DataFrame(results)
