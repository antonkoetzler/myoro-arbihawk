"""
Enhanced Polymarket Scanner

Fetches market data and converts to Market objects for strategy analysis.
"""

import aiohttp
import asyncio
from datetime import datetime
from typing import List, Optional

from .strategies import Market


class PolymarketScanner:
    """Scan Polymarket for market data."""
    
    GAMMA_API = 'https://gamma-api.polymarket.com/events'
    
    def __init__(self, min_liquidity: float = 1000, api_key: Optional[str] = None):
        self.min_liquidity = min_liquidity
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_scan_time: Optional[datetime] = None
    
    async def __aenter__(self):
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def scan(self, limit: int = 100) -> List[Market]:
        """Scan for markets and return Market objects."""
        params = {
            'active': 'true',
            'closed': 'false',
            'limit': limit,
        }
        
        async with self.session.get(self.GAMMA_API, params=params) as resp:
            if resp.status != 200:
                print(f"API error: {resp.status}")
                return []
            
            data = await resp.json()
            events = data if isinstance(data, list) else data.get('events', [])
            
            markets = []
            
            for event in events:
                for market_data in event.get('markets', []):
                    # Skip markets with low liquidity
                    liquidity = market_data.get('liquidityClob', 0) + market_data.get('liquidityClobNo', 0)
                    if liquidity < self.min_liquidity:
                        continue
                    # Skip non-binary markets
                    outcomes = market_data.get('outcomes', [])
                    if outcomes != ['Yes', 'No']:
                        continue
                    
                    # Get prices
                    yes_price = market_data.get('bestAsk') or market_data.get('midpoint')
                    no_price = market_data.get('noBestAsk')
                    
                    # Calculate no_price if not provided
                    if no_price is None and yes_price is not None:
                        no_price = 1.0 - yes_price
                    
                    if yes_price is None or no_price is None:
                        continue
                    
                    liquidity = market_data.get('liquidityClob', 0) + market_data.get('liquidityClobNo', 0)
                    volume = market_data.get('volume', 0)
                    
                    market = Market(
                        market_id=market_data.get('id', 'unknown'),
                        title=event.get('title', 'Unknown Market'),
                        yes_price=float(yes_price),
                        no_price=float(no_price),
                        volume=float(volume),
                        liquidity=float(liquidity),
                        timestamp=datetime.utcnow(),
                        outcome=None
                    )
                    
                    markets.append(market)
            
            self.last_scan_time = datetime.utcnow()
            return markets
    
    async def get_market_by_id(self, market_id: str) -> Optional[Market]:
        """Get a specific market by ID."""
        url = f'https://gamma-api.polymarket.com/markets/{market_id}'
        
        async with self.session.get(url) as resp:
            if resp.status != 200:
                return None
            
            data = await resp.json()
            
            yes_price = data.get('bestAsk') or data.get('midpoint')
            no_price = data.get('noBestAsk')
            
            if no_price is None and yes_price is not None:
                no_price = 1.0 - yes_price
            
            if yes_price is None:
                return None
            
            return Market(
                market_id=data.get('id', 'unknown'),
                title=data.get('question', 'Unknown'),
                yes_price=float(yes_price),
                no_price=float(no_price),
                volume=float(data.get('volume', 0)),
                liquidity=float(data.get('liquidityClob', 0)),
                timestamp=datetime.utcnow(),
                outcome=data.get('resolution')
            )


async def test_scanner():
    """Test the scanner."""
    async with PolymarketScanner() as scanner:
        markets = await scanner.scan(limit=20)
        print(f"Found {len(markets)} markets")
        for m in markets[:5]:
            print(f"  {m.title[:50]}: YES ${m.yes_price:.4f}, NO ${m.no_price:.4f}, Liquidity: ${m.liquidity:.0f}")


if __name__ == '__main__':
    asyncio.run(test_scanner())
