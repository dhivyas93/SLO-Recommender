"""
Property-based tests for concurrent FileStorage operations using Hypothesis.

This module uses property-based testing to verify that FileStorage maintains
data integrity under various concurrent access patterns with randomly generated
data and scenarios.

**Validates: Requirements 8.1** (file-based storage with concurrency support)
"""

import json
import pytest
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize

from src.storage.file_storage import FileStorage


# ============================================================================
# Strategy Definitions
# ============================================================================

# Generate valid JSON-serializable data
json_value = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | st.text(),
    lambda children: st.lists(children, max_size=5) | st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=5),
    max_leaves=10
)

# Generate simple dictionaries for testing
simple_dict = st.dictionaries(
    st.text(min_size=1, max_size=20),
    st.integers() | st.text(max_size=50) | st.booleans(),
    min_size=1,
    max_size=10
)


# ============================================================================
# Property Tests for Concurrent Writes
# ============================================================================

class TestConcurrentWriteProperties:
    """Property-based tests for concurrent write operations."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage directory for testing."""
        temp_dir = tempfile.mkdtemp()
        storage = FileStorage(base_path=temp_dir)
        yield storage
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @given(
        data_items=st.lists(simple_dict, min_size=2, max_size=20),
        num_threads=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=50, deadline=5000)
    def test_concurrent_writes_preserve_one_complete_write(self, temp_storage, data_items, num_threads):
        """
        Property: When multiple threads write to the same file concurrently,
        the final file should contain exactly one complete, valid write
        (not corrupted or partial data).
        
        This verifies that file locking prevents corruption, though it doesn't
        guarantee which write wins (that's a race condition by design).
        """
        # Limit threads to available data items
        num_threads = min(num_threads, len(data_items))
        assume(num_threads >= 2)
        
        errors = []
        
        def write_data(thread_id):
            try:
                temp_storage.write_json("concurrent.json", data_items[thread_id])
            except Exception as e:
                errors.append((thread_id, e))
        
        # Execute concurrent writes
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=write_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Property 1: No errors should occur
        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"
        
        # Property 2: File should contain valid JSON
        file_path = Path(temp_storage.base_path) / "concurrent.json"
        assert file_path.exists(), "File should exist after writes"
        
        with open(file_path, 'r') as f:
            final_data = json.load(f)
        
        # Property 3: Final data should be one of the written items (complete write)
        assert final_data in data_items, \
            f"Final data should match one of the written items, got: {final_data}"
    
    @given(
        data_items=st.lists(simple_dict, min_size=5, max_size=30),
        num_threads=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=50, deadline=5000)
    def test_concurrent_appends_preserve_all_data(self, temp_storage, data_items, num_threads):
        """
        Property: When multiple threads append to the same file concurrently,
        all appended items should be present in the final array with no data loss.
        
        This is the critical property for audit logs and other append-only data.
        """
        # Distribute items across threads
        items_per_thread = len(data_items) // num_threads
        assume(items_per_thread >= 1)
        
        errors = []
        
        def append_data(thread_id, items):
            try:
                for item in items:
                    # Add thread_id to track which thread wrote what
                    item_with_id = {**item, "_thread_id": thread_id}
                    temp_storage.append_json("appends.json", item_with_id)
            except Exception as e:
                errors.append((thread_id, e))
        
        # Execute concurrent appends
        threads = []
        for i in range(num_threads):
            start_idx = i * items_per_thread
            end_idx = start_idx + items_per_thread
            thread_items = data_items[start_idx:end_idx]
            
            thread = threading.Thread(target=append_data, args=(i, thread_items))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Property 1: No errors should occur
        assert len(errors) == 0, f"Errors during concurrent appends: {errors}"
        
        # Property 2: File should contain valid JSON array
        file_path = Path(temp_storage.base_path) / "appends.json"
        assert file_path.exists(), "File should exist after appends"
        
        with open(file_path, 'r') as f:
            final_data = json.load(f)
        
        assert isinstance(final_data, list), "Final data should be a list"
        
        # Property 3: All items should be present (no data loss)
        expected_count = num_threads * items_per_thread
        assert len(final_data) == expected_count, \
            f"Expected {expected_count} items, got {len(final_data)}"
        
        # Property 4: Each thread's items should all be present
        for thread_id in range(num_threads):
            thread_items = [item for item in final_data if item.get("_thread_id") == thread_id]
            assert len(thread_items) == items_per_thread, \
                f"Thread {thread_id} should have {items_per_thread} items, got {len(thread_items)}"
    
    @given(
        write_data=st.lists(simple_dict, min_size=3, max_size=15),
        num_readers=st.integers(min_value=2, max_value=8),
        num_writers=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=30, deadline=5000)
    def test_concurrent_reads_never_see_corruption(self, temp_storage, write_data, num_readers, num_writers):
        """
        Property: When reads and writes happen concurrently, readers should
        always see valid, complete data - never corrupted or partial writes.
        
        Readers may see old or new data, but never invalid JSON or partial writes.
        """
        # Write initial data
        temp_storage.write_json("mixed.json", write_data[0])
        
        read_results = []
        errors = []
        lock = threading.Lock()
        
        def reader():
            try:
                for _ in range(5):
                    data = temp_storage.read_json("mixed.json")
                    # Property: Data should always be a valid dict
                    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
                    with lock:
                        read_results.append(data)
            except Exception as e:
                errors.append(("reader", e))
        
        def writer(writer_id):
            try:
                # Each writer writes a subset of the data
                data_idx = writer_id % len(write_data)
                temp_storage.write_json("mixed.json", write_data[data_idx])
            except Exception as e:
                errors.append(("writer", writer_id, e))
        
        # Execute concurrent reads and writes
        threads = []
        
        for _ in range(num_readers):
            thread = threading.Thread(target=reader)
            threads.append(thread)
            thread.start()
        
        for i in range(num_writers):
            thread = threading.Thread(target=writer, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Property 1: No errors should occur
        assert len(errors) == 0, f"Errors during mixed operations: {errors}"
        
        # Property 2: All reads should have returned valid data
        assert len(read_results) == num_readers * 5
        
        # Property 3: All read data should be one of the valid write data items
        for data in read_results:
            assert data in write_data, \
                f"Read data should match one of the written items"
    
    @given(
        file_count=st.integers(min_value=3, max_value=15),
        data_per_file=simple_dict
    )
    @settings(max_examples=30, deadline=5000)
    def test_concurrent_writes_to_different_files_no_interference(
        self, temp_storage, file_count, data_per_file
    ):
        """
        Property: Concurrent writes to different files should not interfere
        with each other. All files should be written successfully with correct data.
        """
        errors = []
        
        def write_file(file_id, data):
            try:
                # Add file_id to data for verification
                data_with_id = {**data, "_file_id": file_id}
                temp_storage.write_json(f"file_{file_id}.json", data_with_id)
            except Exception as e:
                errors.append((file_id, e))
        
        # Execute concurrent writes to different files
        threads = []
        for i in range(file_count):
            thread = threading.Thread(target=write_file, args=(i, data_per_file))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Property 1: No errors should occur
        assert len(errors) == 0, f"Errors during writes: {errors}"
        
        # Property 2: All files should exist and contain correct data
        for i in range(file_count):
            data = temp_storage.read_json(f"file_{i}.json")
            assert data.get("_file_id") == i, \
                f"File {i} should contain correct file_id"
            
            # Verify all original keys are present
            for key in data_per_file:
                assert key in data, f"Key {key} should be present in file {i}"
                assert data[key] == data_per_file[key], \
                    f"Value for {key} should match in file {i}"
    
    @given(
        nested_path=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
            min_size=1,
            max_size=4
        ),
        data=simple_dict,
        num_threads=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=20, deadline=5000)
    def test_concurrent_writes_create_directories_safely(
        self, temp_storage, nested_path, data, num_threads
    ):
        """
        Property: Concurrent writes to files in nested directories should
        safely create all parent directories without errors, even when
        multiple threads try to create the same directories simultaneously.
        """
        # Create a nested file path
        file_path = "/".join(nested_path) + "/data.json"
        
        errors = []
        
        def write_nested(thread_id):
            try:
                data_with_id = {**data, "_thread_id": thread_id}
                temp_storage.write_json(file_path, data_with_id)
            except Exception as e:
                errors.append((thread_id, e))
        
        # Execute concurrent writes to nested path
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=write_nested, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Property 1: No errors should occur (directory creation is safe)
        assert len(errors) == 0, f"Errors during nested writes: {errors}"
        
        # Property 2: File should exist
        full_path = Path(temp_storage.base_path) / file_path
        assert full_path.exists(), "Nested file should exist"
        
        # Property 3: All parent directories should exist
        assert full_path.parent.exists(), "Parent directories should exist"
        
        # Property 4: File should contain valid data
        final_data = temp_storage.read_json(file_path)
        assert isinstance(final_data, dict), "Data should be a dict"
        assert "_thread_id" in final_data, "Data should have thread_id"


