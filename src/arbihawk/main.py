"""
Arbihawk - Betting prediction bot
"""

import argparse
from pathlib import Path
from models import BettingPredictor
from data import DataCollector
from data.database import Database
from engine import ValueBetEngine
from config import EV_THRESHOLD


def main():
    """Main entry point for Arbihawk."""
    parser = argparse.ArgumentParser(description='Arbihawk betting prediction bot')
    parser.add_argument('--market', default='1x2', choices=['1x2', 'over_under', 'btts'],
                       help='Betting market to analyze')
    parser.add_argument('--limit', type=int, default=10,
                       help='Number of recommendations to show')
    parser.add_argument('--model-path', type=str,
                       help='Path to trained model (default: models/saved/{market}_model.pkl)')
    
    args = parser.parse_args()
    
    # Load model
    if args.model_path:
        model_path = args.model_path
    else:
        model_path = Path(__file__).parent / "models" / "saved" / f"{args.market}_model.pkl"
    
    if not Path(model_path).exists():
        print(f"Model not found at {model_path}")
        print("Please train a model first using: python train.py")
        return
    
    print(f"Loading model from {model_path}...")
    predictor = BettingPredictor(market=args.market)
    predictor.load(str(model_path))
    
    if not predictor.is_trained:
        print("Model is not trained. Please train a model first.")
        return
    
    # Initialize database and value bet engine
    db = Database()
    engine = ValueBetEngine(predictor, db, ev_threshold=EV_THRESHOLD)
    
    # Get recommendations
    print(f"\nFinding value bets (EV threshold: {EV_THRESHOLD*100:.1f}%)...")
    recommendations = engine.get_recommendations(limit=args.limit)
    
    if len(recommendations) == 0:
        print("No value bets found at this time.")
        return
    
    print(f"\nTop {len(recommendations)} Value Bet Recommendations:")
    print("=" * 80)
    
    for idx, (_, bet) in enumerate(recommendations.iterrows(), 1):
        print(f"\n{idx}. {bet['home_team']} vs {bet['away_team']}")
        print(f"   Market: {bet['market']} | Outcome: {bet['outcome']}")
        print(f"   Bookmaker: {bet['bookmaker']} | Odds: {bet['odds']:.2f}")
        print(f"   Model Probability: {bet['probability']:.1%}")
        print(f"   Expected Value: {bet['ev_percentage']:.2f}%")
        print(f"   Start Time: {bet['start_time']}")


if __name__ == "__main__":
    main()

