"""Polymarket configuration."""

# API Configuration
GAMMA_API_URL = 'https://gamma-api.polymarket.com'

# Trading Parameters
BANKROLL_USD = 10.0
MIN_ARBITRAGE_SPREAD = 0.001  # 0.1% minimum
MAX_POSITION_PCT = 0.30
SCAN_INTERVAL_MINUTES = 15

# Market Filters
MIN_LIQUIDITY_USD = 500
MAX_MARKETS_PER_SCAN = 150

# Notification config
NOTIFICATION_TARGET = '+5548988189095'