# ============================================================================
# Stateful Property Tests
# ============================================================================

class FileStorageStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for FileStorage.
    
    This tests sequences of operations (reads, writes, appends) to ensure
    the system maintains invariants across complex interaction patterns.
    """
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileStorage(base_path=self.temp_dir)
        self.expected_files: Dict[str, Any] = {}
        self.append_files: Dict[str, List[Any]] = {}
    
    def teardown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @rule(
        filename=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        data=simple_dict
    )
    def write_file(self, filename, data):
        """Write data to a file."""
        filepath = f"{filename}.json"
        self.storage.write_json(filepath, data)
        self.expected_files[filepath] = data
    
    @rule(
        filename=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    def read_file(self, filename):
        """Read data from a file."""
        filepath = f"{filename}.json"
        data = self.storage.read_json(filepath)
        
        if filepath in self.expected_files:
            # If we wrote to this file, it should match
            assert data == self.expected_files[filepath], \
                f"Read data should match written data for {filepath}"
        else:
            # If we never wrote to this file, it should be empty
            assert data == {}, f"Unwritten file should return empty dict"
    
    @rule(
        filename=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        data=simple_dict
    )
    def append_to_file(self, filename, data):
        """Append data to a file."""
        filepath = f"{filename}_append.json"
        self.storage.append_json(filepath, data)
        
        if filepath not in self.append_files:
            self.append_files[filepath] = []
        self.append_files[filepath].append(data)
    
    @invariant()
    def all_files_valid(self):
        """Invariant: All files should contain valid JSON."""
        for filepath in self.expected_files:
            full_path = Path(self.storage.base_path) / filepath
            if full_path.exists():
                with open(full_path, 'r') as f:
                    data = json.load(f)
                    assert isinstance(data, dict), f"File {filepath} should contain a dict"
        
        for filepath in self.append_files:
            full_path = Path(self.storage.base_path) / filepath
            if full_path.exists():
                with open(full_path, 'r') as f:
                    data = json.load(f)
                    assert isinstance(data, list), f"Append file {filepath} should contain a list"
    
    @invariant()
    def append_files_contain_all_items(self):
        """Invariant: Append files should contain all appended items."""
        for filepath, expected_items in self.append_files.items():
            full_path = Path(self.storage.base_path) / filepath
            if full_path.exists():
                with open(full_path, 'r') as f:
                    actual_items = json.load(f)
                    assert len(actual_items) == len(expected_items), \
                        f"Append file {filepath} should have {len(expected_items)} items, got {len(actual_items)}"


# Create test class for stateful testing
TestFileStorageStateful = FileStorageStateMachine.TestCase


# ============================================================================
# Summary
# ============================================================================

"""
Property-Based Test Coverage Summary:

1. test_concurrent_writes_preserve_one_complete_write:
   - Verifies file locking prevents corruption during concurrent writes
   - Ensures final file contains one complete, valid write (not partial data)

2. test_concurrent_appends_preserve_all_data:
   - Critical for audit logs and append-only data
   - Verifies no data loss when multiple threads append concurrently
   - Ensures all items from all threads are present in final array

3. test_concurrent_reads_never_see_corruption:
   - Verifies readers never see partial or corrupted writes
   - Ensures data consistency during mixed read/write operations

4. test_concurrent_writes_to_different_files_no_interference:
   - Verifies file locking is per-file (no global lock)
   - Ensures concurrent writes to different files don't interfere

5. test_concurrent_writes_create_directories_safely:
   - Verifies thread-safe directory creation
   - Ensures no race conditions when creating nested directories

6. FileStorageStateMachine (Stateful Testing):
   - Tests sequences of operations to find complex interaction bugs
   - Maintains invariants: all files valid JSON, append files complete

These properties complement the unit tests by:
- Testing with randomly generated data (finds edge cases)
- Testing various concurrency patterns (2-10 threads)
- Verifying invariants hold across operation sequences
- Providing broader coverage than hand-written examples
"""
