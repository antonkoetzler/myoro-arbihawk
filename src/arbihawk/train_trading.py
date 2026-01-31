"""
Training script for Arbihawk trading prediction models.

Trains models for all trading strategies:
- Momentum (stocks + crypto)
- Swing (stocks + crypto)
- Volatility Breakout (crypto only)
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, Callable

from data.database import Database
from data.stock_features import StockFeatureEngineer
from models.trading_predictor import TradingPredictor, TradingModelManager
import config
from utils.colors import (
    print_header, print_success, print_error, 
    print_warning, print_info, print_step
)


def train_trading_models(db: Optional[Database] = None, 
                         log_callback: Optional[Callable[[str, str], None]] = None,
                         strategies: Optional[list] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Train prediction models for all trading strategies.
    
    Args:
        db: Database instance
        log_callback: Optional callback for logging
        strategies: List of strategies to train (default: all)
        
    Returns:
        Tuple of (success: bool, metrics: dict)
    """
    if log_callback:
        log_callback("info", "=" * 60)
        log_callback("info", "[TRADING] Model Training")
        log_callback("info", "=" * 60)
    else:
        print_header("[TRADING] Model Training")
    
    # Default strategies
    if strategies is None:
        strategies = ['momentum', 'swing', 'volatility']
    
    db = db or Database()
    feature_engineer = StockFeatureEngineer(db)
    model_manager = TradingModelManager(db)
    
    models_dir = Path(__file__).parent / "models" / "saved"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    trained_count = 0
    no_data_count = 0
    actual_errors = []
    
    metrics = {
        "trained_at": datetime.now().isoformat(),
        "domain": "trading",
        "strategies": {},
        "total_samples": 0,
        "has_data": False,
        "errors": [],
        "no_data_reason": None
    }
    
    # Get trading config
    trading_config = getattr(config, 'TRADING_CONFIG', {})
    if not trading_config.get('enabled', False):
        msg = "Trading is disabled in config"
        if log_callback:
            log_callback("warning", msg)
        else:
            print_warning(msg)
        metrics["no_data_reason"] = msg
        return True, metrics
    
    # Check price history availability
    price_history = db.get_price_history(limit=1)
    if price_history.empty:
        msg = "No price history data available. Run trading data collection first."
        if log_callback:
            log_callback("warning", msg)
        else:
            print_warning(msg)
        metrics["no_data_reason"] = msg
        return True, metrics
    
    # Train each strategy
    for strategy in strategies:
        if log_callback:
            log_callback("info", f"\n{'='*40}")
            log_callback("info", f"Training {strategy.upper()} strategy")
            log_callback("info", f"{'='*40}")
        else:
            print_info(f"\nTraining {strategy.upper()} strategy")
        
        # Determine asset type based on strategy
        if strategy == 'volatility':
            # Volatility breakout is crypto-only
            asset_type = 'crypto'
            symbols = trading_config.get('watchlist', {}).get('crypto', [])
        else:
            # Momentum and swing work on both stocks and crypto
            asset_type = None  # Train on all
            stock_symbols = trading_config.get('watchlist', {}).get('stocks', [])
            crypto_symbols = trading_config.get('watchlist', {}).get('crypto', [])
            symbols = stock_symbols + crypto_symbols
        
        if not symbols:
            msg = f"No symbols configured for {strategy} strategy"
            if log_callback:
                log_callback("warning", msg)
            else:
                print_warning(msg)
            metrics["strategies"][strategy] = {"skipped": True, "reason": msg}
            no_data_count += 1
            continue
        
        try:
            # Create training data
            if log_callback:
                log_callback("info", f"Creating training data for {strategy}...")
            else:
                print_step(f"Creating training data for {strategy}...")
            
            X, labels, dates, symbol_series = feature_engineer.create_training_data(
                strategy=strategy,
                symbols=symbols if symbols else None,
                asset_type=asset_type,
                lookback_days=365,
                log_callback=log_callback
            )
            
            if len(X) == 0:
                msg = f"No training data available for {strategy}"
                if log_callback:
                    log_callback("warning", msg)
                else:
                    print_warning(msg)
                metrics["strategies"][strategy] = {"skipped": True, "reason": msg}
                no_data_count += 1
                continue
            
            if log_callback:
                log_callback("info", f"Training data: {len(X)} samples, {len(X.columns)} features")
            else:
                print_info(f"Training data: {len(X)} samples, {len(X.columns)} features")
            
            # Show label distribution
            label_dist = labels.value_counts()
            if log_callback:
                log_callback("info", f"Label distribution: {dict(label_dist)}")
            else:
                print_info(f"Label distribution: {dict(label_dist)}")
            
            # Create and train predictor
            if log_callback:
                log_callback("info", "Training model...")
            else:
                print_step("Training model...")
            
            predictor = TradingPredictor(strategy=strategy)
            predictor.train(
                features=X,
                labels=labels,
                dates=dates,
                symbols=symbol_series,
                log_callback=log_callback
            )
            
            # Log training metrics
            training_metrics = predictor.training_metrics
            if log_callback:
                log_callback("info", f"Accuracy: {training_metrics.get('accuracy', 0):.3f}, "
                                     f"Precision: {training_metrics.get('precision', 0):.3f}, "
                                     f"Recall: {training_metrics.get('recall', 0):.3f}, "
                                     f"F1: {training_metrics.get('f1_score', 0):.3f}")
            else:
                print_info(f"Accuracy: {training_metrics.get('accuracy', 0):.3f}, "
                          f"Precision: {training_metrics.get('precision', 0):.3f}, "
                          f"Recall: {training_metrics.get('recall', 0):.3f}, "
                          f"F1: {training_metrics.get('f1_score', 0):.3f}")
            
            # Save model
            version_id = model_manager.save_model(predictor, training_metrics)
            
            if log_callback:
                log_callback("success", f"Model saved, version: {version_id}")
            else:
                print_success(f"Model saved, version: {version_id}")
            
            trained_count += 1
            
            # Store metrics
            metrics["strategies"][strategy] = {
                "samples": len(X),
                "features": len(X.columns),
                "version_id": version_id,
                "cv_score": predictor.cv_score,
                "training_metrics": training_metrics,
                "label_distribution": dict(label_dist),
                "symbols_count": len(symbols)
            }
            metrics["total_samples"] += len(X)
            
            # Log top features
            top_features = predictor.get_top_features(5)
            if top_features:
                features_str = ', '.join([f"{f[0]}={f[1]:.3f}" for f in top_features])
                if log_callback:
                    log_callback("info", f"Top features: {features_str}")
                else:
                    print_info(f"Top features: {features_str}")
            
        except Exception as e:
            error_msg = f"Error training {strategy} model: {e}"
            if log_callback:
                log_callback("error", error_msg)
            else:
                print_error(error_msg)
            metrics["strategies"][strategy] = {"error": str(e)}
            actual_errors.append(error_msg)
            continue
    
    # Determine success
    success = len(actual_errors) == 0
    has_data = trained_count > 0
    
    metrics["trained_count"] = trained_count
    metrics["total_strategies"] = len(strategies)
    metrics["has_data"] = has_data
    metrics["errors"] = actual_errors
    
    if no_data_count == len(strategies):
        metrics["no_data_reason"] = "No price history data available for any strategy"
    elif no_data_count > 0:
        metrics["no_data_reason"] = f"{no_data_count} strategies skipped due to insufficient data"
    
    summary = f"Trained {trained_count}/{len(strategies)} trading models"
    if log_callback:
        log_callback("success" if has_data else "warning", summary)
    else:
        (print_success if has_data else print_warning)(summary)
    
    return success, metrics


