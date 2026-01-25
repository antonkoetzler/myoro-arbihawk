# Arbihawk Test Suite

Comprehensive test suite for the Arbihawk betting prediction system.

## Overview

This test suite covers critical flows and edge cases to ensure system reliability:

- **Ingestion Flow Tests**: Data ingestion from scrapers, duplicate prevention, foreign key integrity
- **Model Training Tests**: Model versioning, activation, multi-market support
- **Betting Flow Tests**: Bet placement, settlement, bankroll tracking
- **Database Integrity Tests**: Foreign key constraints, uniqueness, data consistency
- **End-to-End Tests**: Complete flows from ingestion to betting

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_ingestion_flow.py
```

### Run with coverage
```bash
pytest --cov=data --cov=models --cov=testing
```

### Run with verbose output
```bash
pytest -v
```

## Test Structure

- `conftest.py`: Shared fixtures (temp database, sample data)
- `test_ingestion_flow.py`: Ingestion pipeline tests
- `test_model_training.py`: Model training and versioning tests
- `test_betting_flow.py`: Betting and settlement tests
- `test_database_integrity.py`: Database integrity and constraint tests
- `test_end_to_end.py`: Complete integration flow tests

## Fixtures

- `temp_db`: Temporary database instance (auto-cleaned)
- `ingestion_service`: DataIngestionService with test database
- `sample_betano_data`: Sample Betano fixture data
- `sample_flashscore_data`: Sample FlashScore match data

## Writing New Tests

1. Use fixtures from `conftest.py` for database and services
2. Follow naming convention: `test_<feature>_<scenario>`
3. Clean up test data (fixtures handle this automatically)
4. Test both success and failure cases
5. Verify data integrity after operations

## Continuous Integration

Tests should pass before merging code. All critical flows are covered to prevent regressions.

## Test Requirements for Critical Features

**MANDATORY: Create tests for all critical features**

When implementing or modifying critical functionality, you MUST create comprehensive tests. This is not optional - tests are required for:

- **Data ingestion flows** - All scraper data ingestion, validation, and storage
- **Model training pipeline** - Model versioning, activation, performance tracking
- **Betting operations** - Bet placement, settlement, bankroll management
- **Database operations** - Schema changes, migrations, data integrity
- **API endpoints** - All dashboard and automation APIs
- **Integration flows** - Complete workflows from ingestion to betting

**Test coverage requirements:**

- **End-to-end flows** - Test complete workflows, not just individual functions
- **Edge cases** - Test failures, invalid inputs, boundary conditions
- **Error handling** - Verify graceful degradation and proper error messages
- **Data integrity** - Verify foreign keys, constraints, and consistency
- **Backward compatibility** - Ensure changes don't break existing functionality

**If you implement a critical feature without tests, the work is incomplete.**
