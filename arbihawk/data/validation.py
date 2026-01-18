"""
Data validation layer for scraper outputs.
Validates incoming JSON against defined schemas.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import json

# Try to import jsonschema, but provide fallback if not available
try:
    from jsonschema import validate, ValidationError, Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    ValidationError = Exception


# =============================================================================
# JSON SCHEMAS
# =============================================================================

# Betano fixture schema
BETANO_FIXTURE_SCHEMA = {
    "type": "object",
    "required": ["fixture_id", "home_team_name", "away_team_name", "start_time"],
    "properties": {
        "fixture_id": {"type": "string"},
        "home_team_name": {"type": "string"},
        "away_team_name": {"type": "string"},
        "start_time": {"type": "string"},
        "home_team_id": {"type": ["string", "null"]},
        "away_team_id": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "odds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "market_id": {"type": ["string", "integer"]},
                    "market_name": {"type": "string"},
                    "outcome_id": {"type": ["string", "integer"]},
                    "outcome_name": {"type": "string"},
                    "odds_value": {"type": "number"}
                }
            }
        }
    }
}

# Betano league schema
BETANO_LEAGUE_SCHEMA = {
    "type": "object",
    "required": ["league_id", "league_name"],
    "properties": {
        "league_id": {"type": "integer"},
        "league_name": {"type": "string"},
        "fixtures": {
            "type": "array",
            "items": BETANO_FIXTURE_SCHEMA
        },
        "topScorer": {"type": "array"},
        "leagueWinner": {"type": "array"}
    }
}

# Betano root schema (array of leagues)
BETANO_ROOT_SCHEMA = {
    "type": "array",
    "items": BETANO_LEAGUE_SCHEMA
}

# Match score schema (Flashscore/Livescore)
MATCH_SCORE_SCHEMA = {
    "type": "object",
    "required": ["home_team_name", "away_team_name"],
    "properties": {
        "home_team_name": {"type": "string"},
        "away_team_name": {"type": "string"},
        "home_score": {"type": ["integer", "null"]},
        "away_score": {"type": ["integer", "null"]},
        "start_time": {"type": ["string", "null"]},
        "match_date": {"type": ["string", "null"]},
        "league": {"type": ["string", "null"]},
        "season": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]}
    }
}

# Match score root schema
MATCH_SCORE_ROOT_SCHEMA = {
    "type": "object",
    "required": ["matches"],
    "properties": {
        "matches": {
            "type": "array",
            "items": MATCH_SCORE_SCHEMA
        },
        "total_matches": {"type": "integer"},
        "season": {"type": "string"}
    }
}


class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(self, valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def __bool__(self):
        return self.valid
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


class DataValidator:
    """
    Validates incoming JSON data from scrapers.
    
    Uses JSON Schema validation to ensure data integrity and catch
    scraper format changes early.
    
    Example usage:
        validator = DataValidator()
        
        # Validate Betano data
        result = validator.validate_betano(betano_json)
        if not result.valid:
            print(f"Validation errors: {result.errors}")
        
        # Validate match score data
        result = validator.validate_match_scores(match_score_json)
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize validator.
        
        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
        self._validation_count = 0
        self._error_count = 0
    
    def validate_betano(self, data: Any) -> ValidationResult:
        """
        Validate Betano scraper output.
        
        Args:
            data: Parsed JSON data from Betano scraper
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []
        
        # Basic type check
        if not isinstance(data, list):
            return ValidationResult(False, ["Expected array at root level"])
        
        if len(data) == 0:
            warnings.append("Empty data array")
        
        # Validate each league
        for i, league in enumerate(data):
            league_errors = self._validate_betano_league(league, i)
            errors.extend(league_errors)
        
        self._validation_count += 1
        if errors:
            self._error_count += 1
        
        valid = len(errors) == 0 and (not self.strict or len(warnings) == 0)
        return ValidationResult(valid, errors, warnings)
    
    def _validate_betano_league(self, league: Dict, index: int) -> List[str]:
        """Validate a single Betano league."""
        errors = []
        prefix = f"League[{index}]"
        
        if not isinstance(league, dict):
            return [f"{prefix}: Expected object, got {type(league).__name__}"]
        
        # Required fields
        if "league_id" not in league:
            errors.append(f"{prefix}: Missing required field 'league_id'")
        if "league_name" not in league:
            errors.append(f"{prefix}: Missing required field 'league_name'")
        
        # Validate fixtures if present
        fixtures = league.get("fixtures", [])
        if not isinstance(fixtures, list):
            errors.append(f"{prefix}: 'fixtures' must be an array")
        else:
            for j, fixture in enumerate(fixtures):
                fixture_errors = self._validate_betano_fixture(fixture, f"{prefix}.fixtures[{j}]")
                errors.extend(fixture_errors)
        
        return errors
    
    def _validate_betano_fixture(self, fixture: Dict, prefix: str) -> List[str]:
        """Validate a single Betano fixture."""
        errors = []
        
        if not isinstance(fixture, dict):
            return [f"{prefix}: Expected object, got {type(fixture).__name__}"]
        
        # Required fields
        required = ["fixture_id", "home_team_name", "away_team_name", "start_time"]
        for field in required:
            if field not in fixture:
                errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Type checks
        if "fixture_id" in fixture and not isinstance(fixture["fixture_id"], str):
            errors.append(f"{prefix}: 'fixture_id' must be a string")
        
        if "odds" in fixture:
            odds = fixture["odds"]
            if not isinstance(odds, list):
                errors.append(f"{prefix}: 'odds' must be an array")
            else:
                for k, odd in enumerate(odds):
                    if not isinstance(odd, dict):
                        errors.append(f"{prefix}.odds[{k}]: Expected object")
                    elif "odds_value" in odd and not isinstance(odd["odds_value"], (int, float)):
                        errors.append(f"{prefix}.odds[{k}]: 'odds_value' must be a number")
        
        return errors
    
    def validate_match_scores(self, data: Any) -> ValidationResult:
        """
        Validate match score scraper output (Flashscore/Livescore).
        
        Args:
            data: Parsed JSON data from match score scraper
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []
        
        # Basic type check
        if not isinstance(data, dict):
            return ValidationResult(False, ["Expected object at root level"])
        
        # Required fields
        if "matches" not in data:
            errors.append("Missing required field 'matches'")
            return ValidationResult(False, errors, warnings)
        
        matches = data["matches"]
        if not isinstance(matches, list):
            return ValidationResult(False, ["'matches' must be an array"])
        
        if len(matches) == 0:
            warnings.append("Empty matches array")
        
        # Validate each match
        for i, match in enumerate(matches):
            match_errors = self._validate_match_score(match, i)
            errors.extend(match_errors)
        
        self._validation_count += 1
        if errors:
            self._error_count += 1
        
        valid = len(errors) == 0 and (not self.strict or len(warnings) == 0)
        return ValidationResult(valid, errors, warnings)
    
    def _validate_match_score(self, match: Dict, index: int) -> List[str]:
        """Validate a single match score."""
        errors = []
        prefix = f"matches[{index}]"
        
        if not isinstance(match, dict):
            return [f"{prefix}: Expected object, got {type(match).__name__}"]
        
        # Required fields
        if "home_team_name" not in match:
            errors.append(f"{prefix}: Missing required field 'home_team_name'")
        if "away_team_name" not in match:
            errors.append(f"{prefix}: Missing required field 'away_team_name'")
        
        # Type checks for scores
        if "home_score" in match and match["home_score"] is not None:
            if not isinstance(match["home_score"], int):
                errors.append(f"{prefix}: 'home_score' must be an integer")
        
        if "away_score" in match and match["away_score"] is not None:
            if not isinstance(match["away_score"], int):
                errors.append(f"{prefix}: 'away_score' must be an integer")
        
        return errors
    
    def validate_json_string(self, json_str: str, source: str) -> Tuple[Any, ValidationResult]:
        """
        Parse and validate a JSON string.
        
        Args:
            json_str: JSON string to parse and validate
            source: Source identifier ("betano", "flashscore", or "livescore")
            
        Returns:
            Tuple of (parsed_data, ValidationResult)
        """
        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return None, ValidationResult(False, [f"Invalid JSON: {e}"])
        
        # Validate based on source
        if source == "betano":
            result = self.validate_betano(data)
        elif source in ["flashscore", "livescore"]:
            result = self.validate_match_scores(data)
        else:
            result = ValidationResult(False, [f"Unknown source: {source}"])
        
        return data, result
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return {
            "validation_count": self._validation_count,
            "error_count": self._error_count,
            "success_rate": (
                (self._validation_count - self._error_count) / self._validation_count
                if self._validation_count > 0 else 0
            )
        }