def main():
    """Main trading training pipeline."""
    print_header("Arbihawk Trading Training Pipeline")
    
    # Check if trading is enabled
    trading_config = getattr(config, 'TRADING_CONFIG', {})
    if not trading_config.get('enabled', False):
        print_warning("Trading is disabled in config. Enable it to train trading models.")
        print_info("Set trading.enabled = true in config/config.json")
        return 1
    
    # Check if we have price data
    db = Database()
    price_history = db.get_price_history(limit=10)
    
    if price_history.empty:
        print_warning("No price history in database. Please run trading data collection first.")
        print_info("Use: Run 'Trading: Collect Data' from VSCode tasks or dashboard")
        return 1
    
    unique_symbols = price_history['symbol'].nunique()
    print_info(f"Found price history for {unique_symbols} symbols")
    
    # Train models
    success, metrics = train_trading_models(db)
    
    if not success:
        print_error("\nTrading model training failed. Check errors above.")
        return 1
    
    if not metrics.get('has_data', False):
        print_warning("\nNo models trained due to insufficient data.")
        if metrics.get('no_data_reason'):
            print_info(f"Reason: {metrics['no_data_reason']}")
        return 1
    
    print_header("Trading Training Complete!")
    print_success(f"Successfully trained {metrics.get('trained_count', 0)} models!")
    
    # Summary
    for strategy, data in metrics.get('strategies', {}).items():
        if 'error' not in data and not data.get('skipped', False):
            print_info(f"  {strategy}: accuracy={data.get('training_metrics', {}).get('accuracy', 0):.3f}, "
                      f"samples={data.get('samples', 0)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
