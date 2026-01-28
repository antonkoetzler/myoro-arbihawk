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

# Stock price data schema
STOCK_PRICE_SCHEMA = {
    "type": "object",
    "required": ["timestamp"],
    "properties": {
        "timestamp": {"type": "string"},
        "open": {"type": ["number", "null"]},
        "high": {"type": ["number", "null"]},
        "low": {"type": ["number", "null"]},
        "close": {"type": ["number", "null"]},
        "volume": {"type": ["number", "null"]}
    }
}

# Stock result schema (from scraper)
STOCK_RESULT_SCHEMA = {
    "type": "object",
    "required": ["symbol", "success"],
    "properties": {
        "symbol": {"type": "string"},
        "success": {"type": "boolean"},
        "source": {"type": ["string", "null"]},
        "prices": {
            "type": "array",
            "items": STOCK_PRICE_SCHEMA
        },
        "metadata": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "sector": {"type": ["string", "null"]},
                "industry": {"type": ["string", "null"]},
                "market_cap": {"type": ["number", "null"]},
                "exchange": {"type": ["string", "null"]}
            }
        },
        "error": {"type": ["string", "null"]}
    }
}

# Stock root schema (array of stock results)
STOCK_ROOT_SCHEMA = {
    "type": "array",
    "items": STOCK_RESULT_SCHEMA
}

# Crypto price data schema (same as stock)
CRYPTO_PRICE_SCHEMA = {
    "type": "object",
    "required": ["timestamp"],
    "properties": {
        "timestamp": {"type": "string"},
        "open": {"type": ["number", "null"]},
        "high": {"type": ["number", "null"]},
        "low": {"type": ["number", "null"]},
        "close": {"type": ["number", "null"]},
        "volume": {"type": ["number", "null"]}
    }
}

# Crypto result schema (from scraper)
CRYPTO_RESULT_SCHEMA = {
    "type": "object",
    "required": ["symbol", "success"],
    "properties": {
        "symbol": {"type": "string"},
        "success": {"type": "boolean"},
        "source": {"type": ["string", "null"]},
        "prices": {
            "type": "array",
            "items": CRYPTO_PRICE_SCHEMA
        },
        "metadata": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "category": {"type": ["string", "null"]},
                "market_cap": {"type": ["number", "null"]}
            }
        },
        "error": {"type": ["string", "null"]}
    }
}

# Crypto root schema (array of crypto results)
CRYPTO_ROOT_SCHEMA = {
    "type": "array",
    "items": CRYPTO_RESULT_SCHEMA
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
        elif source == "stocks":
            result = self.validate_stocks(data)
        elif source == "crypto":
            result = self.validate_crypto(data)
        else:
            result = ValidationResult(False, [f"Unknown source: {source}"])
        
        return data, result
    
    def validate_stocks(self, data: Any) -> ValidationResult:
        """
        Validate stock scraper output.
        
        Args:
            data: Parsed JSON data from stock scraper
            
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
        
        # Validate each stock result
        for i, stock_result in enumerate(data):
            stock_errors = self._validate_stock_result(stock_result, i)
            errors.extend(stock_errors)
        
        self._validation_count += 1
        if errors:
            self._error_count += 1
        
        valid = len(errors) == 0 and (not self.strict or len(warnings) == 0)
        return ValidationResult(valid, errors, warnings)
    
    def _validate_stock_result(self, stock_result: Dict, index: int) -> List[str]:
        """Validate a single stock result."""
        errors = []
        prefix = f"Stock[{index}]"
        
        if not isinstance(stock_result, dict):
            return [f"{prefix}: Expected object, got {type(stock_result).__name__}"]
        
        # Required fields
        if "symbol" not in stock_result:
            errors.append(f"{prefix}: Missing required field 'symbol'")
        if "success" not in stock_result:
            errors.append(f"{prefix}: Missing required field 'success'")
        
        # Validate prices if present
        if "prices" in stock_result:
            if not isinstance(stock_result["prices"], list):
                errors.append(f"{prefix}: 'prices' must be an array")
            else:
                for j, price in enumerate(stock_result["prices"]):
                    if not isinstance(price, dict):
                        errors.append(f"{prefix}.prices[{j}]: Expected object")
                    elif "timestamp" not in price:
                        errors.append(f"{prefix}.prices[{j}]: Missing required field 'timestamp'")
        
        return errors
    
    def validate_crypto(self, data: Any) -> ValidationResult:
        """
        Validate crypto scraper output.
        
        Args:
            data: Parsed JSON data from crypto scraper
            
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
        
        # Validate each crypto result
        for i, crypto_result in enumerate(data):
            crypto_errors = self._validate_crypto_result(crypto_result, i)
            errors.extend(crypto_errors)
        
        self._validation_count += 1
        if errors:
            self._error_count += 1
        
        valid = len(errors) == 0 and (not self.strict or len(warnings) == 0)
        return ValidationResult(valid, errors, warnings)
    
    def _validate_crypto_result(self, crypto_result: Dict, index: int) -> List[str]:
        """Validate a single crypto result."""
        errors = []
        prefix = f"Crypto[{index}]"
        
        if not isinstance(crypto_result, dict):
            return [f"{prefix}: Expected object, got {type(crypto_result).__name__}"]
        
        # Required fields
        if "symbol" not in crypto_result:
            errors.append(f"{prefix}: Missing required field 'symbol'")
        if "success" not in crypto_result:
            errors.append(f"{prefix}: Missing required field 'success'")
        
        # Validate prices if present
        if "prices" in crypto_result:
            if not isinstance(crypto_result["prices"], list):
                errors.append(f"{prefix}: 'prices' must be an array")
            else:
                for j, price in enumerate(crypto_result["prices"]):
                    if not isinstance(price, dict):
                        errors.append(f"{prefix}.prices[{j}]: Expected object")
                    elif "timestamp" not in price:
                        errors.append(f"{prefix}.prices[{j}]: Missing required field 'timestamp'")
        
        return errors
    
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
