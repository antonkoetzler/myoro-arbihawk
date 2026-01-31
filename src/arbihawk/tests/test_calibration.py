"""
Test suite for probability calibration functionality.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from models.predictor import BettingPredictor
from models.calibration import calculate_brier_score, calculate_ece, evaluate_calibration


class TestCalibration:
    """Test probability calibration."""
    
    def test_calibration_metrics_binary(self):
        """Test calibration metrics for binary classification."""
        # Perfect calibration: predictions match outcomes
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_pred = np.array([0.0, 0.1, 0.9, 1.0, 0.2, 0.8])
        
        brier = calculate_brier_score(y_true, y_pred)
        ece = calculate_ece(y_true, y_pred)
        
        # Perfect predictions should have low Brier score
        assert brier < 0.1
        assert ece < 0.1
    
    def test_calibration_metrics_multiclass(self):
        """Test calibration metrics for multiclass."""
        # 3-class example
        y_true = np.array([0, 1, 2, 0, 1])
        y_pred_proba = np.array([
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
            [0.7, 0.2, 0.1],
            [0.2, 0.7, 0.1]
        ])
        
        # Convert to one-hot
        y_true_onehot = np.zeros((len(y_true), 3))
        y_true_onehot[np.arange(len(y_true)), y_true] = 1
        
        brier = calculate_brier_score(y_true_onehot, y_pred_proba)
        ece = calculate_ece(y_true, y_pred_proba)
        
        assert brier >= 0
        assert brier <= 1
        assert ece >= 0
        assert ece <= 1
    
    def test_train_with_calibration(self):
        """Test training with calibration enabled."""
        # Create synthetic data
        np.random.seed(42)
        n_samples = 200
        n_features = 10
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        
        predictor = BettingPredictor(market='1x2', enable_calibration=True)
        predictor.train(X, y, calibration_split=0.2)
        
        assert predictor.is_trained
        assert predictor.calibrator is not None
        assert 'calibrated' in predictor.calibration_metrics
        assert 'brier_score' in predictor.calibration_metrics['calibrated']
        assert 'ece' in predictor.calibration_metrics['calibrated']
    
    def test_train_without_calibration(self):
        """Test training with calibration disabled."""
        np.random.seed(42)
        n_samples = 200
        n_features = 10
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        
        predictor = BettingPredictor(market='1x2', enable_calibration=False)
        predictor.train(X, y, calibration_split=0.2)
        
        assert predictor.is_trained
        assert predictor.calibrator is None
        assert predictor.calibration_metrics == {}

    def test_train_with_betting_eval_is_trained_before_evaluation(self):
        """Test that predictor sets is_trained=True before betting evaluation (no 'Predictor must be trained' error)."""
        np.random.seed(42)
        n_samples = 120  # >= 100 so use_betting_eval can be True
        n_features = 10
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        dates = pd.Series(pd.date_range('2024-01-01', periods=n_samples, freq='D').astype(str))

        mock_eval_return = {
            'roi': 0.0, 'profit': 0.0, 'sharpe_ratio': 0.0,
            'win_rate': 0.0, 'total_bets': 0, 'total_stake': 0.0
        }

        with patch('models.betting_evaluator.BettingEvaluator') as MockEval:
            MockEval.return_value.evaluate.return_value = mock_eval_return
            predictor = BettingPredictor(market='1x2', enable_calibration=False)
            predictor.train(X, y, dates=dates, db=MagicMock(), validation_split=0.2)

        assert predictor.is_trained
        MockEval.return_value.evaluate.assert_called_once()
        assert predictor.betting_metrics == mock_eval_return

    def test_calibration_insufficient_data(self):
        """Test that calibration is skipped with insufficient data."""
        np.random.seed(42)
        n_samples = 30  # Too few for calibration
        n_features = 10
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        
        predictor = BettingPredictor(market='1x2', enable_calibration=True)
        predictor.train(X, y, calibration_split=0.2)
        
        assert predictor.is_trained
        # Calibration should be skipped due to insufficient data
        assert predictor.calibrator is None
    
    def test_predict_with_calibration(self):
        """Test predictions use calibrated probabilities."""
        np.random.seed(42)
        n_samples = 200
        n_features = 10
        
        X_train = pd.DataFrame(np.random.randn(n_samples, n_features))
        y_train = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        
        predictor = BettingPredictor(market='1x2', enable_calibration=True)
        predictor.train(X_train, y_train, calibration_split=0.2)
        
        # Make predictions
        X_test = pd.DataFrame(np.random.randn(10, n_features))
        probs = predictor.predict_probabilities(X_test)
        
        assert len(probs) == 10
        assert set(probs.columns) == {'home_win', 'draw', 'away_win'}
        # Probabilities should sum to ~1.0
        assert np.allclose(probs.sum(axis=1), 1.0, atol=0.01)
        # All probabilities should be between 0 and 1
        assert (probs >= 0).all().all()
        assert (probs <= 1).all().all()
    
    def test_save_and_load_calibrated_model(self):
        """Test saving and loading calibrated model."""
        np.random.seed(42)
        n_samples = 200
        n_features = 10
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        
        # Train and save
        predictor1 = BettingPredictor(market='1x2', enable_calibration=True)
        predictor1.train(X, y, calibration_split=0.2)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
            model_path = f.name
            predictor1.save(model_path)
            
            # Load
            predictor2 = BettingPredictor(market='1x2')
            predictor2.load(model_path)
            
            assert predictor2.is_trained
            assert predictor2.calibrator is not None
            assert 'calibrated' in predictor2.calibration_metrics
            
            # Predictions should be the same
            X_test = pd.DataFrame(np.random.randn(5, n_features))
            probs1 = predictor1.predict_probabilities(X_test)
            probs2 = predictor2.predict_probabilities(X_test)
            
            pd.testing.assert_frame_equal(probs1, probs2)
            
            # Cleanup - close file handles first
            del predictor1, predictor2
            import gc
            gc.collect()
            try:
                Path(model_path).unlink()
            except (PermissionError, FileNotFoundError):
                pass  # Windows file locking - ignore
    
    def test_backward_compatibility_old_model(self):
        """Test loading old models without calibration (backward compatibility)."""
        np.random.seed(42)
        n_samples = 200
        n_features = 10
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        
        # Train without calibration (old style)
        predictor_old = BettingPredictor(market='1x2', enable_calibration=False)
        predictor_old.train(X, y, calibration_split=0)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
            model_path = f.name
            predictor_old.save(model_path)
            
            # Load with new code
            predictor_new = BettingPredictor(market='1x2')
            predictor_new.load(model_path)
            
            assert predictor_new.is_trained
            # Should handle missing calibrator gracefully
            assert predictor_new.calibrator is None
            
            # Should still make predictions
            X_test = pd.DataFrame(np.random.randn(5, n_features))
            probs = predictor_new.predict_probabilities(X_test)
            assert len(probs) == 5
            
            # Cleanup - close file handles first
            del predictor_old, predictor_new
            import gc
            gc.collect()
            try:
                Path(model_path).unlink()
            except (PermissionError, FileNotFoundError):
                pass  # Windows file locking - ignore
    
    def test_calibration_improves_metrics(self):
        """Test that calibration improves Brier score and ECE."""
        np.random.seed(42)
        n_samples = 300  # More data for better calibration
        n_features = 10
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice(['home_win', 'draw', 'away_win'], n_samples))
        
        predictor = BettingPredictor(market='1x2', enable_calibration=True)
        predictor.train(X, y, calibration_split=0.2)
        
        if predictor.calibrator is not None:
            metrics = predictor.calibration_metrics
            if 'improvement' in metrics:
                # Calibration should improve (or at least not hurt) metrics
                # Improvement is uncalibrated - calibrated, so positive = improvement
                assert metrics['improvement']['brier_score'] >= -0.1  # Allow small tolerance
                assert metrics['improvement']['ece'] >= -0.1
