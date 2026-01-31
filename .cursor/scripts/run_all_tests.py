"""Run all tests for collection and training flows."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "arbihawk"))

def test_odds():
    """Test odds extraction."""
    print("=" * 60)
    print("TEST 1: Odds Extraction")
    print("=" * 60)
    
    try:
        from scrapers.src.sports_data.livescore import fetch_league_winner_odds
        lwo = fetch_league_winner_odds('KKay4EE8')
        print(f"✓ LiveScore league winner odds: {len(lwo) if lwo else 0} entries")
        return True
    except Exception as e:
        print(f"✗ LiveScore odds failed: {e}")
        return False

def test_training():
    """Test training flow."""
    print("\n" + "=" * 60)
    print("TEST 2: Training Flow")
    print("=" * 60)
    
    try:
        from data.database import Database
        from data.features import FeatureEngineer
        
        db = Database()
        fe = FeatureEngineer(db)
        
        X, y = fe.create_training_data('1x2')
        print(f"✓ Feature engineering: {len(X)} samples, {len(X.columns) if len(X) > 0 else 0} features")
        
        if len(X) > 0:
            from train import train_models
            success, metrics = train_models(db)
            print(f"✓ Training completed: {success}")
            print(f"  Trained: {metrics.get('trained_count')} models")
            print(f"  Has data: {metrics.get('has_data')}")
            
            from models.versioning import ModelVersionManager
            vm = ModelVersionManager()
            versions = vm.get_all_versions()
            print(f"✓ Model versions in DB: {len(versions)}")
            
            return success
        else:
            print("⚠ No training data available")
            return False
    except Exception as e:
        print(f"✗ Training test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_collection():
    """Test collection scheduler."""
    print("\n" + "=" * 60)
    print("TEST 3: Collection Scheduler")
    print("=" * 60)
    
    try:
        from automation.scheduler import AutomationScheduler
        scheduler = AutomationScheduler()
        status = scheduler.get_status()
        print(f"✓ Scheduler initialized")
        print(f"  Running: {status.get('running')}")
        print(f"  Current task: {status.get('current_task')}")
        return True
    except Exception as e:
        print(f"✗ Scheduler test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ARBIHAWK TEST SUITE")
    print("=" * 60)
    
    results = []
    results.append(("Odds Extraction", test_odds()))
    results.append(("Training Flow", test_training()))
    results.append(("Collection Scheduler", test_collection()))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
