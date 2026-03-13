"""
Tenant-aware storage layer for multi-tenant support.

This module provides a TenantStorage class that wraps FileStorage
and enforces tenant isolation by prefixing all paths with tenant_id.
"""

from typing import Any, Dict, Optional
from src.storage.file_storage import FileStorage


class TenantStorage:
    """
    Tenant-aware storage wrapper for multi-tenant isolation.
    
    Enforces tenant isolation by prefixing all file paths with tenant_id.
    This ensures that each tenant's data is stored in separate directories
    and cannot be accessed by other tenants.
    
    Attributes:
        storage: Underlying FileStorage instance
        tenant_id: Current tenant identifier
    """
    
    def __init__(self, storage: FileStorage, tenant_id: str):
        """
        Initialize TenantStorage with a FileStorage instance and tenant_id.
        
        Args:
            storage: FileStorage instance to wrap
            tenant_id: Tenant identifier for isolation
            
        Raises:
            ValueError: If tenant_id is empty or invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        self.storage = storage
        self.tenant_id = tenant_id.strip()
    
    def _get_tenant_path(self, path: str) -> str:
        """
        Get tenant-prefixed path.
        
        Args:
            path: Original path
            
        Returns:
            Path prefixed with tenant_id
        """
        # Remove leading slashes to avoid double slashes
        path = path.lstrip('/')
        return f"tenants/{self.tenant_id}/{path}"
    
    def read_json(self, path: str) -> Dict[str, Any]:
        """
        Read JSON file with tenant isolation.
        
        Args:
            path: Relative path from tenant's base directory
            
        Returns:
            Dictionary containing the JSON data, or empty dict if file doesn't exist
            
        Raises:
            json.JSONDecodeError: If the file contains invalid JSON
            IOError: If there's an error reading the file
        """
        tenant_path = self._get_tenant_path(path)
        return self.storage.read_json(tenant_path)
    
    def write_json(self, path: str, data: Dict[str, Any]):
        """
        Write JSON file with tenant isolation.
        
        Args:
            path: Relative path from tenant's base directory
            data: Dictionary to write as JSON
            
        Raises:
            IOError: If there's an error writing the file
        """
        tenant_path = self._get_tenant_path(path)
        self.storage.write_json(tenant_path, data)
    
    def append_json(self, path: str, data: Dict[str, Any]):
        """
        Append to JSON array file with tenant isolation.
        
        Args:
            path: Relative path from tenant's base directory
            data: Dictionary to append to the JSON array
            
        Raises:
            json.JSONDecodeError: If existing file contains invalid JSON
            IOError: If there's an error reading or writing the file
        """
        tenant_path = self._get_tenant_path(path)
        self.storage.append_json(tenant_path, data)
    
    def get_tenant_id(self) -> str:
        """
        Get the tenant identifier.
        
        Returns:
            Tenant identifier
        """
        return self.tenant_id


class TenantStorageFactory:
    """
    Factory for creating TenantStorage instances.
    
    Manages a shared FileStorage instance and creates tenant-specific
    storage wrappers on demand.
    """
    
    def __init__(self, base_path: str = "data"):
        """
        Initialize TenantStorageFactory.
        
        Args:
            base_path: Base directory for file storage
        """
        self.storage = FileStorage(base_path)
        self._tenant_storages: Dict[str, TenantStorage] = {}
    
    def get_tenant_storage(self, tenant_id: str) -> TenantStorage:
        """
        Get or create a TenantStorage instance for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            TenantStorage instance for the tenant
            
        Raises:
            ValueError: If tenant_id is empty or invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        tenant_id = tenant_id.strip()
        
        if tenant_id not in self._tenant_storages:
            self._tenant_storages[tenant_id] = TenantStorage(self.storage, tenant_id)
        
        return self._tenant_storages[tenant_id]
    
    def clear_cache(self, tenant_id: Optional[str] = None):
        """
        Clear cached TenantStorage instances.
        
        Args:
            tenant_id: Specific tenant to clear, or None to clear all
        """
        if tenant_id:
            self._tenant_storages.pop(tenant_id, None)
        else:
            self._tenant_storages.clear()
