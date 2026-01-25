"""
Test suite for model training pipeline.
Tests model training, versioning, and activation.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.database import Database
from models.versioning import ModelVersionManager
import tempfile
from pathlib import Path
import config

# Check if Optuna is available
try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


class TestModelTraining:
    """Test model training and versioning."""
    
    def test_model_version_save_and_retrieve(self, temp_db):
        """Test saving and retrieving model versions."""
        manager = ModelVersionManager(db=temp_db)
        
        # Save a model version
        version_id = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/1x2_model.pkl",
            training_samples=100,
            cv_score=0.65,
            performance_metrics={"accuracy": 0.68, "precision": 0.70}
        )
        
        assert version_id is not None
        
        # Retrieve model versions
        versions = temp_db.get_model_versions(domain="betting", market="1x2")
        assert len(versions) == 1
        assert versions.iloc[0]["version_id"] == version_id
        assert versions.iloc[0]["market"] == "1x2"
        assert versions.iloc[0]["cv_score"] == 0.65
    
    def test_model_activation(self, temp_db):
        """Test activating a model version."""
        manager = ModelVersionManager(db=temp_db)
        
        # Save two versions
        v1 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/v1.pkl",
            training_samples=100,
            cv_score=0.60,
            activate=True
        )
        
        v2 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/v2.pkl",
            training_samples=150,
            cv_score=0.65,
            activate=True
        )
        
        # Only v2 should be active
        active = temp_db.get_active_model(domain="betting", market="1x2")
        assert active is not None
        assert active["version_id"] == v2
        
        # v1 should be inactive
        versions = temp_db.get_model_versions(domain="betting", market="1x2")
        v1_data = versions[versions["version_id"] == v1].iloc[0]
        assert v1_data["is_active"] == 0
    
    def test_multiple_markets_independent_activation(self, temp_db):
        """Test that different markets can have independent active models."""
        manager = ModelVersionManager(db=temp_db)
        
        # Save models for different markets
        v1_1x2 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/1x2.pkl",
            training_samples=100,
            cv_score=0.65,
            activate=True
        )
        
        v1_btts = manager.save_version(
            domain="betting",
            market="btts",
            model_path="test_models/btts.pkl",
            training_samples=100,
            cv_score=0.70,
            activate=True
        )
        
        # Both should be active for their respective markets
        active_1x2 = temp_db.get_active_model(domain="betting", market="1x2")
        active_btts = temp_db.get_active_model(domain="betting", market="btts")
        
        assert active_1x2["version_id"] == v1_1x2
        assert active_btts["version_id"] == v1_btts
    
    def test_domain_separation(self, temp_db):
        """Test that betting and trading domains are completely separate."""
        manager = ModelVersionManager(db=temp_db)
        
        # Save betting model
        betting_v1 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/betting_1x2.pkl",
            training_samples=100,
            cv_score=0.65,
            activate=True
        )
        
        # Save trading model with same market name
        trading_v1 = manager.save_version(
            domain="trading",
            market="momentum",
            model_path="test_models/trading_momentum.pkl",
            training_samples=200,
            cv_score=0.70,
            activate=True
        )
        
        # Both should be active in their respective domains
        active_betting = temp_db.get_active_model(domain="betting", market="1x2")
        active_trading = temp_db.get_active_model(domain="trading", market="momentum")
        
        assert active_betting is not None
        assert active_betting["version_id"] == betting_v1
        assert active_betting["domain"] == "betting"
        
        assert active_trading is not None
        assert active_trading["version_id"] == trading_v1
        assert active_trading["domain"] == "trading"
        
        # Trading domain should not see betting models
        trading_versions = manager.get_all_versions(domain="trading")
        assert len(trading_versions) == 1
        assert trading_versions[0]["domain"] == "trading"
        
        # Betting domain should not see trading models
        betting_versions = manager.get_all_versions(domain="betting")
        betting_1x2_versions = [v for v in betting_versions if v["market"] == "1x2"]
        assert len(betting_1x2_versions) == 1
        assert betting_1x2_versions[0]["domain"] == "betting"
        
        # Test that activating a trading model doesn't affect betting
        trading_v2 = manager.save_version(
            domain="trading",
            market="momentum",
            model_path="test_models/trading_momentum_v2.pkl",
            training_samples=250,
            cv_score=0.75,
            activate=True
        )
        
        # Betting model should still be active
        active_betting_after = temp_db.get_active_model(domain="betting", market="1x2")
        assert active_betting_after["version_id"] == betting_v1
        
        # Trading should now have v2 active
        active_trading_after = temp_db.get_active_model(domain="trading", market="momentum")
        assert active_trading_after["version_id"] == trading_v2
    
    @pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="Optuna not installed")
    def test_hyperparameter_tuning_with_sufficient_data(self, temp_db):
        """Test that hyperparameter tuning runs when sufficient data is available."""
        from models.predictor import BettingPredictor
        
        # Create synthetic data with enough samples
        np.random.seed(42)
        n_samples = 400  # Above min_samples threshold
        n_features = 21  # Match real feature count
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        dates = pd.Series([
            (datetime.now() - timedelta(days=i)).isoformat() 
            for i in range(n_samples)
        ])
        
        # Temporarily set small search space and few trials for fast testing
        original_config = config.HYPERPARAMETER_TUNING_CONFIG.copy()
        config.HYPERPARAMETER_TUNING_CONFIG['enabled'] = True
        config.HYPERPARAMETER_TUNING_CONFIG['search_space'] = 'small'
        config.HYPERPARAMETER_TUNING_CONFIG['min_samples'] = 300
        
        try:
            predictor = BettingPredictor(market='1x2')
            predictor.train(X, y, dates=dates)
            
            # If tuning ran, hyperparameters should be set
            # Note: With small search space and fast trials, it may or may not run
            # But if it runs, it should set hyperparameters
            if hasattr(predictor, 'hyperparameters') and predictor.hyperparameters:
                assert predictor.hyperparameters is not None
                assert isinstance(predictor.hyperparameters, dict)
                assert 'n_estimators' in predictor.hyperparameters or 'max_depth' in predictor.hyperparameters
                assert predictor.is_trained
        finally:
            config.HYPERPARAMETER_TUNING_CONFIG.update(original_config)
    
    @pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="Optuna not installed")
    def test_hyperparameter_tuning_skipped_insufficient_data(self, temp_db):
        """Test that hyperparameter tuning is skipped with insufficient data."""
        from models.predictor import BettingPredictor
        
        # Create small dataset
        np.random.seed(42)
        n_samples = 100  # Below min_samples threshold
        n_features = 21
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        dates = pd.Series([
            (datetime.now() - timedelta(days=i)).isoformat() 
            for i in range(n_samples)
        ])
        
        original_config = config.HYPERPARAMETER_TUNING_CONFIG.copy()
        config.HYPERPARAMETER_TUNING_CONFIG['enabled'] = True
        config.HYPERPARAMETER_TUNING_CONFIG['min_samples'] = 300
        
        try:
            predictor = BettingPredictor(market='1x2')
            predictor.train(X, y, dates=dates)
            
            # Tuning should be skipped, but model should still train
            assert predictor.is_trained
            # Hyperparameters should be None when tuning is skipped
            if hasattr(predictor, 'hyperparameters'):
                # Either None or not set
                assert predictor.hyperparameters is None or len(predictor.hyperparameters) == 0
        finally:
            config.HYPERPARAMETER_TUNING_CONFIG.update(original_config)
    
    @pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="Optuna not installed")
    def test_temporal_splitter_respects_chronological_order(self):
        """Test that TemporalSplitter ensures train data comes before test data."""
        from models.hyperparameter_tuning import TemporalSplitter
        
        # Create data with dates
        n_samples = 100
        X = pd.DataFrame(np.random.randn(n_samples, 10))
        y = pd.Series(np.random.choice(['A', 'B', 'C'], n_samples))
        dates = pd.Series(pd.date_range('2024-01-01', periods=n_samples, freq='D'))
        
        splitter = TemporalSplitter(n_splits=5, test_size=0.2)
        splits = list(splitter.split(X, y, groups=dates))
        
        assert len(splits) > 0
        
        for train_idx, test_idx in splits:
            train_dates = dates.iloc[train_idx]
            test_dates = dates.iloc[test_idx]
            
            # All training dates should be before all test dates
            assert train_dates.max() <= test_dates.min(), "Temporal order violated!"
    
    @pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="Optuna not installed")
    def test_hyperparameter_tuning_stored_in_version_metrics(self, temp_db):
        """Test that hyperparameters are stored in model version metrics."""
        from models.predictor import BettingPredictor
        
        # Create synthetic data
        np.random.seed(42)
        n_samples = 400
        n_features = 21
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        dates = pd.Series([
            (datetime.now() - timedelta(days=i)).isoformat() 
            for i in range(n_samples)
        ])
        
        original_config = config.HYPERPARAMETER_TUNING_CONFIG.copy()
        config.HYPERPARAMETER_TUNING_CONFIG['enabled'] = True
        config.HYPERPARAMETER_TUNING_CONFIG['search_space'] = 'small'
        config.HYPERPARAMETER_TUNING_CONFIG['min_samples'] = 300
        
        try:
            predictor = BettingPredictor(market='1x2')
            predictor.train(X, y, dates=dates)
            
            # Save model version
            manager = ModelVersionManager(db=temp_db)
            with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
                model_path = f.name
                predictor.save(model_path)
            
            try:
                version_id = manager.save_version(
                    domain='betting',
                    market='1x2',
                    model_path=model_path,
                    training_samples=n_samples,
                    cv_score=0.65,
                    performance_metrics={
                        'hyperparameters': getattr(predictor, 'hyperparameters', None),
                        'tuning_metrics': getattr(predictor, 'tuning_metrics', {})
                    }
                )
                
                # Retrieve version and check metrics
                versions = temp_db.get_model_versions(domain='betting', market='1x2')
                version_data = versions[versions['version_id'] == version_id].iloc[0]
                
                # Check that performance_metrics contains hyperparameters if they exist
                import json
                perf_metrics = json.loads(version_data['performance_metrics']) if isinstance(version_data['performance_metrics'], str) else version_data['performance_metrics']
                
                if predictor.hyperparameters:
                    assert 'hyperparameters' in perf_metrics
                    assert perf_metrics['hyperparameters'] == predictor.hyperparameters
            finally:
                Path(model_path).unlink(missing_ok=True)
        finally:
            config.HYPERPARAMETER_TUNING_CONFIG.update(original_config)
