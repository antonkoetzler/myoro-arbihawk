"""
Metrics collection system for tracking system performance.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from data.database import Database
import config


class MetricsCollector:
    """
    Collects and stores metrics for all system components.
    
    Tracks:
    - Ingestion metrics (success rate, records processed)
    - Matching metrics (match rate, unmatched count)
    - Model metrics (accuracy, CV scores)
    - Betting metrics (ROI, win rate)
    
    Example usage:
        collector = MetricsCollector()
        
        # Record a metric
        collector.record("ingestion", "records_processed", 150)
        
        # Get recent metrics
        metrics = collector.get_metrics("betting", days=7)
    """
    
    METRIC_TYPES = ["ingestion", "matching", "model", "betting"]
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.retention_months = config.METRICS_CONFIG.get("retention_months", 18)
    
    def record(self, metric_type: str, metric_name: str, value: float,
               metadata: Optional[Dict] = None) -> int:
        """
        Record a metric value.
        
        Args:
            metric_type: Type of metric (ingestion/matching/model/betting)
            metric_name: Name of the metric
            value: Metric value
            metadata: Optional additional data
            
        Returns:
            Metric record ID
        """
        return self.db.insert_metric(metric_type, metric_name, value, metadata)
    
    def record_ingestion(self, source: str, records: int, success: bool,
                         duration_ms: Optional[float] = None) -> None:
        """
        Record ingestion metrics.
        
        Args:
            source: Data source (betano/fbref)
            records: Number of records processed
            success: Whether ingestion succeeded
            duration_ms: Processing time in milliseconds
        """
        metadata = {
            "source": source,
            "success": success,
            "duration_ms": duration_ms
        }
        
        self.record("ingestion", f"records_{source}", records, metadata)
        self.record("ingestion", f"success_{source}", 1 if success else 0, metadata)
        
        if duration_ms:
            self.record("ingestion", f"duration_{source}", duration_ms, metadata)
    
    def record_matching(self, total: int, matched: int, unmatched: int,
                        duration_ms: Optional[float] = None) -> None:
        """
        Record score matching metrics.
        
        Args:
            total: Total scores processed
            matched: Number matched
            unmatched: Number unmatched
            duration_ms: Processing time
        """
        match_rate = matched / total if total > 0 else 0
        
        metadata = {
            "total": total,
            "matched": matched,
            "unmatched": unmatched
        }
        
        self.record("matching", "total_processed", total, metadata)
        self.record("matching", "matched", matched, metadata)
        self.record("matching", "unmatched", unmatched, metadata)
        self.record("matching", "match_rate", match_rate, metadata)
        
        if duration_ms:
            self.record("matching", "duration", duration_ms, metadata)
    
    def record_model(self, market: str, cv_score: float,
                     training_samples: int, accuracy: Optional[float] = None,
                     version_id: Optional[int] = None) -> None:
        """
        Record model training metrics.
        
        Args:
            market: Market type
            cv_score: Cross-validation score
            training_samples: Number of training samples
            accuracy: Model accuracy (optional)
            version_id: Model version ID
        """
        metadata = {
            "market": market,
            "training_samples": training_samples,
            "version_id": version_id
        }
        
        self.record("model", f"cv_score_{market}", cv_score, metadata)
        self.record("model", f"samples_{market}", training_samples, metadata)
        
        if accuracy is not None:
            self.record("model", f"accuracy_{market}", accuracy, metadata)
    
    def record_betting(self, roi: float, win_rate: float, total_bets: int,
                       profit: float) -> None:
        """
        Record betting performance metrics.
        
        Args:
            roi: Return on investment
            win_rate: Win rate
            total_bets: Total bets placed
            profit: Total profit/loss
        """
        metadata = {
            "total_bets": total_bets
        }
        
        self.record("betting", "roi", roi, metadata)
        self.record("betting", "win_rate", win_rate, metadata)
        self.record("betting", "total_bets", total_bets, metadata)
        self.record("betting", "profit", profit, metadata)
    
    def get_metrics(self, metric_type: Optional[str] = None,
                    metric_name: Optional[str] = None,
                    days: int = 30,
                    limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get metrics with optional filtering.
        
        Args:
            metric_type: Filter by type
            metric_name: Filter by name
            days: Number of days to look back
            limit: Maximum records to return
            
        Returns:
            List of metric records
        """
        from_date = (datetime.now() - 
                    datetime.timedelta(days=days) if hasattr(datetime, 'timedelta') 
                    else datetime.now()).isoformat()
        
        # Import timedelta properly
        from datetime import timedelta
        from_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        df = self.db.get_metrics(
            metric_type=metric_type,
            metric_name=metric_name,
            from_date=from_date,
            limit=limit
        )
        
        return df.to_dict('records') if len(df) > 0 else []
    
    def get_latest(self, metric_type: str, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Get most recent value for a metric.
        
        Args:
            metric_type: Metric type
            metric_name: Metric name
            
        Returns:
            Most recent metric record or None
        """
        df = self.db.get_metrics(
            metric_type=metric_type,
            metric_name=metric_name,
            limit=1
        )
        
        if len(df) > 0:
            return df.iloc[0].to_dict()
        
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.
        
        Returns:
            Dict with summary for each metric type
        """
        summary = {}
        
        for metric_type in self.METRIC_TYPES:
            metrics = self.get_metrics(metric_type=metric_type, days=1, limit=100)
            
            summary[metric_type] = {
                "count": len(metrics),
                "latest": metrics[0] if metrics else None
            }
        
        return summary
    
    def cleanup_old_metrics(self) -> int:
        """
        Remove metrics older than retention period.
        
        Returns:
            Number of records deleted
        """
        return self.db.cleanup_old_metrics(self.retention_months)
