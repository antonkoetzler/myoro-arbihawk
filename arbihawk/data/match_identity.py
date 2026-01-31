"""
Central match-identity layer for linking fixtures, scores, and bets by teams + date.
Defines synthetic ID format, team normalization, and same_match logic.
"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

# Synthetic ID format: source_Home_Away_Date (date YYYY-MM-DD, teams with spaces → underscores)
SYNTHETIC_PREFIXES = ("flashscore_", "livescore_")
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _normalize_date(d: Optional[str]) -> Optional[str]:
    """Return YYYY-MM-DD from ISO datetime or date string, or None."""
    if not d:
        return None
    s = str(d).strip()
    if not s:
        return None
    # Already date-only
    if DATE_ONLY_RE.match(s):
        return s[:10]
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        if DATE_ONLY_RE.match(s[:10]):
            return s[:10]
        return None


def normalize_team_name(name: str, aliases_map: Optional[Dict[str, str]] = None) -> str:
    """Normalize team name for matching: lowercase, strip, apply aliases, remove common suffixes."""
    if not name:
        return ""
    normalized = name.lower().strip()
    suffixes = [" fc", " cf", " sc", " ac", " afc", " bc"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
    if aliases_map and normalized in aliases_map:
        normalized = aliases_map[normalized]
    return normalized


def fixture_key(home: str, away: str, date: Optional[str]) -> str:
    """Canonical key for a fixture: normalized home_away_YYYY-MM-DD."""
    d = _normalize_date(date)
    if not d:
        d = ""
    return f"{normalize_team_name(home, None)}_{normalize_team_name(away, None)}_{d}"


def team_similarity(name1: str, name2: str, aliases_map: Optional[Dict[str, str]] = None) -> int:
    """Fuzzy + aliases similarity 0-100."""
    n1 = normalize_team_name(name1, aliases_map)
    n2 = normalize_team_name(name2, aliases_map)
    if n1 == n2:
        return 100
    if HAS_RAPIDFUZZ:
        ratio = fuzz.ratio(n1, n2)
        partial = fuzz.partial_ratio(n1, n2)
        token = fuzz.token_sort_ratio(n1, n2)
        return max(ratio, partial, token)
    if n1 in n2 or n2 in n1:
        return 85
    common = set(n1.split()) & set(n2.split())
    if common:
        total = len(set(n1.split()) | set(n2.split()))
        return int((len(common) / total) * 100) if total else 0
    return 0


def same_match(
    home1: str,
    away1: str,
    date1: Optional[str],
    home2: str,
    away2: str,
    date2: Optional[str],
    min_score: int = 75,
    aliases_map: Optional[Dict[str, str]] = None,
) -> bool:
    """True if the two (home, away, date) refer to the same match above min_score."""
    d1 = _normalize_date(date1)
    d2 = _normalize_date(date2)
    if d1 and d2 and d1 != d2:
        return False
    home_sim = team_similarity(home1, home2, aliases_map)
    away_sim = team_similarity(away1, away2, aliases_map)
    combined = (home_sim + away_sim) / 2
    return combined >= min_score


def synthetic_id(source: str, home: str, away: str, date: Optional[str]) -> str:
    """Build synthetic fixture_id: source_Home_Away_YYYY-MM-DD (spaces → underscores)."""
    d = _normalize_date(date) or ""
    safe_home = (home or "").replace(" ", "_").strip() or "Home"
    safe_away = (away or "").replace(" ", "_").strip() or "Away"
    return f"{source}_{safe_home}_{safe_away}_{d}"


def parse_synthetic_id(fixture_id: str) -> Optional[Dict[str, str]]:
    """
    Parse source_Home_Away_Date into {source, home, away, date}.
    Returns None if fixture_id is not a synthetic ID.
    For multi-word teams we only have a single-token heuristic (last token before date = away).
    Use synthetic_id_matches_fixture() when you need to match without that ambiguity.
    """
    if not fixture_id:
        return None
    for prefix in SYNTHETIC_PREFIXES:
        if fixture_id.startswith(prefix):
            rest = fixture_id[len(prefix) :].strip()
            if not rest:
                return {"source": prefix.rstrip("_"), "home": "", "away": "", "date": ""}
            parts = rest.split("_")
            date_idx = None
            for i in range(len(parts) - 1, -1, -1):
                if DATE_ONLY_RE.match(parts[i]):
                    date_idx = i
                    break
            if date_idx is None:
                if len(parts) >= 3:
                    date_idx = len(parts) - 1
                    date_part = parts[-1]
                else:
                    return {"source": prefix.rstrip("_"), "home": rest.replace("_", " "), "away": "", "date": ""}
            else:
                date_part = parts[date_idx]
            if date_idx >= 2:
                away = parts[date_idx - 1].replace("_", " ")
                home = "_".join(parts[: date_idx - 1]).replace("_", " ")
            elif date_idx == 1:
                home = parts[0].replace("_", " ")
                away = ""
            else:
                home = ""
                away = ""
            return {"source": prefix.rstrip("_"), "home": home, "away": away, "date": date_part}
    return None


def synthetic_id_matches_fixture(
    synthetic_fixture_id: str,
    home_team: str,
    away_team: str,
    start_time: Optional[str],
    min_score: int = 75,
    aliases_map: Optional[Dict[str, str]] = None,
) -> bool:
    """
    True if the synthetic ID refers to the same match as (home_team, away_team, start_time).
    Tries every possible split of the teams part (handles multi-word names).
    """
    parsed = parse_synthetic_id(synthetic_fixture_id)
    if not parsed:
        return False
    date_str = parsed.get("date")
    rest = synthetic_fixture_id
    for prefix in SYNTHETIC_PREFIXES:
        if rest.startswith(prefix):
            rest = rest[len(prefix) :].strip()
            break
    # rest = "Home_Away_Date" or "H_A_B_Date"; strip date from end
    parts = rest.split("_")
    date_idx = None
    for i in range(len(parts) - 1, -1, -1):
        if DATE_ONLY_RE.match(parts[i]):
            date_idx = i
            break
    if date_idx is None or date_idx < 2:
        return same_match(
            home_team, away_team, start_time,
            parsed.get("home") or "", parsed.get("away") or "", date_str,
            min_score=min_score, aliases_map=aliases_map,
        )
    teams_parts = parts[:date_idx]
    # Try every split: [0:i] = home, [i:date_idx] = away (handles multi-word names)
    for i in range(1, len(teams_parts)):
        home_cand = " ".join(teams_parts[:i])
        away_cand = " ".join(teams_parts[i:])
        if same_match(
            home_team, away_team, start_time,
            home_cand, away_cand, date_str,
            min_score=min_score, aliases_map=aliases_map,
        ):
            return True
    # Single split (i=0 or i=len) already covered by parse_synthetic_id; try parsed home/away
    return same_match(
        home_team, away_team, start_time,
        parsed.get("home") or "", parsed.get("away") or "", date_str,
        min_score=min_score, aliases_map=aliases_map,
    )


def get_aliases_and_min_score() -> Tuple[Dict[str, str], int]:
    """Load aliases map and min_match_score from config. Safe to call before config is fully loaded."""
    try:
        import config as _config
        aliases = getattr(_config, "TEAM_ALIASES", None) or {}
        min_score = getattr(_config, "MATCHING_MIN_MATCH_SCORE", 75)
        return (aliases, min_score)
    except Exception:
        return ({}, 75)
