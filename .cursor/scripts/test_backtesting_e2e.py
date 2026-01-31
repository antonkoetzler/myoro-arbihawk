"""End-to-end tests for backtesting framework."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "arbihawk"))

from data.database import Database
from backtesting.backtest import BacktestEngine, BacktestResult
from automation.runner import run_backtest
from automation.scheduler import AutomationScheduler


def test_imports():
    """Test that all imports work."""
    print("[OK] Testing imports...")
    try:
        from backtesting.backtest import BacktestEngine, BacktestResult
        from backtesting.runner import main
        print("  [OK] All imports successful")
        return True
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        return False


def test_database_integration():
    """Test database integration."""
    print("[OK] Testing database integration...")
    try:
        db = Database()
        fixtures = db.get_fixtures()
        scores = db.get_scores()
        odds = db.get_odds()
        if len(odds) > 10:
            odds = odds.head(10)
        
        print(f"  [OK] Database accessible: {len(fixtures)} fixtures, {len(scores)} scores, {len(odds)} odds")
        
        # Test odds filtering
        if len(odds) > 0:
            test_fixture = odds.iloc[0]['fixture_id']
            filtered_odds = db.get_odds(fixture_id=test_fixture, before_date="2025-12-31")
            print(f"  [OK] Odds filtering works: {len(filtered_odds)} odds for fixture")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backtest_engine_creation():
    """Test BacktestEngine can be created."""
    print("[OK] Testing BacktestEngine creation...")
    try:
        engine = BacktestEngine(ev_threshold=0.05)
        print(f"  [OK] Engine created with EV threshold: {engine.ev_threshold}")
        return True
    except Exception as e:
        print(f"  [FAIL] Engine creation failed: {e}")
        return False


def test_automation_integration():
    """Test automation runner integration."""
    print("[OK] Testing automation integration...")
    try:
        # Test that backtest mode is available
        scheduler = AutomationScheduler()
        print("  [OK] Scheduler created")
        
        # Test trigger_backtest method exists
        if hasattr(scheduler, 'trigger_backtest'):
            print("  [OK] trigger_backtest method exists")
        else:
            print("  [FAIL] trigger_backtest method missing")
            return False
        
        return True
    except Exception as e:
        print(f"  [FAIL] Automation integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_runner_integration():
    """Test runner integration."""
    print("[OK] Testing runner integration...")
    try:
        # Test that run_backtest function exists
        from automation.runner import run_backtest
        print("  [OK] run_backtest function imported")
        return True
    except Exception as e:
        print(f"  [FAIL] Runner integration test failed: {e}")
        return False


def test_small_backtest():
    """Test running a small backtest if data is available."""
    print("[OK] Testing small backtest execution...")
    try:
        db = Database()
        fixtures = db.get_fixtures()
        scores = db.get_scores()
        
        if len(fixtures) == 0 or len(scores) == 0:
            print("  [SKIP] Skipping: No data in database")
            return True
        
        completed = fixtures.merge(scores, on='fixture_id', how='inner')
        if len(completed) < 20:
            print("  [SKIP] Skipping: Not enough completed matches (< 20)")
            return True
        
        # Use actual date range from data
        import pandas as pd
        completed_sorted = completed.sort_values('start_time')
        first_date = completed_sorted.iloc[0]['start_time']
        last_date = completed_sorted.iloc[-1]['start_time']
        
        first_dt = pd.to_datetime(first_date)
        last_dt = pd.to_datetime(last_date)
        
        # Small test: use first 60% for training, last 40% for testing
        split_point = first_dt + (last_dt - first_dt) * 0.6
        
        train_start = first_dt.strftime('%Y-%m-%d')
        test_start = split_point.strftime('%Y-%m-%d')
        test_end = last_dt.strftime('%Y-%m-%d')
        
        engine = BacktestEngine(ev_threshold=0.01)  # Low threshold for testing
        result = engine.run_backtest(
            train_start=train_start,
            test_start=test_start,
            test_end=test_end,
            period_days=30,
            min_training_samples=10  # Lower threshold for testing
        )
        
        print(f"  [OK] Backtest completed: {result.overall_metrics.get('total_bets', 0)} bets")
        print(f"    ROI: {result.overall_metrics.get('roi', 0):.2%}")
        print(f"    Win rate: {result.overall_metrics.get('win_rate', 0):.2%}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Backtest execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all E2E tests."""
    print("=" * 60)
    print("Backtesting Framework E2E Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_database_integration,
        test_backtest_engine_creation,
        test_automation_integration,
        test_runner_integration,
        test_small_backtest
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  [FAIL] Test {test.__name__} crashed: {e}")
            results.append(False)
        print()
    
    print("=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
