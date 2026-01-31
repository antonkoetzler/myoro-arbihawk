"""
CLI script for running backtests.
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

from .backtest import BacktestEngine
from utils.colors import (
    print_header, print_success, print_error,
    print_warning, print_info, print_step
)


def main():
    """Run backtest from command line."""
    print_header("Arbihawk Backtesting")
    
    # Default parameters
    # Use last 6 months as test period, with 3 months training before that
    today = datetime.now()
    test_end = today.strftime('%Y-%m-%d')
    test_start = (today - timedelta(days=180)).strftime('%Y-%m-%d')
    train_start = (today - timedelta(days=270)).strftime('%Y-%m-%d')
    
    # Allow override via command line args
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("Usage: python -m backtesting.runner [train_start] [test_start] [test_end] [period_days]")
            print("\nExample:")
            print("  python -m backtesting.runner 2024-01-01 2024-06-01 2024-12-31 30")
            print("\nDefaults:")
            print(f"  train_start: {train_start}")
            print(f"  test_start: {test_start}")
            print(f"  test_end: {test_end}")
            print(f"  period_days: 30")
            return 0
        
        if len(sys.argv) >= 4:
            train_start = sys.argv[1]
            test_start = sys.argv[2]
            test_end = sys.argv[3]
        
        if len(sys.argv) >= 5:
            period_days = int(sys.argv[4])
        else:
            period_days = 30
    else:
        period_days = 30
    
    print_info(f"Training period: {train_start} to {test_start}")
    print_info(f"Test period: {test_start} to {test_end}")
    print_info(f"Period window: {period_days} days")
    print()
    
    # Run backtest
    print_step("Initializing backtest engine...")
    engine = BacktestEngine()
    
    print_step("Running backtest...")
    try:
        result = engine.run_backtest(
            train_start=train_start,
            test_start=test_start,
            test_end=test_end,
            period_days=period_days
        )
    except Exception as e:
        print_error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Display results
    print_header("Backtest Results")
    
    if len(result.bets) == 0:
        print_warning("No bets were placed in backtest.")
        print_info("This could mean:")
        print_info("  - Insufficient training data")
        print_info("  - No value bets found (EV threshold too high)")
        print_info("  - No odds available for test fixtures")
        return 0
    
    print_success(f"Total bets: {result.overall_metrics['total_bets']}")
    print_info(f"Wins: {result.overall_metrics['wins']}")
    print_info(f"Losses: {result.overall_metrics['losses']}")
    print_info(f"Win rate: {result.overall_metrics['win_rate']:.2%}")
    print_info(f"ROI: {result.overall_metrics['roi']:.2%}")
    print_info(f"Profit: ${result.overall_metrics['profit']:.2f}")
    print_info(f"Sharpe ratio: {result.overall_metrics['sharpe_ratio']:.2f}")
    print_info(f"Max drawdown: {result.overall_metrics['max_drawdown']:.2%}")
    print()
    
    # By market
    if result.by_market:
        print_header("Performance by Market")
        for market, metrics in result.by_market.items():
            print_info(f"{market.upper()}:")
            print_info(f"  Bets: {metrics['total_bets']}")
            print_info(f"  Win rate: {metrics['win_rate']:.2%}")
            print_info(f"  ROI: {metrics['roi']:.2%}")
            print_info(f"  Profit: ${metrics['profit']:.2f}")
        print()
    
    # Period breakdown
    if len(result.periods) > 1:
        print_header("Performance by Period")
        for i, period in enumerate(result.periods[:10]):  # Show first 10
            print_info(f"Period {i+1} ({period['period_start'][:10]} to {period['period_end'][:10]}):")
            print_info(f"  Bets: {period['total_bets']}, ROI: {period['roi']:.2%}, Profit: ${period['profit']:.2f}")
        if len(result.periods) > 10:
            print_info(f"... and {len(result.periods) - 10} more periods")
        print()
    
    # Save results to file
    results_file = Path(__file__).parent.parent / "backtesting" / "results" / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2, default=str)
    
    print_success(f"Results saved to {results_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
