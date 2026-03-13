"""
Unit tests for tenant-aware storage layer.
"""

import pytest
from pathlib import Path
from src.storage.file_storage import FileStorage
from src.storage.tenant_storage import TenantStorage, TenantStorageFactory


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary FileStorage instance."""
    return FileStorage(base_path=str(tmp_path / "data"))


@pytest.fixture
def tenant_storage(temp_storage):
    """Create a TenantStorage instance."""
    return TenantStorage(temp_storage, "tenant-1")


class TestTenantStorageInitialization:
    """Test TenantStorage initialization."""
    
    def test_init_with_valid_tenant_id(self, temp_storage):
        """Test initialization with valid tenant_id."""
        storage = TenantStorage(temp_storage, "tenant-1")
        assert storage.tenant_id == "tenant-1"
        assert storage.storage == temp_storage
    
    def test_init_with_empty_tenant_id(self, temp_storage):
        """Test initialization with empty tenant_id raises error."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            TenantStorage(temp_storage, "")
    
    def test_init_with_whitespace_tenant_id(self, temp_storage):
        """Test initialization with whitespace-only tenant_id raises error."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            TenantStorage(temp_storage, "   ")
    
    def test_init_strips_whitespace(self, temp_storage):
        """Test that tenant_id whitespace is stripped."""
        storage = TenantStorage(temp_storage, "  tenant-1  ")
        assert storage.tenant_id == "tenant-1"


class TestTenantPathPrefixing:
    """Test tenant path prefixing."""
    
    def test_get_tenant_path_basic(self, tenant_storage):
        """Test basic tenant path prefixing."""
        path = tenant_storage._get_tenant_path("services/test.json")
        assert path == "tenants/tenant-1/services/test.json"
    
    def test_get_tenant_path_removes_leading_slash(self, tenant_storage):
        """Test that leading slashes are removed."""
        path = tenant_storage._get_tenant_path("/services/test.json")
        assert path == "tenants/tenant-1/services/test.json"
    
    def test_get_tenant_path_multiple_leading_slashes(self, tenant_storage):
        """Test that multiple leading slashes are removed."""
        path = tenant_storage._get_tenant_path("///services/test.json")
        assert path == "tenants/tenant-1/services/test.json"
    
    def test_get_tenant_path_nested_directories(self, tenant_storage):
        """Test tenant path with nested directories."""
        path = tenant_storage._get_tenant_path("services/api/metrics/data.json")
        assert path == "tenants/tenant-1/services/api/metrics/data.json"


class TestTenantStorageReadWrite:
    """Test tenant storage read/write operations."""
    
    def test_write_and_read_json(self, tenant_storage):
        """Test writing and reading JSON with tenant isolation."""
        data = {"service_id": "api-1", "availability": 99.9}
        
        tenant_storage.write_json("services/api-1/metadata.json", data)
        result = tenant_storage.read_json("services/api-1/metadata.json")
        
        assert result == data
    
    def test_read_nonexistent_file(self, tenant_storage):
        """Test reading nonexistent file returns empty dict."""
        result = tenant_storage.read_json("nonexistent/file.json")
        assert result == {}
    
    def test_write_creates_directories(self, tenant_storage, tmp_path):
        """Test that write creates necessary directories."""
        data = {"test": "data"}
        tenant_storage.write_json("deep/nested/path/file.json", data)
        
        # Check that the file was created in the correct tenant directory
        expected_path = tmp_path / "data" / "tenants" / "tenant-1" / "deep" / "nested" / "path" / "file.json"
        assert expected_path.exists()
    
    def test_append_json(self, tenant_storage):
        """Test appending to JSON array."""
        data1 = {"id": 1, "value": "first"}
        data2 = {"id": 2, "value": "second"}
        
        tenant_storage.append_json("logs/audit.json", data1)
        tenant_storage.append_json("logs/audit.json", data2)
        
        result = tenant_storage.read_json("logs/audit.json")
        
        assert len(result) == 2
        assert result[0] == data1
        assert result[1] == data2
    
    def test_append_creates_array(self, tenant_storage):
        """Test that append creates array if file doesn't exist."""
        data = {"id": 1, "value": "first"}
        
        tenant_storage.append_json("logs/new.json", data)
        result = tenant_storage.read_json("logs/new.json")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == data


