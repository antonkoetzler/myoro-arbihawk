#!/usr/bin/env python3
"""
Export Arbihawk data for transfer to different computer.

Exports:
- Database file
- Model files (models/saved/*.pkl)
- Configuration files (config/*.json)
- Version information

Usage:
    python export_data.py [output_path]
    
If output_path is not provided, creates export in current directory with timestamp.
"""

import sys
import json
import zipfile
import sqlite3
from pathlib import Path
from datetime import datetime
import platform
import importlib.metadata

import config
from data.database import Database


def get_version_info() -> dict:
    """Get version information for the export."""
    db = Database()
    
    # Get schema version from database
    schema_version = None
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            if result and result[0] is not None:
                schema_version = result[0]
    except Exception:
        pass
    
    # Get Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Get platform info
    platform_info = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": python_version
    }
    
    # Try to get package versions
    package_versions = {}
    for package in ['pandas', 'numpy', 'xgboost', 'scikit-learn', 'optuna']:
        try:
            version = importlib.metadata.version(package)
            package_versions[package] = version
        except Exception:
            pass
    
    return {
        "exported_at": datetime.now().isoformat(),
        "schema_version": schema_version,
        "platform": platform_info,
        "package_versions": package_versions,
        "arbihawk_version": "1.0.0"  # Update this if you version your project
    }


def export_data(output_path: Path) -> None:
    """
    Export database, models, and config to a zip archive.
    
    Args:
        output_path: Path to output zip file
    """
    print(f"Exporting Arbihawk data to {output_path}...")
    
    base_dir = Path(__file__).parent
    db_path = Path(config.DB_PATH)
    
    # Check if database exists
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        print("Please ensure the database exists before exporting.")
        sys.exit(1)
    
    # Get version info
    print("Collecting version information...")
    version_info = get_version_info()
    
    # Create zip archive
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add database
        print(f"Adding database: {db_path.name}")
        zipf.write(db_path, f"data/{db_path.name}")
        
        # Add model files
        models_dir = base_dir / "models" / "saved"
        if models_dir.exists():
            model_files = list(models_dir.glob("*.pkl"))
            if model_files:
                print(f"Adding {len(model_files)} model file(s)...")
                for model_file in model_files:
                    zipf.write(model_file, f"models/saved/{model_file.name}")
                    print(f"  - {model_file.name}")
            else:
                print("No model files found in models/saved/")
        else:
            print("Models directory not found")
        
        # Add config files
        config_dir = base_dir / "config"
        if config_dir.exists():
            config_files = list(config_dir.glob("*.json"))
            if config_files:
                print(f"Adding {len(config_files)} config file(s)...")
                for config_file in config_files:
                    zipf.write(config_file, f"config/{config_file.name}")
                    print(f"  - {config_file.name}")
            else:
                print("No config files found in config/")
        else:
            print("Config directory not found")
        
        # Add version info as JSON
        print("Adding version information...")
        version_json = json.dumps(version_info, indent=2)
        zipf.writestr("VERSION.json", version_json)
    
    # Get archive size
    archive_size_mb = output_path.stat().st_size / (1024 * 1024)
    
    print(f"\nExport completed successfully!")
    print(f"Archive: {output_path}")
    print(f"Size: {archive_size_mb:.2f} MB")
    print(f"\nVersion information:")
    print(f"  Schema version: {version_info.get('schema_version', 'Unknown')}")
    print(f"  Exported at: {version_info.get('exported_at')}")
    print(f"  Platform: {version_info['platform']['system']} {version_info['platform']['release']}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
    else:
        # Default: timestamped export in current directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"arbihawk_export_{timestamp}.zip")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if output file already exists
    if output_path.exists():
        response = input(f"File {output_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Export cancelled.")
            sys.exit(0)
    
    try:
        export_data(output_path)
    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
