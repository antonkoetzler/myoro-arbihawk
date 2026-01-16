"""
Metrics reporting for human-readable output.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .metrics import MetricsCollector


class MetricsReporter:
    """
    Generates human-readable reports from metrics.
    
    Example usage:
        reporter = MetricsReporter()
        
        # Print summary report
        report = reporter.generate_summary()
        reporter.print_report(report)
    """
    
    def __init__(self, collector: Optional[MetricsCollector] = None):
        self.collector = collector or MetricsCollector()
    
    def generate_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Generate summary report for recent period.
        
        Args:
            days: Number of days to include
            
        Returns:
            Summary report dict
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "sections": {}
        }
        
        # Ingestion summary
        ingestion_metrics = self.collector.get_metrics("ingestion", days=days)
        if ingestion_metrics:
            records_total = sum(m['value'] for m in ingestion_metrics 
                               if 'records' in m.get('metric_name', ''))
            success_total = sum(m['value'] for m in ingestion_metrics 
                               if 'success' in m.get('metric_name', ''))
            
            report["sections"]["ingestion"] = {
                "total_records": records_total,
                "success_count": success_total,
                "metric_count": len(ingestion_metrics)
            }
        
        # Matching summary
        matching_metrics = self.collector.get_metrics("matching", days=days)
        if matching_metrics:
            match_rates = [m['value'] for m in matching_metrics 
                          if m.get('metric_name') == 'match_rate']
            
            report["sections"]["matching"] = {
                "avg_match_rate": sum(match_rates) / len(match_rates) if match_rates else 0,
                "metric_count": len(matching_metrics)
            }
        
        # Model summary
        model_metrics = self.collector.get_metrics("model", days=days)
        if model_metrics:
            cv_scores = {}
            for m in model_metrics:
                if 'cv_score' in m.get('metric_name', ''):
                    market = m.get('metric_name', '').replace('cv_score_', '')
                    cv_scores[market] = m['value']
            
            report["sections"]["model"] = {
                "cv_scores": cv_scores,
                "metric_count": len(model_metrics)
            }
        
        # Betting summary
        betting_metrics = self.collector.get_metrics("betting", days=days)
        if betting_metrics:
            latest_roi = None
            latest_win_rate = None
            
            for m in betting_metrics:
                if m.get('metric_name') == 'roi':
                    latest_roi = m['value']
                    break
            
            for m in betting_metrics:
                if m.get('metric_name') == 'win_rate':
                    latest_win_rate = m['value']
                    break
            
            report["sections"]["betting"] = {
                "latest_roi": latest_roi,
                "latest_win_rate": latest_win_rate,
                "metric_count": len(betting_metrics)
            }
        
        return report
    
    def generate_betting_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate detailed betting performance report.
        
        Args:
            days: Number of days to include
            
        Returns:
            Betting report dict
        """
        metrics = self.collector.get_metrics("betting", days=days)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "data": {
                "roi": [],
                "win_rate": [],
                "profit": [],
                "total_bets": []
            }
        }
        
        for m in metrics:
            metric_name = m.get('metric_name', '')
            if metric_name in report["data"]:
                report["data"][metric_name].append({
                    "timestamp": m.get('timestamp'),
                    "value": m.get('value')
                })
        
        # Calculate summary
        if report["data"]["roi"]:
            roi_values = [x['value'] for x in report["data"]["roi"]]
            report["summary"] = {
                "current_roi": roi_values[0] if roi_values else 0,
                "avg_roi": sum(roi_values) / len(roi_values),
                "max_roi": max(roi_values),
                "min_roi": min(roi_values)
            }
        
        return report
    
    def format_console(self, report: Dict[str, Any]) -> str:
        """
        Format report for console output.
        
        Args:
            report: Report dict
            
        Returns:
            Formatted string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("METRICS REPORT")
        lines.append(f"Generated: {report.get('generated_at', 'N/A')}")
        lines.append(f"Period: {report.get('period_days', 'N/A')} days")
        lines.append("=" * 60)
        
        sections = report.get("sections", {})
        
        if "ingestion" in sections:
            lines.append("\n📥 INGESTION")
            s = sections["ingestion"]
            lines.append(f"  Total records: {s.get('total_records', 0):,}")
            lines.append(f"  Success count: {s.get('success_count', 0):,}")
        
        if "matching" in sections:
            lines.append("\n🔗 MATCHING")
            s = sections["matching"]
            lines.append(f"  Avg match rate: {s.get('avg_match_rate', 0):.1%}")
        
        if "model" in sections:
            lines.append("\n🤖 MODEL")
            s = sections["model"]
            for market, score in s.get("cv_scores", {}).items():
                lines.append(f"  {market} CV score: {score:.4f}")
        
        if "betting" in sections:
            lines.append("\n💰 BETTING")
            s = sections["betting"]
            roi = s.get('latest_roi')
            win_rate = s.get('latest_win_rate')
            if roi is not None:
                lines.append(f"  ROI: {roi:.2%}")
            if win_rate is not None:
                lines.append(f"  Win rate: {win_rate:.1%}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def print_report(self, report: Dict[str, Any]) -> None:
        """Print formatted report to console."""
        print(self.format_console(report))
    
    def to_json(self, report: Dict[str, Any], pretty: bool = True) -> str:
        """
        Convert report to JSON string.
        
        Args:
            report: Report dict
            pretty: Use pretty printing
            
        Returns:
            JSON string
        """
        indent = 2 if pretty else None
        return json.dumps(report, indent=indent, default=str)
