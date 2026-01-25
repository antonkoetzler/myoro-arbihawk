"""
Calibration utilities for probability calibration and evaluation.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from sklearn.calibration import CalibratedClassifierCV, CalibrationDisplay
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def calculate_brier_score(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
    """
    Calculate Brier Score for probability predictions.
    
    Brier Score = mean((predicted_probability - actual_outcome)^2)
    Lower is better. Perfect calibration = 0.0
    
    Args:
        y_true: True binary labels (0 or 1) or one-hot encoded for multiclass
        y_pred_proba: Predicted probabilities (shape: [n_samples] for binary, 
                     [n_samples, n_classes] for multiclass)
    
    Returns:
        Brier Score (float)
    """
    y_true = np.asarray(y_true)
    y_pred_proba = np.asarray(y_pred_proba)
    
    # Handle binary case
    if y_pred_proba.ndim == 1:
        return np.mean((y_pred_proba - y_true) ** 2)
    
    # Handle multiclass case - use one-vs-rest approach
    # For each class, calculate Brier score
    if y_true.ndim == 1:
        # Convert to one-hot encoding
        n_classes = y_pred_proba.shape[1]
        y_true_onehot = np.zeros((len(y_true), n_classes))
        y_true_onehot[np.arange(len(y_true)), y_true] = 1
        y_true = y_true_onehot
    
    # Calculate Brier score for each class and average
    brier_scores = []
    for class_idx in range(y_pred_proba.shape[1]):
        class_true = y_true[:, class_idx]
        class_pred = y_pred_proba[:, class_idx]
        brier_scores.append(np.mean((class_pred - class_true) ** 2))
    
    return np.mean(brier_scores)


def calculate_ece(y_true: np.ndarray, y_pred_proba: np.ndarray, 
                  n_bins: int = 10) -> float:
    """
    Calculate Expected Calibration Error (ECE).
    
    ECE measures how well-calibrated probabilities are by binning predictions
    and comparing average predicted probability to actual frequency in each bin.
    
    Args:
        y_true: True binary labels (0 or 1) or class indices for multiclass
        y_pred_proba: Predicted probabilities (shape: [n_samples] for binary,
                     [n_samples, n_classes] for multiclass)
        n_bins: Number of bins for calibration (default: 10)
    
    Returns:
        Expected Calibration Error (float, 0-1, lower is better)
    """
    y_true = np.asarray(y_true)
    y_pred_proba = np.asarray(y_pred_proba)
    
    # Handle binary case
    if y_pred_proba.ndim == 1:
        return _calculate_ece_binary(y_true, y_pred_proba, n_bins)
    
    # Handle multiclass - use max probability (confidence) approach
    # Take the probability of the predicted class
    y_pred_class = np.argmax(y_pred_proba, axis=1)
    y_pred_conf = np.max(y_pred_proba, axis=1)
    y_true_class = y_true if y_true.ndim == 1 else np.argmax(y_true, axis=1)
    
    # Check if predicted class matches true class
    y_correct = (y_pred_class == y_true_class).astype(float)
    
    return _calculate_ece_binary(y_correct, y_pred_conf, n_bins)


def _calculate_ece_binary(y_true: np.ndarray, y_pred_proba: np.ndarray,
                          n_bins: int) -> float:
    """Calculate ECE for binary classification."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        # Find samples in this bin
        in_bin = (y_pred_proba > bin_lower) & (y_pred_proba <= bin_upper)
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            # Average predicted probability in this bin
            accuracy_in_bin = y_true[in_bin].mean()
            avg_confidence_in_bin = y_pred_proba[in_bin].mean()
            # Add to ECE
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
    
    return ece


def evaluate_calibration(y_true: np.ndarray, y_pred_proba: np.ndarray,
                        n_bins: int = 10) -> Dict[str, float]:
    """
    Evaluate calibration quality with multiple metrics.
    
    Args:
        y_true: True labels
        y_pred_proba: Predicted probabilities
        n_bins: Number of bins for ECE calculation
    
    Returns:
        Dictionary with calibration metrics:
        - brier_score: Brier Score (lower is better)
        - ece: Expected Calibration Error (lower is better)
    """
    brier = calculate_brier_score(y_true, y_pred_proba)
    ece = calculate_ece(y_true, y_pred_proba, n_bins)
    
    return {
        'brier_score': float(brier),
        'ece': float(ece)
    }


def create_calibrator(method: str = 'isotonic') -> Any:
    """
    Create a calibration method.
    
    Args:
        method: Calibration method ('isotonic' or 'platt')
            - 'isotonic': Isotonic regression (non-parametric, more flexible)
            - 'platt': Platt scaling (logistic regression, parametric)
    
    Returns:
        Calibrator instance
    """
    if method == 'isotonic':
        return IsotonicRegression(out_of_bounds='clip')
    elif method == 'platt':
        return LogisticRegression()
    else:
        raise ValueError(f"Unknown calibration method: {method}. Use 'isotonic' or 'platt'")


# Note: CalibratedClassifierCV is used directly in predictor.py
# This module provides utility functions for calibration evaluation
