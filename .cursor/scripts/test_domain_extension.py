"""
End-to-end test script for ModelVersionManager domain extension.

Tests that:
1. Migration runs correctly
2. Existing betting models still work
3. Domain separation works (betting vs trading)
4. All existing functionality is preserved
"""

import sys
from pathlib import Path

# Add arbihawk to path
arbihawk_path = Path(__file__).parent.parent.parent / "src" / "arbihawk"
sys.path.insert(0, str(arbihawk_path))

from data.database import Database
from models.versioning import ModelVersionManager
import tempfile
import shutil


def test_migration():
    """Test that migration 5 runs correctly."""
    print("=" * 60)
    print("Test 1: Migration 5 - Domain Column")
    print("=" * 60)
    
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_migration.db"
    
    try:
        db = Database(db_path=str(db_path))
        
        # Check if domain column exists
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(model_versions)")
            columns = [row[1] for row in cursor.fetchall()]
        
        assert 'domain' in columns, "Domain column not found!"
        print("✓ Domain column exists")
        
        # Check if indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_model_versions_domain%'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert 'idx_model_versions_domain_market' in indexes, "Domain-market index not found!"
        assert 'idx_model_versions_domain_active' in indexes, "Domain-active index not found!"
        print("✓ Domain indexes created")
        
        # Check schema version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        version = cursor.fetchone()[0]
        assert version >= 5, f"Schema version should be >= 5, got {version}"
        print(f"✓ Schema version: {version}")
        
        print("\n✅ Migration test PASSED\n")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_betting_backward_compatibility():
    """Test that existing betting code still works."""
    print("=" * 60)
    print("Test 2: Betting Backward Compatibility")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_betting.db"
    
    try:
        db = Database(db_path=str(db_path))
        manager = ModelVersionManager(db=db)
        
        # Save betting models (explicit domain)
        v1_1x2 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/1x2.pkl",
            training_samples=100,
            cv_score=0.65,
            activate=True
        )
        
        v1_over = manager.save_version(
            domain="betting",
            market="over_under",
            model_path="test_models/over_under.pkl",
            training_samples=100,
            cv_score=0.70,
            activate=True
        )
        
        print(f"✓ Saved betting models: 1x2 (v{v1_1x2}), over_under (v{v1_over})")
        
        # Retrieve active models
        active_1x2 = manager.get_active_version(domain="betting", market="1x2")
        active_over = manager.get_active_version(domain="betting", market="over_under")
        
        assert active_1x2 is not None, "Active 1x2 model not found!"
        assert active_over is not None, "Active over_under model not found!"
        assert active_1x2["version_id"] == v1_1x2, "Wrong active 1x2 model!"
        assert active_over["version_id"] == v1_over, "Wrong active over_under model!"
        print("✓ Active models retrieved correctly")
        
        # Get all betting versions
        betting_versions = manager.get_all_versions(domain="betting")
        assert len(betting_versions) == 2, f"Expected 2 betting versions, got {len(betting_versions)}"
        print(f"✓ Retrieved {len(betting_versions)} betting versions")
        
        # Test activation (deactivate old, activate new)
        v2_1x2 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/1x2_v2.pkl",
            training_samples=150,
            cv_score=0.68,
            activate=True
        )
        
        active_1x2_after = manager.get_active_version(domain="betting", market="1x2")
        assert active_1x2_after["version_id"] == v2_1x2, "New model not activated!"
        
        # Old model should be inactive
        all_1x2 = manager.get_all_versions(domain="betting", market="1x2")
        v1_data = next((v for v in all_1x2 if v["version_id"] == v1_1x2), None)
        assert v1_data is not None, "Old version not found!"
        assert v1_data["is_active"] == 0, "Old version should be inactive!"
        print("✓ Model activation works correctly")
        
        print("\n✅ Backward compatibility test PASSED\n")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_domain_separation():
    """Test that betting and trading domains are completely separate."""
    print("=" * 60)
    print("Test 3: Domain Separation")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_separation.db"
    
    try:
        db = Database(db_path=str(db_path))
        manager = ModelVersionManager(db=db)
        
        # Save betting model
        betting_v1 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/betting_1x2.pkl",
            training_samples=100,
            cv_score=0.65,
            activate=True
        )
        
        # Save trading models
        trading_momentum = manager.save_version(
            domain="trading",
            market="momentum",
            model_path="test_models/trading_momentum.pkl",
            training_samples=200,
            cv_score=0.70,
            activate=True
        )
        
        trading_swing = manager.save_version(
            domain="trading",
            market="swing",
            model_path="test_models/trading_swing.pkl",
            training_samples=180,
            cv_score=0.72,
            activate=True
        )
        
        print("✓ Saved models in both domains")
        
        # Test domain filtering
        betting_versions = manager.get_all_versions(domain="betting")
        trading_versions = manager.get_all_versions(domain="trading")
        all_versions = manager.get_all_versions(domain=None)
        
        assert len(betting_versions) == 1, f"Expected 1 betting version, got {len(betting_versions)}"
        assert len(trading_versions) == 2, f"Expected 2 trading versions, got {len(trading_versions)}"
        assert len(all_versions) == 3, f"Expected 3 total versions, got {len(all_versions)}"
        print(f"✓ Domain filtering works: {len(betting_versions)} betting, {len(trading_versions)} trading")
        
        # Test that domains don't interfere
        active_betting = manager.get_active_version(domain="betting", market="1x2")
        active_trading = manager.get_active_version(domain="trading", market="momentum")
        
        assert active_betting["domain"] == "betting", "Betting model has wrong domain!"
        assert active_trading["domain"] == "trading", "Trading model has wrong domain!"
        print("✓ Domains are properly separated")
        
        # Test that activating trading doesn't affect betting
        trading_momentum_v2 = manager.save_version(
            domain="trading",
            market="momentum",
            model_path="test_models/trading_momentum_v2.pkl",
            training_samples=250,
            cv_score=0.75,
            activate=True
        )
        
        active_betting_after = manager.get_active_version(domain="betting", market="1x2")
        active_trading_after = manager.get_active_version(domain="trading", market="momentum")
        
        assert active_betting_after["version_id"] == betting_v1, "Betting model changed!"
        assert active_trading_after["version_id"] == trading_momentum_v2, "Trading model not updated!"
        print("✓ Domain activation independence works")
        
        print("\n✅ Domain separation test PASSED\n")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_rollback():
    """Test that rollback works with domain."""
    print("=" * 60)
    print("Test 4: Rollback with Domain")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_rollback.db"
    
    try:
        db = Database(db_path=str(db_path))
        manager = ModelVersionManager(db=db)
        
        # Create multiple versions
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
        
        v3 = manager.save_version(
            domain="betting",
            market="1x2",
            model_path="test_models/v3.pkl",
            training_samples=200,
            cv_score=0.68,
            activate=True
        )
        
        # Verify v3 is active
        active = manager.get_active_version(domain="betting", market="1x2")
        assert active["version_id"] == v3, "v3 should be active!"
        print("✓ v3 is active")
        
        # Rollback to v1
        success = manager.rollback_to_version(v1)
        assert success, "Rollback failed!"
        
        # Verify v1 is now active
        active_after = manager.get_active_version(domain="betting", market="1x2")
        assert active_after["version_id"] == v1, "v1 should be active after rollback!"
        print("✓ Rollback to v1 successful")
        
        # Verify domain is preserved
        assert active_after["domain"] == "betting", "Domain not preserved in rollback!"
        print("✓ Domain preserved in rollback")
        
        print("\n✅ Rollback test PASSED\n")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ModelVersionManager Domain Extension - End-to-End Tests")
    print("=" * 60 + "\n")
    
    try:
        test_migration()
        test_betting_backward_compatibility()
        test_domain_separation()
        test_rollback()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe domain extension is working correctly.")
        print("Existing betting functionality is preserved.")
        print("Trading domain is ready to be used.\n")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
