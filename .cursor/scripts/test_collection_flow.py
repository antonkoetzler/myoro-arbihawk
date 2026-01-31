"""Test collection flow with limited data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "arbihawk"))

from automation.scheduler import AutomationScheduler
from utils.colors import print_header, print_info, print_success, print_error

def test_collection():
    """Test collection flow."""
    print_header("Testing Collection Flow")
    
    scheduler = AutomationScheduler()
    
    # Check status
    status = scheduler.get_status()
    print_info(f"Scheduler status: {status}")
    
    if status.get('running'):
        print_error("Scheduler is already running!")
        return False
    
    print_info("Starting collection test...")
    print_info("Note: This will run full collection. Press Ctrl+C to stop if needed.")
    
    try:
        result = scheduler.run_collection()
        
        print_success("Collection completed!")
        print_info(f"Results: {result}")
        
        return result.get('success', False)
    except KeyboardInterrupt:
        print_error("Collection interrupted by user")
        scheduler.stop_task()
        return False
    except Exception as e:
        print_error(f"Collection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_collection()
    sys.exit(0 if success else 1)
