#!/usr/bin/env python3
"""
Import Arbihawk data from export archive.

Imports:
- Database file (with schema migration if needed)
- Model files
- Configuration files

Usage:
    python import_data.py <export_file.zip> [--overwrite-db] [--overwrite-models] [--overwrite-config]
"""

import sys
import json
import zipfile
import sqlite3
import argparse
from pathlib import Path
from shutil import copy2

import config
from data.database import Database


def load_version_info(zipf: zipfile.ZipFile) -> dict:
    """Load version information from export."""
    try:
        version_data = zipf.read("VERSION.json")
        return json.loads(version_data)
    except KeyError:
        print("WARNING: VERSION.json not found in export (old export format?)")
        return {}
    except Exception as e:
        print(f"WARNING: Failed to load version info: {e}")
        return {}


def check_schema_compatibility(export_version: dict, current_db: Database) -> bool:
    """
    Check if schema versions are compatible.
    
    Returns:
        True if compatible, False if migration needed
    """
    export_schema = export_version.get("schema_version")
    if export_schema is None:
        print("WARNING: Could not determine export schema version")
        return True  # Assume compatible
    
    # Get current schema version
    current_schema = None
    try:
        with current_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            if result and result[0] is not None:
                current_schema = result[0]
    except Exception:
        pass
    
    if current_schema is None:
        print("INFO: No existing database, will create new one")
        return True
    
    if export_schema > current_schema:
        print(f"INFO: Export schema version ({export_schema}) is newer than current ({current_schema})")
        print("      Database migrations will be applied automatically")
        return True
    elif export_schema < current_schema:
        print(f"WARNING: Export schema version ({export_schema}) is older than current ({current_schema})")
        print("         This may cause compatibility issues")
        response = input("Continue anyway? (y/N): ")
        return response.lower() == 'y'
    else:
        print(f"INFO: Schema versions match ({export_schema})")
        return True


def import_database(zipf: zipfile.ZipFile, overwrite: bool = False) -> None:
    """Import database from archive."""
    # Find database file in archive
    db_files = [f for f in zipf.namelist() if f.startswith("data/") and f.endswith(".db")]
    
    if not db_files:
        print("ERROR: No database file found in export")
        sys.exit(1)
    
    if len(db_files) > 1:
        print(f"WARNING: Multiple database files found: {db_files}")
        print(f"Using: {db_files[0]}")
    
    db_file = db_files[0]
    db_name = Path(db_file).name
    
    # Check if database already exists
    current_db_path = Path(config.DB_PATH)
    if current_db_path.exists() and not overwrite:
        print(f"ERROR: Database already exists at {current_db_path}")
        print("Use --overwrite-db to replace it")
        sys.exit(1)
    
    # Extract database
    print(f"Importing database: {db_name}")
    print(f"  Destination: {current_db_path}")
    
    # Ensure data directory exists
    current_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract to temporary location first
    temp_db = current_db_path.parent / f"{current_db_path.name}.tmp"
    with zipf.open(db_file) as source:
        with open(temp_db, 'wb') as target:
            target.write(source.read())
    
    # Replace existing database
    if current_db_path.exists():
        backup_path = current_db_path.parent / f"{current_db_path.name}.backup"
        print(f"  Backing up existing database to: {backup_path}")
        copy2(current_db_path, backup_path)
    
    temp_db.replace(current_db_path)
    print("  Database imported successfully")
    
    # Initialize schema (will run migrations if needed)
    print("  Initializing schema and running migrations...")
    db = Database(db_path=str(current_db_path))
    print("  Schema initialized")


def import_models(zipf: zipfile.ZipFile, overwrite: bool = False) -> None:
    """Import model files from archive."""
    model_files = [f for f in zipf.namelist() if f.startswith("models/saved/") and f.endswith(".pkl")]
    
    if not model_files:
        print("No model files found in export")
        return
    
    base_dir = Path(__file__).parent
    models_dir = base_dir / "models" / "saved"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Importing {len(model_files)} model file(s)...")
    for model_file in model_files:
        model_name = Path(model_file).name
        target_path = models_dir / model_name
        
        if target_path.exists() and not overwrite:
            print(f"  SKIP: {model_name} (already exists, use --overwrite-models to replace)")
            continue
        
        print(f"  - {model_name}")
        with zipf.open(model_file) as source:
            with open(target_path, 'wb') as target:
                target.write(source.read())


def import_config(zipf: zipfile.ZipFile, overwrite: bool = False) -> None:
    """Import configuration files from archive."""
    config_files = [f for f in zipf.namelist() if f.startswith("config/") and f.endswith(".json")]
    
    if not config_files:
        print("No config files found in export")
        return
    
    base_dir = Path(__file__).parent
    config_dir = base_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Importing {len(config_files)} config file(s)...")
    for config_file in config_files:
        config_name = Path(config_file).name
        target_path = config_dir / config_name
        
        if target_path.exists() and not overwrite:
            print(f"  SKIP: {config_name} (already exists, use --overwrite-config to replace)")
            continue
        
        print(f"  - {config_name}")
        with zipf.open(config_file) as source:
            with open(target_path, 'wb') as target:
                target.write(source.read())


def import_data(export_path: Path, overwrite_db: bool = False,
                overwrite_models: bool = False, overwrite_config: bool = False) -> None:
    """
    Import data from export archive.
    
    Args:
        export_path: Path to export zip file
        overwrite_db: Overwrite existing database
        overwrite_models: Overwrite existing model files
        overwrite_config: Overwrite existing config files
    """
    if not export_path.exists():
        print(f"ERROR: Export file not found: {export_path}")
        sys.exit(1)
    
    print(f"Importing from: {export_path}")
    
    with zipfile.ZipFile(export_path, 'r') as zipf:
        # Load version info
        version_info = load_version_info(zipf)
        
        if version_info:
            print("\nExport information:")
            print(f"  Exported at: {version_info.get('exported_at', 'Unknown')}")
            print(f"  Schema version: {version_info.get('schema_version', 'Unknown')}")
            print(f"  Platform: {version_info.get('platform', {}).get('system', 'Unknown')}")
        
        # Check schema compatibility
        print("\nChecking schema compatibility...")
        current_db = Database()
        if not check_schema_compatibility(version_info, current_db):
            print("Import cancelled due to schema incompatibility")
            sys.exit(1)
        
        # Import components
        print("\nImporting components...")
        import_database(zipf, overwrite=overwrite_db)
        import_models(zipf, overwrite=overwrite_models)
        import_config(zipf, overwrite=overwrite_config)
    
    print("\nImport completed successfully!")
    print("\nNext steps:")
    print("  1. Verify database and models are working")
    print("  2. Review imported configuration files")
    print("  3. Run a test training cycle to ensure everything works")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import Arbihawk data from export archive"
    )
    parser.add_argument(
        "export_file",
        type=Path,
        help="Path to export zip file"
    )
    parser.add_argument(
        "--overwrite-db",
        action="store_true",
        help="Overwrite existing database"
    )
    parser.add_argument(
        "--overwrite-models",
        action="store_true",
        help="Overwrite existing model files"
    )
    parser.add_argument(
        "--overwrite-config",
        action="store_true",
        help="Overwrite existing config files"
    )
    
    args = parser.parse_args()
    
    try:
        import_data(
            args.export_file,
            overwrite_db=args.overwrite_db,
            overwrite_models=args.overwrite_models,
            overwrite_config=args.overwrite_config
        )
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
