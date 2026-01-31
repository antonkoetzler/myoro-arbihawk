"""
Tests for betting feature engineering (FeatureEngineer).
"""

import pytest
import pandas as pd
import numpy as np
from data.features import FeatureEngineer


class TestFeatureEngineerFormMomentum:
    """Tests for form momentum in betting features."""

    def test_create_features_includes_form_momentum(self, temp_db):
        """create_features returns home_form_momentum and away_form_momentum."""
        # Seed completed matches: 6 fixtures, same H vs A; H wins first 3, loses last 2 before f6
        fixtures = []
        scores = []
        starts = ["2024-05-01T15:00:00", "2024-05-02T15:00:00", "2024-05-03T15:00:00",
                  "2024-05-04T15:00:00", "2024-05-05T15:00:00", "2024-05-10T15:00:00"]
        for i in range(6):
            fid = f"fm_{i}"
            fixtures.append({
                "fixture_id": fid,
                "home_team_id": "H",
                "away_team_id": "A",
                "home_team_name": "Home",
                "away_team_name": "Away",
                "start_time": starts[i],
                "status": "finished",
            })
            # H: 2-0, 1-0, 1-0, 0-1, 0-2 (wins then losses)
            if i == 0:
                scores.append({"fixture_id": fid, "home_score": 2, "away_score": 0, "status": "ft"})
            elif i == 1:
                scores.append({"fixture_id": fid, "home_score": 1, "away_score": 0, "status": "ft"})
            elif i == 2:
                scores.append({"fixture_id": fid, "home_score": 1, "away_score": 0, "status": "ft"})
            elif i == 3:
                scores.append({"fixture_id": fid, "home_score": 0, "away_score": 1, "status": "ft"})
            elif i == 4:
                scores.append({"fixture_id": fid, "home_score": 0, "away_score": 2, "status": "ft"})
            else:
                scores.append({"fixture_id": fid, "home_score": 0, "away_score": 0, "status": "ft"})

        for f in fixtures:
            temp_db.insert_fixture(f)
        for s in scores:
            temp_db.insert_score(s["fixture_id"], s)

        # Odds for the fixture we featurize (fm_5) so odds cache has data
        temp_db.insert_odds("fm_5", [
            {"bookmaker_id": "b1", "outcome_name": "1", "outcome_id": "1", "odds_value": 2.0},
            {"bookmaker_id": "b1", "outcome_name": "X", "outcome_id": "X", "odds_value": 3.0},
            {"bookmaker_id": "b1", "outcome_name": "2", "outcome_id": "2", "odds_value": 3.5},
        ])

        fe = FeatureEngineer(temp_db)
        s = fe.create_features("fm_5")

        assert "home_form_momentum" in s.index
        assert "away_form_momentum" in s.index
        assert isinstance(s["home_form_momentum"], (int, float, np.floating))
        assert isinstance(s["away_form_momentum"], (int, float, np.floating))
        # H: last 5 = 3W,2L -> recent 2 pts=0, older 3 pts=3 -> momentum = -3
        assert s["home_form_momentum"] == -3.0

    def test_form_momentum_default_when_insufficient_matches(self, temp_db):
        """form_momentum is 0 when team has fewer than 3 matches."""
        temp_db.insert_fixture({
            "fixture_id": "single",
            "home_team_id": "H",
            "away_team_id": "A",
            "home_team_name": "H",
            "away_team_name": "A",
            "start_time": "2024-06-01T15:00:00",
            "status": "finished",
        })
        temp_db.insert_score("single", {"home_score": 1, "away_score": 0, "status": "ft"})
        temp_db.insert_odds("single", [
            {"bookmaker_id": "b1", "outcome_name": "1", "outcome_id": "1", "odds_value": 2.0},
            {"bookmaker_id": "b1", "outcome_name": "X", "outcome_id": "X", "odds_value": 3.0},
            {"bookmaker_id": "b1", "outcome_name": "2", "outcome_id": "2", "odds_value": 3.0},
        ])

        fe = FeatureEngineer(temp_db)
        s = fe.create_features("single")

        assert s["home_form_momentum"] == 0.0
        assert s["away_form_momentum"] == 0.0

    def test_opponent_strength_features_present(self, temp_db):
        """create_features returns form_vs_strong_ppg and form_vs_weak_ppg."""
        temp_db.insert_fixture({
            "fixture_id": "os",
            "home_team_id": "H",
            "away_team_id": "A",
            "home_team_name": "H",
            "away_team_name": "A",
            "start_time": "2024-06-01T15:00:00",
            "status": "finished",
        })
        temp_db.insert_score("os", {"home_score": 1, "away_score": 0, "status": "ft"})
        temp_db.insert_odds("os", [
            {"bookmaker_id": "b1", "outcome_name": "1", "outcome_id": "1", "odds_value": 2.0},
            {"bookmaker_id": "b1", "outcome_name": "X", "outcome_id": "X", "odds_value": 3.0},
            {"bookmaker_id": "b1", "outcome_name": "2", "outcome_id": "2", "odds_value": 3.0},
        ])
        fe = FeatureEngineer(temp_db)
        s = fe.create_features("os")
        assert "home_form_vs_strong_ppg" in s.index
        assert "home_form_vs_weak_ppg" in s.index
        assert "away_form_vs_strong_ppg" in s.index
        assert "away_form_vs_weak_ppg" in s.index
        assert s["home_form_vs_strong_ppg"] >= 0.0 and s["home_form_vs_strong_ppg"] <= 3.0
        assert s["home_form_vs_weak_ppg"] >= 0.0 and s["home_form_vs_weak_ppg"] <= 3.0

    def test_market_specific_features_present(self, temp_db):
        """create_features returns O/U and BTTS market-specific features."""
        temp_db.insert_fixture({
            "fixture_id": "ms",
            "home_team_id": "H",
            "away_team_id": "A",
            "home_team_name": "H",
            "away_team_name": "A",
            "start_time": "2024-06-01T15:00:00",
            "status": "finished",
        })
        temp_db.insert_score("ms", {"home_score": 1, "away_score": 0, "status": "ft"})
        temp_db.insert_odds("ms", [
            {"bookmaker_id": "b1", "outcome_name": "1", "outcome_id": "1", "odds_value": 2.0},
            {"bookmaker_id": "b1", "outcome_name": "X", "outcome_id": "X", "odds_value": 3.0},
            {"bookmaker_id": "b1", "outcome_name": "2", "outcome_id": "2", "odds_value": 3.0},
        ])
        fe = FeatureEngineer(temp_db)
        s = fe.create_features("ms")
        for col in ("home_avg_total_goals_5", "away_avg_total_goals_5",
                    "home_over25_rate_5", "away_over25_rate_5",
                    "home_btts_rate_5", "away_btts_rate_5"):
            assert col in s.index, f"Missing column: {col}"
        assert 0 <= s["home_over25_rate_5"] <= 1.0 and 0 <= s["away_over25_rate_5"] <= 1.0
        assert 0 <= s["home_btts_rate_5"] <= 1.0 and 0 <= s["away_btts_rate_5"] <= 1.0
        assert s["home_avg_total_goals_5"] >= 0 and s["away_avg_total_goals_5"] >= 0

    def test_tournament_context_features_present(self, temp_db):
        """create_features returns is_playoff_or_cup, is_final, tournament_id_numeric."""
        temp_db.insert_fixture({
            "fixture_id": "tc",
            "home_team_id": "H",
            "away_team_id": "A",
            "home_team_name": "H",
            "away_team_name": "A",
            "start_time": "2024-06-01T15:00:00",
            "status": "finished",
            "tournament_name": "FA Cup Final",
            "tournament_id": 42,
        })
        temp_db.insert_score("tc", {"home_score": 1, "away_score": 0, "status": "ft"})
        temp_db.insert_odds("tc", [
            {"bookmaker_id": "b1", "outcome_name": "1", "outcome_id": "1", "odds_value": 2.0},
            {"bookmaker_id": "b1", "outcome_name": "X", "outcome_id": "X", "odds_value": 3.0},
            {"bookmaker_id": "b1", "outcome_name": "2", "outcome_id": "2", "odds_value": 3.0},
        ])
        fe = FeatureEngineer(temp_db)
        s = fe.create_features("tc")
        assert "is_playoff_or_cup" in s.index and "is_final" in s.index and "tournament_id_numeric" in s.index
        assert s["is_playoff_or_cup"] == 1.0 and s["is_final"] == 1.0
        assert s["tournament_id_numeric"] == 42.0

    def test_tournament_context_regular_league(self, temp_db):
        """Tournament context for regular league: is_playoff_or_cup=0, is_final=0."""
        temp_db.insert_fixture({
            "fixture_id": "tcreg",
            "home_team_id": "H",
            "away_team_id": "A",
            "home_team_name": "H",
            "away_team_name": "A",
            "start_time": "2024-06-01T15:00:00",
            "status": "finished",
            "tournament_name": "Brasileiro Serie A",
            "tournament_id": 71,
        })
        temp_db.insert_score("tcreg", {"home_score": 1, "away_score": 0, "status": "ft"})
        temp_db.insert_odds("tcreg", [
            {"bookmaker_id": "b1", "outcome_name": "1", "outcome_id": "1", "odds_value": 2.0},
            {"bookmaker_id": "b1", "outcome_name": "X", "outcome_id": "X", "odds_value": 3.0},
            {"bookmaker_id": "b1", "outcome_name": "2", "outcome_id": "2", "odds_value": 3.0},
        ])
        fe = FeatureEngineer(temp_db)
        s = fe.create_features("tcreg")
        assert s["is_playoff_or_cup"] == 0.0 and s["is_final"] == 0.0
        assert s["tournament_id_numeric"] == 71.0
