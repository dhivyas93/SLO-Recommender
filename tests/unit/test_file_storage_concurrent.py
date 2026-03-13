"""
Unit tests for concurrent read/write operations in FileStorage.

Tests verify that file locking prevents race conditions and maintains
data integrity during concurrent access from multiple threads.

**Validates: Requirements 8.1** (file-based storage with thread safety)
"""

import json
import pytest
import threading
import time
from pathlib import Path
from typing import List
import tempfile
import shutil

from src.storage.file_storage import FileStorage


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    storage = FileStorage(base_path=temp_dir)
    yield storage
    # Cleanup
    shutil.rmtree(temp_dir)


class TestConcurrentReads:
    """Test concurrent read operations."""
    
    def test_multiple_concurrent_readers(self, temp_storage):
        """
        Test that multiple threads can read the same file simultaneously.
        
        Verifies that concurrent reads don't interfere with each other
        and all threads receive the same correct data.
        """
        # Setup: Write initial data
        test_data = {"value": 42, "name": "test", "items": [1, 2, 3]}
        temp_storage.write_json("test_file.json", test_data)
        
        results = []
        errors = []
        num_readers = 10
        
        def read_file():
            try:
                data = temp_storage.read_json("test_file.json")
                results.append(data)
            except Exception as e:
                errors.append(e)
        
        # Create and start multiple reader threads
        threads = []
        for _ in range(num_readers):
            thread = threading.Thread(target=read_file)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred during concurrent reads: {errors}"
        
        # Verify all readers got the correct data
        assert len(results) == num_readers
        for result in results:
            assert result == test_data
    
    def test_concurrent_reads_with_large_file(self, temp_storage):
        """
        Test concurrent reads with a larger JSON file.
        
        Ensures file locking works correctly even with larger data.
        """
        # Create a larger dataset
        large_data = {
            "services": [
                {"id": f"service-{i}", "metrics": {"latency": i * 10}}
                for i in range(100)
            ]
        }
        temp_storage.write_json("large_file.json", large_data)
        
        results = []
        num_readers = 20
        
        def read_file():
            data = temp_storage.read_json("large_file.json")
            results.append(len(data["services"]))
        
        threads = []
        for _ in range(num_readers):
            thread = threading.Thread(target=read_file)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All readers should see 100 services
        assert len(results) == num_readers
        assert all(count == 100 for count in results)