class TestTenantIsolation:
    """Test tenant isolation."""
    
    def test_different_tenants_isolated(self, temp_storage):
        """Test that different tenants have isolated storage."""
        tenant1 = TenantStorage(temp_storage, "tenant-1")
        tenant2 = TenantStorage(temp_storage, "tenant-2")
        
        data1 = {"service": "api-1", "tenant": "tenant-1"}
        data2 = {"service": "api-2", "tenant": "tenant-2"}
        
        tenant1.write_json("services/api.json", data1)
        tenant2.write_json("services/api.json", data2)
        
        # Each tenant should read their own data
        assert tenant1.read_json("services/api.json") == data1
        assert tenant2.read_json("services/api.json") == data2
    
    def test_tenant_cannot_access_other_tenant_data(self, temp_storage):
        """Test that tenant cannot access other tenant's data."""
        tenant1 = TenantStorage(temp_storage, "tenant-1")
        tenant2 = TenantStorage(temp_storage, "tenant-2")
        
        data = {"secret": "data"}
        tenant1.write_json("secrets/data.json", data)
        
        # Tenant2 should not see tenant1's data
        result = tenant2.read_json("secrets/data.json")
        assert result == {}
    
    def test_multiple_tenants_same_path(self, temp_storage):
        """Test multiple tenants can use same relative paths."""
        tenants = [
            TenantStorage(temp_storage, f"tenant-{i}")
            for i in range(3)
        ]
        
        # Each tenant writes to the same relative path
        for i, tenant in enumerate(tenants):
            data = {"tenant_id": f"tenant-{i}", "index": i}
            tenant.write_json("config/settings.json", data)
        
        # Each tenant reads their own data
        for i, tenant in enumerate(tenants):
            result = tenant.read_json("config/settings.json")
            assert result["tenant_id"] == f"tenant-{i}"
            assert result["index"] == i


class TestTenantStorageFactory:
    """Test TenantStorageFactory."""
    
    def test_factory_initialization(self, tmp_path):
        """Test factory initialization."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        assert factory.storage is not None
        assert len(factory._tenant_storages) == 0
    
    def test_get_tenant_storage_creates_instance(self, tmp_path):
        """Test that get_tenant_storage creates instance."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        
        storage = factory.get_tenant_storage("tenant-1")
        
        assert isinstance(storage, TenantStorage)
        assert storage.tenant_id == "tenant-1"
    
    def test_get_tenant_storage_caches_instance(self, tmp_path):
        """Test that get_tenant_storage caches instances."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        
        storage1 = factory.get_tenant_storage("tenant-1")
        storage2 = factory.get_tenant_storage("tenant-1")
        
        assert storage1 is storage2
    
    def test_get_tenant_storage_different_tenants(self, tmp_path):
        """Test that different tenants get different instances."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        
        storage1 = factory.get_tenant_storage("tenant-1")
        storage2 = factory.get_tenant_storage("tenant-2")
        
        assert storage1 is not storage2
        assert storage1.tenant_id == "tenant-1"
        assert storage2.tenant_id == "tenant-2"
    
    def test_get_tenant_storage_invalid_tenant_id(self, tmp_path):
        """Test that invalid tenant_id raises error."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            factory.get_tenant_storage("")
    
    def test_clear_cache_specific_tenant(self, tmp_path):
        """Test clearing cache for specific tenant."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        
        storage1 = factory.get_tenant_storage("tenant-1")
        storage2 = factory.get_tenant_storage("tenant-2")
        
        assert len(factory._tenant_storages) == 2
        
        factory.clear_cache("tenant-1")
        
        assert len(factory._tenant_storages) == 1
        assert "tenant-2" in factory._tenant_storages
    
    def test_clear_cache_all_tenants(self, tmp_path):
        """Test clearing cache for all tenants."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        
        factory.get_tenant_storage("tenant-1")
        factory.get_tenant_storage("tenant-2")
        factory.get_tenant_storage("tenant-3")
        
        assert len(factory._tenant_storages) == 3
        
        factory.clear_cache()
        
        assert len(factory._tenant_storages) == 0
    
    def test_factory_shared_underlying_storage(self, tmp_path):
        """Test that factory uses shared underlying storage."""
        factory = TenantStorageFactory(base_path=str(tmp_path / "data"))
        
        storage1 = factory.get_tenant_storage("tenant-1")
        storage2 = factory.get_tenant_storage("tenant-2")
        
        # Both should use the same underlying FileStorage
        assert storage1.storage is storage2.storage
        assert storage1.storage is factory.storage


class TestTenantStorageEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_special_characters_in_tenant_id(self, temp_storage):
        """Test tenant_id with special characters."""
        # Tenant IDs should be alphanumeric with hyphens/underscores
        storage = TenantStorage(temp_storage, "tenant-1_prod")
        assert storage.tenant_id == "tenant-1_prod"
    
    def test_get_tenant_id(self, tenant_storage):
        """Test get_tenant_id method."""
        assert tenant_storage.get_tenant_id() == "tenant-1"
    
    def test_large_data_write_read(self, tenant_storage):
        """Test writing and reading large data."""
        large_data = {
            f"key_{i}": f"value_{i}" * 100
            for i in range(1000)
        }
        
        tenant_storage.write_json("large/data.json", large_data)
        result = tenant_storage.read_json("large/data.json")
        
        assert result == large_data
    
    def test_unicode_in_data(self, tenant_storage):
        """Test handling of unicode characters."""
        data = {
            "emoji": "🚀🎉",
            "chinese": "你好",
            "arabic": "مرحبا",
            "russian": "Привет"
        }
        
        tenant_storage.write_json("unicode/data.json", data)
        result = tenant_storage.read_json("unicode/data.json")
        
        assert result == data
    
    def test_nested_tenant_paths(self, tenant_storage):
        """Test deeply nested paths."""
        data = {"level": 10}
        path = "a/b/c/d/e/f/g/h/i/j/data.json"
        
        tenant_storage.write_json(path, data)
        result = tenant_storage.read_json(path)
        
        assert result == data
