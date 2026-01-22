"""Database health check script."""
import sqlite3
import sys
from pathlib import Path

db_path = Path(__file__).parent.parent.parent / "arbihawk" / "data" / "arbihawk.db"

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

issues = []

print("=== DATABASE HEALTH CHECK ===\n")

# 1. Check for duplicate fixtures
print("1. Checking for duplicate fixtures...")
cursor.execute("""
    SELECT fixture_id, COUNT(*) as count 
    FROM fixtures 
    GROUP BY fixture_id 
    HAVING COUNT(*) > 1
""")
duplicates = cursor.fetchall()
if duplicates:
    issues.append(f"DUPLICATE FIXTURES: {len(duplicates)} fixture_ids appear multiple times")
    for row in duplicates[:5]:
        print(f"   - fixture_id {row[0]} appears {row[1]} times")
else:
    print("   OK - No duplicate fixtures")

# 2. Check for duplicate odds (violating UNIQUE constraint)
print("\n2. Checking for duplicate odds...")
cursor.execute("""
    SELECT fixture_id, bookmaker_id, market_id, outcome_id, COUNT(*) as count
    FROM odds
    GROUP BY fixture_id, bookmaker_id, market_id, outcome_id
    HAVING COUNT(*) > 1
""")
duplicate_odds = cursor.fetchall()
if duplicate_odds:
    issues.append(f"DUPLICATE ODDS: {len(duplicate_odds)} unique combinations appear multiple times")
    for row in duplicate_odds[:5]:
        print(f"   - fixture_id={row[0]}, bookmaker={row[1]}, market={row[2]}, outcome={row[3]} appears {row[4]} times")
else:
    print("   OK - No duplicate odds")

