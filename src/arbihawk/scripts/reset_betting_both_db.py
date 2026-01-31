"""
Reset betting domain on both prod and debug databases.
Run from arbihawk dir: python -m scripts.reset_betting_both_db
"""
import config
from data.database import Database

PROD_PATH = config.BASE_DIR / "data" / "arbihawk.db"
DEBUG_PATH = config.BASE_DIR / "data" / "arbihawk_debug.db"


def main() -> None:
    for label, path in [("prod", PROD_PATH), ("debug", DEBUG_PATH)]:
        if not path.exists():
            print(f"[{label}] skip (not found): {path}")
            continue
        db = Database(str(path))
        result = db.reset_betting_domain(preserve_models=True)
        print(f"[{label}] {path}: {result.get('total_deleted', 0)} deleted, backup {result.get('backup_path', '')}")


if __name__ == "__main__":
    main()