class TestConcurrentWrites:
    """Test concurrent write operations."""
    
    def test_multiple_concurrent_writers(self, temp_storage):
        """
        Test that multiple threads writing to the same file maintain data integrity.
        
        Verifies that file locking prevents race conditions and the final
        state reflects one of the writes (not corrupted data).
        """
        num_writers = 10
        errors = []
        
        def write_file(thread_id):
            try:
                data = {"thread_id": thread_id, "timestamp": time.time()}
                temp_storage.write_json("concurrent_write.json", data)
            except Exception as e:
                errors.append(e)
        
        # Create and start multiple writer threads
        threads = []
        for i in range(num_writers):
            thread = threading.Thread(target=write_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred during concurrent writes: {errors}"
        
        # Read the final result
        final_data = temp_storage.read_json("concurrent_write.json")
        
        # Verify the file is valid JSON and contains expected structure
        assert "thread_id" in final_data
        assert "timestamp" in final_data
        assert 0 <= final_data["thread_id"] < num_writers
        
        # Verify the file is not corrupted (can be parsed as valid JSON)
        file_path = Path(temp_storage.base_path) / "concurrent_write.json"
        with open(file_path, 'r') as f:
            parsed = json.load(f)
            assert parsed == final_data
    
    def test_concurrent_writes_to_different_files(self, temp_storage):
        """
        Test that concurrent writes to different files don't interfere.
        
        Each thread writes to its own file, all should succeed.
        """
        num_writers = 15
        errors = []
        
        def write_file(thread_id):
            try:
                data = {"thread_id": thread_id, "value": thread_id * 100}
                temp_storage.write_json(f"file_{thread_id}.json", data)
            except Exception as e:
                errors.append((thread_id, e))
        
        threads = []
        for i in range(num_writers):
            thread = threading.Thread(target=write_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all files were created correctly
        for i in range(num_writers):
            data = temp_storage.read_json(f"file_{i}.json")
            assert data["thread_id"] == i
            assert data["value"] == i * 100
    
    def test_concurrent_writes_sequential_consistency(self, temp_storage):
        """
        Test that concurrent writes maintain sequential consistency.
        
        Each write should be atomic - the file should never contain
        partial or corrupted data.
        """
        num_writers = 20
        write_order = []
        lock = threading.Lock()
        
        def write_file(thread_id):
            data = {
                "thread_id": thread_id,
                "data": [i for i in range(thread_id * 10, (thread_id + 1) * 10)]
            }
            temp_storage.write_json("sequential.json", data)
            with lock:
                write_order.append(thread_id)
        
        threads = []
        for i in range(num_writers):
            thread = threading.Thread(target=write_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify final data is valid and complete
        final_data = temp_storage.read_json("sequential.json")
        assert "thread_id" in final_data
        assert "data" in final_data
        assert len(final_data["data"]) == 10
        
        # Verify data integrity - the array should be sequential
        thread_id = final_data["thread_id"]
        expected_data = list(range(thread_id * 10, (thread_id + 1) * 10))
        assert final_data["data"] == expected_data


class TestMixedReadWrite:
    """Test mixed concurrent read and write operations."""
    
    def test_concurrent_readers_and_writers(self, temp_storage):
        """
        Test mixed read/write operations happening concurrently.
        
        Verifies that readers always get valid data (either old or new)
        and never see corrupted/partial writes.
        """
        # Setup initial data
        initial_data = {"counter": 0, "status": "initial"}
        temp_storage.write_json("mixed.json", initial_data)
        
        read_results = []
        write_count = [0]
        errors = []
        lock = threading.Lock()
        
        def reader():
            try:
                for _ in range(5):
                    data = temp_storage.read_json("mixed.json")
                    # Verify data is always valid
                    assert "counter" in data
                    assert "status" in data
                    with lock:
                        read_results.append(data)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(("reader", e))
        
        def writer(writer_id):
            try:
                for i in range(5):
                    data = {"counter": writer_id * 10 + i, "status": f"writer-{writer_id}"}
                    temp_storage.write_json("mixed.json", data)
                    with lock:
                        write_count[0] += 1
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(("writer", writer_id, e))
        
        # Create mixed threads
        threads = []
        
        # Start 5 reader threads
        for _ in range(5):
            thread = threading.Thread(target=reader)
            threads.append(thread)
            thread.start()
        
        # Start 3 writer threads
        for i in range(3):
            thread = threading.Thread(target=writer, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all reads returned valid data
        assert len(read_results) == 25  # 5 readers * 5 reads each
        for data in read_results:
            assert isinstance(data, dict)
            assert "counter" in data
            assert "status" in data
        
        # Verify writes completed
        assert write_count[0] == 15  # 3 writers * 5 writes each
    
    def test_read_during_write_sees_consistent_data(self, temp_storage):
        """
        Test that reads during writes never see partial/corrupted data.
        
        All reads should see either the complete old data or complete new data,
        never a mix or corrupted state.
        """
        # Write initial data
        temp_storage.write_json("consistency.json", {"version": 0, "data": [0]})
        
        read_results = []
        errors = []
        
        def continuous_reader():
            try:
                for _ in range(50):
                    data = temp_storage.read_json("consistency.json")
                    # Verify data structure is always valid
                    assert "version" in data
                    assert "data" in data
                    assert isinstance(data["data"], list)
                    # Verify data consistency: data array should match version
                    assert len(data["data"]) == data["version"] + 1
                    read_results.append(data["version"])
            except Exception as e:
                errors.append(e)
        
        def continuous_writer():
            try:
                for version in range(1, 11):
                    data = {"version": version, "data": list(range(version + 1))}
                    temp_storage.write_json("consistency.json", data)
                    time.sleep(0.002)
            except Exception as e:
                errors.append(e)
        
        # Start reader and writer threads
        reader_thread = threading.Thread(target=continuous_reader)
        writer_thread = threading.Thread(target=continuous_writer)
        
        reader_thread.start()
        writer_thread.start()
        
        reader_thread.join()
        writer_thread.join()
        
        # Verify no errors (this is the key test - no corruption)
        assert len(errors) == 0, f"Data consistency errors: {errors}"
        
        # Verify we got reads
        assert len(read_results) == 50


class TestConcurrentAppends:
    """Test concurrent append operations."""
    
    def test_concurrent_appends_maintain_all_data(self, temp_storage):
        """
        Test that concurrent appends to the same file maintain all data.
        
        All appended items should be present in the final array,
        no data should be lost due to race conditions.
        """
        num_appenders = 10
        appends_per_thread = 5
        errors = []
        
        def append_data(thread_id):
            try:
                for i in range(appends_per_thread):
                    data = {"thread_id": thread_id, "item": i}
                    temp_storage.append_json("appends.json", data)
            except Exception as e:
                errors.append((thread_id, e))
        
        threads = []
        for i in range(num_appenders):
            thread = threading.Thread(target=append_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors during appends: {errors}"
        
        # Read final data
        file_path = Path(temp_storage.base_path) / "appends.json"
        with open(file_path, 'r') as f:
            final_data = json.load(f)
        
        # Verify all items are present
        assert len(final_data) == num_appenders * appends_per_thread
        
        # Verify each thread's items are present
        for thread_id in range(num_appenders):
            thread_items = [item for item in final_data if item["thread_id"] == thread_id]
            assert len(thread_items) == appends_per_thread
            
            # Verify all items for this thread are present
            item_numbers = sorted([item["item"] for item in thread_items])
            assert item_numbers == list(range(appends_per_thread))
    
    def test_concurrent_appends_preserve_order_per_thread(self, temp_storage):
        """
        Test that appends from the same thread maintain their order.
        
        While overall order may vary, items from a single thread
        should appear in the order they were appended.
        """
        num_threads = 5
        items_per_thread = 10
        
        def append_sequential(thread_id):
            for i in range(items_per_thread):
                data = {"thread_id": thread_id, "sequence": i, "timestamp": time.time()}
                temp_storage.append_json("ordered_appends.json", data)
                time.sleep(0.001)  # Small delay to ensure ordering
        
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=append_sequential, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Read final data
        file_path = Path(temp_storage.base_path) / "ordered_appends.json"
        with open(file_path, 'r') as f:
            final_data = json.load(f)
        
        # Verify total count
        assert len(final_data) == num_threads * items_per_thread
        
        # Verify each thread's items are in order
        for thread_id in range(num_threads):
            thread_items = [item for item in final_data if item["thread_id"] == thread_id]
            sequences = [item["sequence"] for item in thread_items]
            assert sequences == list(range(items_per_thread))


class TestDataIntegrity:
    """Test data integrity under concurrent access."""
    
    def test_no_data_corruption_under_load(self, temp_storage):
        """
        Stress test: verify no data corruption under heavy concurrent load.
        
        Multiple threads performing various operations simultaneously.
        All data should remain valid and uncorrupted.
        """
        num_operations = 100
        errors = []
        
        def mixed_operations(op_id):
            try:
                # Write
                temp_storage.write_json(f"stress_{op_id}.json", {"id": op_id, "value": op_id * 2})
                
                # Read
                data = temp_storage.read_json(f"stress_{op_id}.json")
                assert data["id"] == op_id
                assert data["value"] == op_id * 2
                
                # Append
                temp_storage.append_json("stress_appends.json", {"op_id": op_id})
                
                # Read shared file
                temp_storage.read_json("stress_appends.json")
                
            except Exception as e:
                errors.append((op_id, e))
        
        threads = []
        for i in range(num_operations):
            thread = threading.Thread(target=mixed_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors under load: {errors}"
        
        # Verify all individual files
        for i in range(num_operations):
            data = temp_storage.read_json(f"stress_{i}.json")
            assert data["id"] == i
            assert data["value"] == i * 2
        
        # Verify append file
        file_path = Path(temp_storage.base_path) / "stress_appends.json"
        with open(file_path, 'r') as f:
            appends = json.load(f)
        assert len(appends) == num_operations
    
    def test_file_locking_prevents_corruption_not_race_conditions(self, temp_storage):
        """
        Test that file locking prevents file corruption but not logical race conditions.
        
        NOTE: The current FileStorage implementation locks individual read/write operations,
        which prevents file corruption (partial writes, invalid JSON). However, it does NOT
        provide atomicity for read-modify-write sequences. This is by design for the POC.
        
        This test verifies that:
        1. No file corruption occurs (all reads return valid JSON)
        2. No errors occur during concurrent operations
        3. The file remains in a valid state
        
        For atomic read-modify-write operations, applications should implement
        higher-level locking or use a proper database.
        """
        # Initialize counter
        temp_storage.write_json("counter.json", {"count": 0})
        
        num_threads = 10
        increments_per_thread = 5
        errors = []
        successful_reads = [0]
        lock = threading.Lock()
        
        def increment_counter(thread_id):
            try:
                for _ in range(increments_per_thread):
                    # Read-modify-write operation
                    data = temp_storage.read_json("counter.json")
                    # Verify data is valid (no corruption)
                    assert "count" in data
                    assert isinstance(data["count"], int)
                    
                    data["count"] += 1
                    temp_storage.write_json("counter.json", data)
                    
                    with lock:
                        successful_reads[0] += 1
            except Exception as e:
                errors.append((thread_id, e))
        
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=increment_counter, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors (no corruption)
        assert len(errors) == 0, f"Errors during increments: {errors}"
        
        # Verify all operations completed
        assert successful_reads[0] == num_threads * increments_per_thread
        
        # Read final count
        final_data = temp_storage.read_json("counter.json")
        
        # Verify the file is valid and contains a count
        assert "count" in final_data
        assert isinstance(final_data["count"], int)
        assert final_data["count"] > 0
        
        # The count may be less than expected due to race conditions,
        # but the file should never be corrupted
        expected_count = num_threads * increments_per_thread
        assert final_data["count"] <= expected_count, \
            f"Count cannot exceed maximum: {final_data['count']} > {expected_count}"
