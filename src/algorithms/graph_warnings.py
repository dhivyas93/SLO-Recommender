"""Utilities for handling graph construction warnings."""

from typing import List
from datetime import datetime
from src.models.dependency import GraphWarning
from src.storage.file_storage import FileStorage


def save_warnings_to_file(warnings: List[GraphWarning], filepath: str) -> None:
    """
    Save graph warnings to a JSON file.
    
    Args:
        warnings: List of GraphWarning objects to save
        filepath: Path to the output file (relative to data directory)
    
    Example:
        >>> from src.models.dependency import GraphWarning, WarningType
        >>> warnings = [
        ...     GraphWarning(
        ...         warning_type=WarningType.MISSING_DEPENDENCY,
        ...         service_id="api-gateway",
        ...         target_id="auth-service",
        ...         message="Service 'api-gateway' depends on 'auth-service' which is not declared"
        ...     )
        ... ]
        >>> save_warnings_to_file(warnings, "dependencies/warnings.json")
    """
    storage = FileStorage()
    
    # Convert warnings to dict format for JSON serialization
    warnings_data = {
        "generated_at": datetime.now().isoformat(),
        "warning_count": len(warnings),
        "warnings": [
            {
                "warning_type": w.warning_type.value,
                "service_id": w.service_id,
                "target_id": w.target_id,
                "message": w.message,
                "timestamp": w.timestamp.isoformat()
            }
            for w in warnings
        ]
    }
    
    storage.write_json(filepath, warnings_data)


def load_warnings_from_file(filepath: str) -> List[GraphWarning]:
    """
    Load graph warnings from a JSON file.
    
    Args:
        filepath: Path to the input file (relative to data directory)
    
    Returns:
        List of GraphWarning objects
    
    Example:
        >>> warnings = load_warnings_from_file("dependencies/warnings.json")
        >>> print(f"Loaded {len(warnings)} warnings")
    """
    from src.models.dependency import WarningType
    from dateutil import parser
    
    storage = FileStorage()
    data = storage.read_json(filepath)
    
    warnings = []
    for w_data in data.get("warnings", []):
        warning = GraphWarning(
            warning_type=WarningType(w_data["warning_type"]),
            service_id=w_data["service_id"],
            target_id=w_data.get("target_id"),
            message=w_data["message"],
            timestamp=parser.isoparse(w_data["timestamp"])
        )
        warnings.append(warning)
    
    return warnings
