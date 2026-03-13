"""Unit tests for graph warning utilities."""

import pytest
import os
from datetime import datetime
from src.algorithms.graph_warnings import save_warnings_to_file, load_warnings_from_file
from src.models.dependency import GraphWarning, WarningType
from src.storage.file_storage import FileStorage


class TestGraphWarnings:
    """Test graph warning save/load functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.storage = FileStorage()
        self.test_file = "test_warnings.json"
    
    def teardown_method(self):
        """Clean up test files."""
        try:
            filepath = os.path.join(self.storage.base_path, self.test_file)
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
    
    def test_save_empty_warnings(self):
        """Test saving empty warnings list."""
        warnings = []
        save_warnings_to_file(warnings, self.test_file)
        
        # Verify file was created
        filepath = os.path.join(self.storage.base_path, self.test_file)
        assert os.path.exists(filepath)
        
        # Verify content
        data = self.storage.read_json(self.test_file)
        assert data["warning_count"] == 0
        assert len(data["warnings"]) == 0
    
    def test_save_single_warning(self):
        """Test saving a single warning."""
        warnings = [
            GraphWarning(
                warning_type=WarningType.MISSING_DEPENDENCY,
                service_id="api-gateway",
                target_id="auth-service",
                message="Service 'api-gateway' depends on 'auth-service' which is not declared"
            )
        ]
        
        save_warnings_to_file(warnings, self.test_file)
        
        # Verify content
        data = self.storage.read_json(self.test_file)
        assert data["warning_count"] == 1
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["warning_type"] == "missing_dependency"
        assert data["warnings"][0]["service_id"] == "api-gateway"
        assert data["warnings"][0]["target_id"] == "auth-service"
    
    def test_save_multiple_warnings(self):
        """Test saving multiple warnings of different types."""
        warnings = [
            GraphWarning(
                warning_type=WarningType.MISSING_DEPENDENCY,
                service_id="api-gateway",
                target_id="auth-service",
                message="Missing dependency"
            ),
            GraphWarning(
                warning_type=WarningType.ISOLATED_NODE,
                service_id="standalone-service",
                message="Isolated node"
            ),
            GraphWarning(
                warning_type=WarningType.NO_TARGET,
                service_id="broken-service",
                message="No target specified"
            )
        ]
        
        save_warnings_to_file(warnings, self.test_file)
        
        # Verify content
        data = self.storage.read_json(self.test_file)
        assert data["warning_count"] == 3
        assert len(data["warnings"]) == 3
        
        # Verify warning types
        warning_types = {w["warning_type"] for w in data["warnings"]}
        assert "missing_dependency" in warning_types
        assert "isolated_node" in warning_types
        assert "no_target" in warning_types
    
    def test_load_warnings(self):
        """Test loading warnings from file."""
        # First save some warnings
        original_warnings = [
            GraphWarning(
                warning_type=WarningType.MISSING_DEPENDENCY,
                service_id="api-gateway",
                target_id="auth-service",
                message="Missing dependency"
            ),
            GraphWarning(
                warning_type=WarningType.ISOLATED_NODE,
                service_id="standalone-service",
                message="Isolated node"
            )
        ]
        
        save_warnings_to_file(original_warnings, self.test_file)
        
        # Load them back
        loaded_warnings = load_warnings_from_file(self.test_file)
        
        # Verify
        assert len(loaded_warnings) == 2
        assert loaded_warnings[0].warning_type == WarningType.MISSING_DEPENDENCY
        assert loaded_warnings[0].service_id == "api-gateway"
        assert loaded_warnings[0].target_id == "auth-service"
        assert loaded_warnings[1].warning_type == WarningType.ISOLATED_NODE
        assert loaded_warnings[1].service_id == "standalone-service"
    
    def test_save_load_roundtrip(self):
        """Test that save and load preserve all warning data."""
        original_warnings = [
            GraphWarning(
                warning_type=WarningType.MISSING_DEPENDENCY,
                service_id="service-a",
                target_id="service-b",
                message="Test message"
            )
        ]
        
        # Save and load
        save_warnings_to_file(original_warnings, self.test_file)
        loaded_warnings = load_warnings_from_file(self.test_file)
        
        # Verify all fields match
        assert len(loaded_warnings) == 1
        assert loaded_warnings[0].warning_type == original_warnings[0].warning_type
        assert loaded_warnings[0].service_id == original_warnings[0].service_id
        assert loaded_warnings[0].target_id == original_warnings[0].target_id
        assert loaded_warnings[0].message == original_warnings[0].message
    
    def test_load_nonexistent_file(self):
        """Test loading from a file that doesn't exist."""
        # FileStorage.read_json returns empty dict for nonexistent files
        # So load_warnings_from_file will return an empty list
        warnings = load_warnings_from_file("nonexistent_file.json")
        assert warnings == []
