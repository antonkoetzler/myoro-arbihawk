"""Tests for central match-identity layer."""
import pytest
from data.match_identity import (
    normalize_team_name,
    fixture_key,
    team_similarity,
    same_match,
    synthetic_id,
    parse_synthetic_id,
    synthetic_id_matches_fixture,
    get_aliases_and_min_score,
)


class TestMatchIdentity:
    def test_normalize_team_name(self):
        assert normalize_team_name("  Manchester United  ", None) == "manchester united"
        assert normalize_team_name("Man Utd", {"man utd": "manchester united"}) == "manchester united"
        assert normalize_team_name("Barcelona FC", None) == "barcelona"

    def test_fixture_key(self):
        k = fixture_key("Team A", "Team B", "2025-01-15")
        assert "team a" in k and "team b" in k and "2025-01-15" in k
        assert fixture_key("A", "B", "2025-01-15T12:00:00Z") == "a_b_2025-01-15"

    def test_team_similarity(self):
        assert team_similarity("Manchester United", "Manchester United", None) == 100
        assert team_similarity("Man United", "Manchester United", {"man united": "manchester united"}) == 100
        assert team_similarity("Spezia", "Spezia", None) == 100
        assert team_similarity("Unknown", "Other", None) < 100

    def test_same_match(self):
        assert same_match("Spezia", "Sampdoria", "2025-11-30", "Spezia", "Sampdoria", "2025-11-30", min_score=75) is True
        assert same_match("A", "B", "2025-01-01", "A", "B", "2025-01-02", min_score=75) is False
        assert same_match("Man Utd", "Liverpool", "2025-01-15", "Manchester United", "Liverpool", "2025-01-15", min_score=75, aliases_map={"man utd": "manchester united"}) is True

    def test_synthetic_id(self):
        sid = synthetic_id("flashscore", "Spezia", "Sampdoria", "2025-11-30")
        assert sid == "flashscore_Spezia_Sampdoria_2025-11-30"
        assert synthetic_id("flashscore", "Real Madrid", "Barcelona", "2025-01-15") == "flashscore_Real_Madrid_Barcelona_2025-01-15"
        assert synthetic_id("livescore", "A", "B", "2025-01-15T18:00:00") == "livescore_A_B_2025-01-15"

    def test_parse_synthetic_id(self):
        assert parse_synthetic_id("79560484") is None
        p = parse_synthetic_id("flashscore_Spezia_Sampdoria_2025-11-30")
        assert p is not None
        assert p["source"] == "flashscore"
        assert p["home"] == "Spezia"
        assert p["away"] == "Sampdoria"
        assert p["date"] == "2025-11-30"
        p2 = parse_synthetic_id("flashscore_Real_Madrid_Barcelona_2025-01-15")
        assert p2 is not None
        assert p2["home"] == "Real Madrid"
        assert p2["away"] == "Barcelona"
        assert p2["date"] == "2025-01-15"

    def test_get_aliases_and_min_score(self):
        aliases, min_score = get_aliases_and_min_score()
        assert isinstance(aliases, dict)
        assert isinstance(min_score, int)
        assert min_score >= 0

    def test_synthetic_id_matches_fixture_multi_word_teams(self):
        """Multi-word team names: synthetic ID has no delimiter between home/away; try all splits."""
        # ID format: flashscore_Real_Madrid_Atletico_Madrid_2025-01-15
        sid = "flashscore_Real_Madrid_Atletico_Madrid_2025-01-15"
        assert synthetic_id_matches_fixture(
            sid, "Real Madrid", "Atletico Madrid", "2025-01-15T18:00:00",
            min_score=75, aliases_map={},
        ) is True
        assert synthetic_id_matches_fixture(
            sid, "Other", "Team", "2025-01-15", min_score=75, aliases_map={},
        ) is False
