"""
Model versioning system for tracking and managing model versions.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from data.database import Database
from data.backup import DatabaseBackup
import config


class ModelVersionManager:
    """
    Manages model versions with performance tracking and rollback.
    
    Features:
    - Store model versions with metadata
    - Track performance per version
    - Enable rollback to previous versions
    - Auto-rollback on performance degradation
    
    Example usage:
        manager = ModelVersionManager()
        
        # Save a new version
        version_id = manager.save_version(
            market="1x2",
            model_path="models/saved/1x2_model.pkl",
            training_samples=1000,
            cv_score=0.65
        )
        
        # Rollback if needed
        manager.rollback_to_version(previous_version_id)
    """
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.backup = DatabaseBackup(db_path=config.DB_PATH)
        
        versioning_config = config.MODEL_VERSIONING_CONFIG
        self.auto_rollback_enabled = versioning_config.get("auto_rollback_enabled", True)
        self.rollback_threshold = versioning_config.get("rollback_threshold", -10.0)
        self.rollback_evaluation_bets = versioning_config.get("rollback_evaluation_bets", 50)
        self.max_versions_to_keep = versioning_config.get("max_versions_to_keep", 10)
    
    def save_version(self, market: str, model_path: str,
                     training_samples: int, cv_score: float,
                     performance_metrics: Optional[Dict] = None,
                     activate: bool = True) -> int:
        """
        Save a new model version.
        
        Args:
            market: Market type (1x2, over_under, btts)
            model_path: Path to saved model file
            training_samples: Number of training samples
            cv_score: Cross-validation score
            performance_metrics: Additional metrics
            activate: Whether to activate this version
            
        Returns:
            Version ID
        """
        version_id = self.db.insert_model_version(
            market=market,
            model_path=model_path,
            training_samples=training_samples,
            cv_score=cv_score,
            performance_metrics=performance_metrics
        )
        
        if activate:
            self.db.set_active_model(version_id, market)
        
        # Cleanup old versions
        self._cleanup_old_versions(market)
        
        return version_id
    
    def get_active_version(self, market: str) -> Optional[Dict[str, Any]]:
        """
        Get active model version for a market.
        
        Args:
            market: Market type
            
        Returns:
            Active version info or None
        """
        return self.db.get_active_model(market)
    
    def get_all_versions(self, market: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all model versions.
        
        Args:
            market: Filter by market (optional)
            limit: Maximum versions to return
            
        Returns:
            List of version info dicts
        """
        df = self.db.get_model_versions(market=market, limit=limit)
        return df.to_dict('records') if len(df) > 0 else []
    
    def rollback_to_version(self, version_id: int) -> bool:
        """
        Rollback to a specific model version.
        
        Args:
            version_id: Version to activate
            
        Returns:
            True on success
        """
        versions = self.get_all_versions()
        version = next((v for v in versions if v['version_id'] == version_id), None)
        
        if not version:
            return False
        
        # Create backup before rollback
        self.backup.create_backup("pre_rollback")
        
        # Activate the version
        self.db.set_active_model(version_id, version['market'])
        
        return True
    
    def compare_versions(self, version_id_1: int, version_id_2: int) -> Dict[str, Any]:
        """
        Compare two model versions.
        
        Args:
            version_id_1: First version ID
            version_id_2: Second version ID
            
        Returns:
            Comparison dict
        """
        versions = self.get_all_versions()
        
        v1 = next((v for v in versions if v['version_id'] == version_id_1), None)
        v2 = next((v for v in versions if v['version_id'] == version_id_2), None)
        
        if not v1 or not v2:
            return {"error": "Version not found"}
        
        comparison = {
            "version_1": {
                "id": version_id_1,
                "cv_score": v1.get('cv_score'),
                "training_samples": v1.get('training_samples'),
                "trained_at": v1.get('trained_at'),
                "is_active": v1.get('is_active')
            },
            "version_2": {
                "id": version_id_2,
                "cv_score": v2.get('cv_score'),
                "training_samples": v2.get('training_samples'),
                "trained_at": v2.get('trained_at'),
                "is_active": v2.get('is_active')
            },
            "cv_score_diff": (v1.get('cv_score', 0) or 0) - (v2.get('cv_score', 0) or 0),
            "sample_diff": (v1.get('training_samples', 0) or 0) - (v2.get('training_samples', 0) or 0)
        }
        
        # Parse performance metrics if available
        for v_key, v_data in [("version_1", v1), ("version_2", v2)]:
            metrics_str = v_data.get('performance_metrics')
            if metrics_str:
                try:
                    comparison[v_key]["performance_metrics"] = json.loads(metrics_str)
                except:
                    pass
        
        return comparison
    
    def check_should_rollback(self, market: str) -> Optional[int]:
        """
        Check if current model should be rolled back.
        
        Uses betting performance to determine if the current model
        is underperforming compared to the previous version.
        
        Args:
            market: Market type
            
        Returns:
            Version ID to rollback to, or None if no rollback needed
        """
        if not self.auto_rollback_enabled:
            return None
        
        versions = self.get_all_versions(market=market, limit=5)
        
        if len(versions) < 2:
            return None
        
        current_version = versions[0]
        previous_version = versions[1]
        
        # Get betting stats
        stats = self.db.get_bankroll_stats()
        
        # Only check if we have enough settled bets
        if stats.get('settled_bets', 0) < self.rollback_evaluation_bets:
            return None
        
        # Get ROI
        current_roi = stats.get('roi', 0) * 100  # Convert to percentage
        
        # Check threshold
        if current_roi < self.rollback_threshold:
            return previous_version.get('version_id')
        
        return None
    
    def update_version_metrics(self, version_id: int,
                               performance_metrics: Dict) -> None:
        """
        Update performance metrics for a version.
        
        Args:
            version_id: Version ID
            performance_metrics: New metrics to store
        """
        # This would require adding an update method to database
        # For now, metrics are stored at creation time
        pass
    
    def get_best_version(self, market: str,
                         metric: str = "cv_score") -> Optional[Dict[str, Any]]:
        """
        Get best performing version for a market.
        
        Args:
            market: Market type
            metric: Metric to optimize ("cv_score" or from performance_metrics)
            
        Returns:
            Best version info or None
        """
        versions = self.get_all_versions(market=market)
        
        if not versions:
            return None
        
        if metric == "cv_score":
            best = max(versions, key=lambda v: v.get('cv_score', 0) or 0)
        else:
            # Try to find in performance_metrics
            def get_metric(v):
                metrics_str = v.get('performance_metrics')
                if metrics_str:
                    try:
                        metrics = json.loads(metrics_str)
                        return metrics.get(metric, 0)
                    except:
                        pass
                return 0
            
            best = max(versions, key=get_metric)
        
        return best
    
    def _cleanup_old_versions(self, market: str) -> int:
        """
        Remove old versions beyond max_versions_to_keep.
        
        Args:
            market: Market type
            
        Returns:
            Number of versions removed
        """
        # Note: This requires a delete method in database
        # For now, old versions are kept but not used
        return 0
