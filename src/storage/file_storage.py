"""
File-based storage with thread-safe file locking.

This module provides a FileStorage class that implements thread-safe
file operations using fcntl for file locking to prevent race conditions
during concurrent access.
"""

import json
import fcntl
from pathlib import Path
from typing import Any, Dict, List
from contextlib import contextmanager


class FileStorage:
    """
    Thread-safe file-based storage with file locking.
    
    Provides methods for reading, writing, and appending JSON data
    with automatic directory creation and file locking to prevent
    race conditions during concurrent access.
    
    Attributes:
        base_path: Base directory for all file operations
    """
    
    def __init__(self, base_path: str = "data"):
        """
        Initialize FileStorage with a base path.
        
        Args:
            base_path: Base directory for file storage (default: "data")
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _lock_file(self, file_path: Path):
        """
        Context manager for file locking.
        
        Creates a lock file and acquires an exclusive lock using fcntl.
        The lock is automatically released when the context exits.
        
        Args:
            file_path: Path to the file to lock
            
        Yields:
            None
        """
        lock_path = file_path.with_suffix(file_path.suffix + '.lock')
        lock_file = open(lock_path, 'w')
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
    
    def read_json(self, path: str) -> Dict[str, Any]:
        """
        Read JSON file with locking.
        
        Args:
            path: Relative path from base_path to the JSON file
            
        Returns:
            Dictionary containing the JSON data, or empty dict if file doesn't exist
            
        Raises:
            json.JSONDecodeError: If the file contains invalid JSON
            IOError: If there's an error reading the file
        """
        file_path = self.base_path / path
        if not file_path.exists():
            return {}
        
        with self._lock_file(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
    
    def write_json(self, path: str, data: Dict[str, Any]):
        """
        Write JSON file with locking.
        
        Automatically creates parent directories if they don't exist.
        
        Args:
            path: Relative path from base_path to the JSON file
            data: Dictionary to write as JSON
            
        Raises:
            IOError: If there's an error writing the file
        """
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._lock_file(file_path):
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
    
    def append_json(self, path: str, data: Dict[str, Any]):
        """
        Append to JSON array file (for audit logs).
        
        Reads existing JSON array, appends new data, and writes back.
        If file doesn't exist, creates a new array with the data.
        Automatically creates parent directories if they don't exist.
        
        Args:
            path: Relative path from base_path to the JSON file
            data: Dictionary to append to the JSON array
            
        Raises:
            json.JSONDecodeError: If existing file contains invalid JSON
            IOError: If there's an error reading or writing the file
        """
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._lock_file(file_path):
            existing: List[Dict[str, Any]] = []
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing = json.load(f)
            
            existing.append(data)
            
            with open(file_path, 'w') as f:
                json.dump(existing, f, indent=2)
