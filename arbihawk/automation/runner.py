"""
Main entry point for automation.
CLI interface for running data collection and training.
"""

import sys
import argparse
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.scheduler import AutomationScheduler
from utils.colors import print_header, print_success, print_error, print_info


def run_collect(scheduler: AutomationScheduler) -> int:
    """Run data collection only."""
    print_header("Data Collection")
    result = scheduler.run_collection()
    
    if result["success"]:
        print_success(f"Collection completed")
        print_info(f"  Betano: {result['betano'].get('records', 0)} records")
        print_info(f"  Flashscore: {result['flashscore'].get('records', 0)} records")
        if result.get('livescore', {}).get('records', 0) > 0:
            print_info(f"  Livescore: {result['livescore'].get('records', 0)} records")
        print_info(f"  Settled: {result['settlement'].get('settled', 0)} bets")
        return 0
    else:
        print_error("Collection failed")
        for error in result.get("errors", []):
            print_error(f"  {error}")
        return 1


def run_train(scheduler: AutomationScheduler) -> int:
    """Run training only."""
    print_header("Model Training")
    result = scheduler.run_training()
    
    if result["success"]:
        print_success(f"Training completed")
        print_info(f"  Markets trained: {result.get('markets_trained', 0)}")
        if result.get("backup_path"):
            print_info(f"  Backup: {result['backup_path']}")
        return 0
    else:
        print_error("Training failed")
        for error in result.get("errors", []):
            print_error(f"  {error}")
        return 1


def run_full(scheduler: AutomationScheduler) -> int:
    """Run full cycle (collection + training)."""
    print_header("Full Automation Cycle")
    result = scheduler.run_full_cycle()
    
    if result["success"]:
        print_success("Full cycle completed successfully")
        return 0
    else:
        print_error("Full cycle had errors")
        return 1


def run_daemon(scheduler: AutomationScheduler, interval: int) -> int:
    """Run in daemon mode."""
    print_header("Daemon Mode")
    print_info(f"Starting daemon with {interval}s interval...")
    print_info("Press Ctrl+C to stop")
    
    try:
        scheduler.start_daemon(interval_seconds=interval)
    except KeyboardInterrupt:
        print_info("\nInterrupted by user")
        scheduler.stop_daemon()
    
    return 0


def run_once(scheduler: AutomationScheduler) -> int:
    """Run once and exit (for cron jobs)."""
    return run_full(scheduler)


def run_status(scheduler: AutomationScheduler) -> int:
    """Show scheduler status."""
    status = scheduler.get_status()
    print_header("Scheduler Status")
    print_info(f"Running: {status['running']}")
    print_info(f"Current task: {status['current_task'] or 'None'}")
    print_info(f"Last collection: {status['last_collection'] or 'Never'}")
    print_info(f"Last training: {status['last_training'] or 'Never'}")
    print_info(f"Log entries: {status['log_count']}")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Arbihawk Automation Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m automation.runner --mode=collect    # Run data collection only
  python -m automation.runner --mode=train      # Run training only
  python -m automation.runner --mode=full       # Run full cycle
  python -m automation.runner --daemon          # Run as continuous daemon
  python -m automation.runner --once            # Run once and exit (for cron)
  python -m automation.runner --status          # Show scheduler status
"""
    )
    
    parser.add_argument('--mode', choices=['collect', 'train', 'full'],
                        help='Run mode: collect, train, or full')
    parser.add_argument('--daemon', action='store_true',
                        help='Run as continuous daemon')
    parser.add_argument('--once', action='store_true',
                        help='Run full cycle once and exit')
    parser.add_argument('--status', action='store_true',
                        help='Show scheduler status')
    parser.add_argument('--interval', type=int, default=21600,
                        help='Daemon interval in seconds (default: 21600 = 6 hours)')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.mode, args.daemon, args.once, args.status]):
        parser.print_help()
        return 1
    
    # Initialize scheduler
    scheduler = AutomationScheduler()
    
    # Handle status check
    if args.status:
        return run_status(scheduler)
    
    # Run appropriate mode
    if args.daemon:
        return run_daemon(scheduler, args.interval)
    
    if args.once:
        return run_once(scheduler)
    
    if args.mode == 'collect':
        return run_collect(scheduler)
    
    if args.mode == 'train':
        return run_train(scheduler)
    
    if args.mode == 'full':
        return run_full(scheduler)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
