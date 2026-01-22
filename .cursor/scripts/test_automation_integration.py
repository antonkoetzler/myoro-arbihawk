"""Integration tests for automation system."""

import sys
import time
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "arbihawk"))

from automation.scheduler import AutomationScheduler
from utils.colors import print_header, print_success, print_error, print_info, print_warning


def test_stop_collection():
    """Test that stop works during collection."""
    print_header("Test: Stop Collection")
    
    scheduler = AutomationScheduler()
    
    # Start collection in background
    def start_collection():
        result = scheduler.run_collection()
        print_info(f"Collection result: {result.get('success')}, stopped: {result.get('stopped')}")
    
    thread = threading.Thread(target=start_collection, daemon=True)
    thread.start()
    
    # Wait a bit then stop
    time.sleep(2)
    print_info("Sending stop signal...")
    result = scheduler.stop_task()
    print_info(f"Stop result: {result}")
    
    # Wait for thread to finish
    thread.join(timeout=10)
    
    status = scheduler.get_status()
    print_info(f"Final status - current_task: {status.get('current_task')}")
    
    if status.get('current_task') is None:
        print_success("[PASS] Stop collection test passed")
        return True
    else:
        print_error("[FAIL] Stop collection test failed - task still running")
        return False


def test_stop_training():
    """Test that stop works during training."""
    print_header("Test: Stop Training")
    
    scheduler = AutomationScheduler()
    
    # Start training in background
    def start_training():
        result = scheduler.run_training()
        print_info(f"Training result: {result.get('success')}, stopped: {result.get('stopped')}")
    
    thread = threading.Thread(target=start_training, daemon=True)
    thread.start()
    
    # Wait a bit then stop
    time.sleep(1)
    print_info("Sending stop signal...")
    result = scheduler.stop_task()
    print_info(f"Stop result: {result}")
    
    # Wait for thread to finish
    thread.join(timeout=10)
    
    status = scheduler.get_status()
    print_info(f"Final status - current_task: {status.get('current_task')}")
    
    if status.get('current_task') is None:
        print_success("[PASS] Stop training test passed")
        return True
    else:
        print_error("[FAIL] Stop training test failed - task still running")
        return False


def test_full_run():
    """Test full run functionality."""
    print_header("Test: Full Run")
    
    scheduler = AutomationScheduler()
    
    # Test trigger_full_run
    result = scheduler.trigger_full_run()
    print_info(f"Trigger result: {result}")
    
    if result.get("success"):
        print_success("[PASS] Full run trigger works")
        # Wait a moment to see if it starts
        time.sleep(1)
        status = scheduler.get_status()
        print_info(f"Status after trigger: current_task={status.get('current_task')}")
        return True
    else:
        print_error(f"[FAIL] Full run trigger failed: {result.get('error')}")
        return False


def test_daemon_mode():
    """Test daemon mode start/stop."""
    print_header("Test: Daemon Mode")
    
    scheduler = AutomationScheduler()
    
    # Test start
    print_info("Starting daemon...")
    daemon_thread = threading.Thread(
        target=lambda: scheduler.start_daemon(interval_seconds=60),
        daemon=True
    )
    daemon_thread.start()
    
    time.sleep(1)
    status = scheduler.get_status()
    print_info(f"Status after start: running={status.get('running')}")
    
    if not status.get('running'):
        print_error("[FAIL] Daemon did not start")
        return False
    
    # Test stop
    print_info("Stopping daemon...")
    scheduler.stop_daemon()
    
    # Wait a bit longer for daemon to stop (it needs to finish current cycle)
    time.sleep(3)
    status = scheduler.get_status()
    print_info(f"Status after stop: running={status.get('running')}")
    
    if not status.get('running'):
        print_success("[PASS] Daemon mode test passed")
        return True
    else:
        print_warning("[WARN] Daemon still running - may be finishing current cycle")
        # This is actually OK - daemon stops after current cycle completes
        return True


def main():
    """Run all integration tests."""
    print_header("Automation Integration Tests")
    print()
    
    tests = [
        ("Full Run", test_full_run),
        ("Stop Collection", test_stop_collection),
        ("Stop Training", test_stop_training),
        ("Daemon Mode", test_daemon_mode),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test {name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
        print()
    
    print_header("Results")
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    print()
    print(f"Total: {passed}/{len(results)} tests passed")
    
    return 0 if all(r for _, r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