# 3. Check for orphaned odds (fixture_id doesn't exist in fixtures)
print("\n3. Checking for orphaned odds...")
cursor.execute("""
    SELECT COUNT(*) FROM odds o
    LEFT JOIN fixtures f ON o.fixture_id = f.fixture_id
    WHERE f.fixture_id IS NULL
""")
orphaned_odds = cursor.fetchone()[0]
if orphaned_odds > 0:
    issues.append(f"ORPHANED ODDS: {orphaned_odds} odds records reference non-existent fixtures")
    print(f"   WARNING {orphaned_odds} orphaned odds records")
    cursor.execute("""
        SELECT DISTINCT o.fixture_id FROM odds o
        LEFT JOIN fixtures f ON o.fixture_id = f.fixture_id
        WHERE f.fixture_id IS NULL
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   - fixture_id {row[0]}")
else:
    print("   OK - No orphaned odds")

# 4. Check for orphaned scores
print("\n4. Checking for orphaned scores...")
cursor.execute("""
    SELECT COUNT(*) FROM scores s
    LEFT JOIN fixtures f ON s.fixture_id = f.fixture_id
    WHERE f.fixture_id IS NULL
""")
orphaned_scores = cursor.fetchone()[0]
if orphaned_scores > 0:
    issues.append(f"ORPHANED SCORES: {orphaned_scores} scores reference non-existent fixtures")
    print(f"   WARNING {orphaned_scores} orphaned score records")
else:
    print("   OK - No orphaned scores")

# 5. Check for orphaned bet_history
print("\n5. Checking for orphaned bet_history...")
cursor.execute("""
    SELECT COUNT(*) FROM bet_history bh
    LEFT JOIN fixtures f ON bh.fixture_id = f.fixture_id
    WHERE f.fixture_id IS NULL
""")
orphaned_bets = cursor.fetchone()[0]
if orphaned_bets > 0:
    issues.append(f"ORPHANED BETS: {orphaned_bets} bet_history records reference non-existent fixtures")
    print(f"   WARNING {orphaned_bets} orphaned bet records")
else:
    print("   OK - No orphaned bet_history")

# 6. Check for duplicate bet_settlements
print("\n6. Checking for duplicate bet_settlements...")
cursor.execute("""
    SELECT fixture_id, market_id, outcome_id, COUNT(*) as count
    FROM bet_settlements
    GROUP BY fixture_id, market_id, outcome_id
    HAVING COUNT(*) > 1
""")
duplicate_settlements = cursor.fetchall()
if duplicate_settlements:
    issues.append(f"DUPLICATE SETTLEMENTS: {len(duplicate_settlements)} settlement combinations appear multiple times")
    for row in duplicate_settlements[:5]:
        print(f"   - fixture_id={row[0]}, market={row[1]}, outcome={row[2]} appears {row[3]} times")
else:
    print("   OK - No duplicate settlements")

# 7. Check for fixtures with no odds
print("\n7. Checking for fixtures with no odds...")
cursor.execute("""
    SELECT COUNT(*) FROM fixtures f
    LEFT JOIN odds o ON f.fixture_id = o.fixture_id
    WHERE o.fixture_id IS NULL
""")
fixtures_no_odds = cursor.fetchone()[0]
if fixtures_no_odds > 0:
    print(f"   WARNING {fixtures_no_odds} fixtures have no odds (may be normal for future fixtures)")
else:
    print("   OK - All fixtures have odds")

# 8. Check for odds with invalid/null values
print("\n8. Checking for invalid odds values...")
cursor.execute("""
    SELECT COUNT(*) FROM odds 
    WHERE odds_value IS NULL OR odds_value <= 0 OR odds_value > 1000
""")
invalid_odds = cursor.fetchone()[0]
if invalid_odds > 0:
    issues.append(f"INVALID ODDS VALUES: {invalid_odds} odds have NULL, <= 0, or > 1000")
    print(f"   WARNING {invalid_odds} invalid odds values")
    cursor.execute("""
        SELECT fixture_id, bookmaker_name, market_name, outcome_name, odds_value
        FROM odds 
        WHERE odds_value IS NULL OR odds_value <= 0 OR odds_value > 1000
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   - fixture_id={row[0]}, {row[1]}, {row[2]}, {row[3]}, odds={row[4]}")
else:
    print("   OK - All odds values are valid")

# 9. Check for pending bets that should be settled
print("\n9. Checking for old pending bets...")
cursor.execute("""
    SELECT COUNT(*) FROM bet_history bh
    JOIN fixtures f ON bh.fixture_id = f.fixture_id
    WHERE bh.result = 'pending'
    AND f.start_time < datetime('now', '-1 day')
    AND f.status IN ('finished', 'FT', 'AET', 'PEN')
""")
old_pending = cursor.fetchone()[0]
if old_pending > 0:
    issues.append(f"UNSETTLED BETS: {old_pending} pending bets for finished fixtures")
    print(f"   WARNING {old_pending} pending bets for finished fixtures")
else:
    print("   OK - No old pending bets")

# 10. Check for multiple active models per market
print("\n10. Checking for multiple active models per market...")
cursor.execute("""
    SELECT market, COUNT(*) as count
    FROM model_versions
    WHERE is_active = 1
    GROUP BY market
    HAVING COUNT(*) > 1
""")
multiple_active = cursor.fetchall()
if multiple_active:
    issues.append(f"MULTIPLE ACTIVE MODELS: {len(multiple_active)} markets have multiple active models")
    for row in multiple_active:
        print(f"   - market '{row[0]}' has {row[1]} active models")
else:
    print("   OK - No markets with multiple active models")

# 11. Check for duplicate ingestion metadata (same source, same checksum, close timestamps)
print("\n11. Checking for duplicate ingestion metadata...")
cursor.execute("""
    SELECT source, checksum, COUNT(*) as count
    FROM ingestion_metadata
    WHERE checksum IS NOT NULL
    GROUP BY source, checksum
    HAVING COUNT(*) > 1
""")
duplicate_ingestion = cursor.fetchall()
if duplicate_ingestion:
    issues.append(f"DUPLICATE INGESTION: {len(duplicate_ingestion)} duplicate ingestion records")
    for row in duplicate_ingestion[:5]:
        print(f"   - source={row[0]}, checksum={row[1]}, count={row[2]}")
else:
    print("   OK - No duplicate ingestion metadata")

# 12. Check for fixtures with inconsistent team names
print("\n12. Checking for team name inconsistencies...")
cursor.execute("""
    SELECT home_team_name, COUNT(DISTINCT home_team_id) as id_count
    FROM fixtures
    WHERE home_team_id IS NOT NULL
    GROUP BY home_team_name
    HAVING COUNT(DISTINCT home_team_id) > 1
    LIMIT 10
""")
inconsistent_teams = cursor.fetchall()
if inconsistent_teams:
    issues.append(f"TEAM NAME INCONSISTENCY: {len(inconsistent_teams)} team names map to multiple IDs")
    for row in inconsistent_teams[:5]:
        print(f"   - '{row[0]}' has {row[1]} different IDs")
else:
    print("   OK - No team name inconsistencies")

# 13. Check for very old timestamps
print("\n13. Checking for suspicious timestamps...")
cursor.execute("""
    SELECT COUNT(*) FROM fixtures
    WHERE start_time < '2000-01-01' OR start_time > '2100-01-01'
""")
bad_timestamps = cursor.fetchone()[0]
if bad_timestamps > 0:
    issues.append(f"BAD TIMESTAMPS: {bad_timestamps} fixtures have suspicious start_time values")
    print(f"   WARNING {bad_timestamps} fixtures with bad timestamps")
else:
    print("   OK - All timestamps look reasonable")

# 14. Check for NULL primary keys or required fields
print("\n14. Checking for NULL in required fields...")
cursor.execute("""
    SELECT COUNT(*) FROM fixtures WHERE fixture_id IS NULL
""")
null_fixture_ids = cursor.fetchone()[0]
if null_fixture_ids > 0:
    issues.append(f"NULL FIXTURE IDs: {null_fixture_ids} fixtures have NULL fixture_id")
    print(f"   WARNING {null_fixture_ids} NULL fixture_ids")

cursor.execute("""
    SELECT COUNT(*) FROM odds WHERE fixture_id IS NULL
""")
null_odds_fixture = cursor.fetchone()[0]
if null_odds_fixture > 0:
    issues.append(f"NULL ODDS FIXTURE IDs: {null_odds_fixture} odds have NULL fixture_id")
    print(f"   WARNING {null_odds_fixture} odds with NULL fixture_id")

# Summary
print("\n" + "="*50)
print("SUMMARY")
print("="*50)
if issues:
    print(f"\nWARNING FOUND {len(issues)} POTENTIAL ISSUES:\n")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("\nOK - Database health check passed - no issues found!")

conn.close()
