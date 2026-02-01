#!/usr/bin/env python3
"""Fix odds market name mapping for Portuguese odds."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.database import Database

db = Database()

# Map Portuguese to English market names
MARKET_NAME_MAP = {
    'Resultado Final': '1x2',
    'Total de Gols Mais/Menos': 'over_under',
    'Ambas Marcam': 'btts',
    'Ambas as Equipes Marcam': 'btts',
}

with db._get_connection() as conn:
    cursor = conn.cursor()
    
    for pt_name, en_name in MARKET_NAME_MAP.items():
        cursor.execute("""
            UPDATE odds 
            SET market_name = ? 
            WHERE market_name = ?
        """, (en_name, pt_name))
        
        updated = cursor.rowcount
        if updated > 0:
            print(f"Updated {updated} odds: '{pt_name}' -> '{en_name}'")
    
    conn.commit()

print("Market name normalization complete")
