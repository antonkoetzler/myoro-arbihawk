"""
Database backup system.
Automatic backups before critical operations.
"""

import shutil
import gzip
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import os

import config


class DatabaseBackup:
    """
    Manages database backups.
    
    Creates automatic backups before critical operations and maintains
    a rotation of recent backups.
    
    Example usage:
        backup = DatabaseBackup()
        
        # Create a backup
        backup_path = backup.create_backup("pre_training")
        
        # Restore from backup
        backup.restore_backup(backup_path)
    """
    
    def __init__(self, db_path: Optional[str] = None,
                 backup_dir: Optional[str] = None,
                 max_backups: Optional[int] = None,
                 compress: Optional[bool] = None):
        """
        Initialize backup manager.
        
        Args:
            db_path: Path to database file
            backup_dir: Directory for backups
            max_backups: Maximum number of backups to keep
            compress: Whether to compress backups
        """
        self.db_path = db_path or config.DB_PATH
        
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = Path(self.db_path).parent / "backups"
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_config = config.BACKUP_CONFIG
        self.max_backups = max_backups or backup_config.get("max_backups", 10)
        self.compress = compress if compress is not None else backup_config.get("compress", False)
    
    def create_backup(self, label: str = "manual") -> Optional[str]:
        """
        Create a database backup.
        
        Args:
            label: Backup label (e.g., "pre_training", "pre_rollback")
            
        Returns:
            Path to backup file or None on failure
        """
        if not Path(self.db_path).exists():
            return None
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"arbihawk_{label}_{timestamp}.db.backup"
        
        if self.compress:
            backup_name += ".gz"
        
        backup_path = self.backup_dir / backup_name
        
        try:
            if self.compress:
                # Compress backup
                with open(self.db_path, 'rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Simple copy
                shutil.copy2(self.db_path, backup_path)
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            print(f"Backup failed: {e}")
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True on success, False on failure
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            print(f"Backup file not found: {backup_path}")
            return False
        
        try:
            # Create backup of current database before restoring
            self.create_backup("pre_restore")
            
            if str(backup_path).endswith('.gz'):
                # Decompress and restore
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Simple copy
                shutil.copy2(backup_path, self.db_path)
            
            return True
            
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
    
    def list_backups(self) -> List[dict]:
        """
        List available backups.
        
        Returns:
            List of backup info dicts
        """
        backups = []
        
        for path in sorted(self.backup_dir.glob("arbihawk_*.db.backup*"), reverse=True):
            stat = path.stat()
            backups.append({
                "path": str(path),
                "filename": path.name,
                "size_mb": stat.st_size / (1024 * 1024),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "compressed": str(path).endswith('.gz')
            })
        
        return backups
    
    def _cleanup_old_backups(self) -> int:
        """
        Remove old backups beyond max_backups limit.
        
        Returns:
            Number of backups removed
        """
        backups = sorted(
            self.backup_dir.glob("arbihawk_*.db.backup*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        removed = 0
        for backup in backups[self.max_backups:]:
            try:
                backup.unlink()
                removed += 1
            except:
                pass
        
        return removed
    
    def get_latest_backup(self, label: Optional[str] = None) -> Optional[str]:
        """
        Get path to most recent backup.
        
        Args:
            label: Filter by label (optional)
            
        Returns:
            Path to latest backup or None
        """
        pattern = f"arbihawk_{label}_*.db.backup*" if label else "arbihawk_*.db.backup*"
        
        backups = sorted(
            self.backup_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if backups:
            return str(backups[0])
        
        return None
