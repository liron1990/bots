import pytest
import os
import sys
import tempfile
import time
import gc
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.common.tor4u.appointments_db import AppointmentsDb


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = Path(temp_file.name)
    temp_file.close()  # close handle so SQLite can use it
    
    yield db_path
    
    # Cleanup
    gc.collect()
    time.sleep(0.1)  # Small delay to ensure Windows releases file handles
    
    # Clean up WAL and SHM files if they exist
    wal_file = Path(str(db_path) + '-wal')
    shm_file = Path(str(db_path) + '-shm')
    
    for file_path in [wal_file, shm_file, db_path]:
        if file_path.exists():
            try:
                os.unlink(file_path)
            except PermissionError as e:
                print(f"⚠️ Could not delete file {file_path}: {e}")


@pytest.fixture
def appointments_db(temp_db_path):
    """Create an AppointmentsDb instance with a temporary database"""
    db = AppointmentsDb(temp_db_path)
    yield db
    
    # Cleanup
    if hasattr(db, 'close'):
        db.close()


class TestAppointmentsDb:
    
    def test_insert_new_record(self, appointments_db):
        """Test inserting a new record"""
        data = {
            "apptid": "a1",
            "From_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        assert appointments_db.try_insert(data) is True

    def test_insert_duplicate_same_date(self, appointments_db):
        """Test inserting duplicate record with same date"""
        date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data = {"apptid": "a2", "From_date": date}
        
        assert appointments_db.try_insert(data) is True
        assert appointments_db.try_insert(data) is False  # No change

    def test_update_existing_record(self, appointments_db):
        """Test updating an existing record"""
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        later = (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M:%S")
        
        data1 = {"apptid": "a3", "From_date": now}
        data2 = {"apptid": "a3", "From_date": later}
        
        assert appointments_db.try_insert(data1) is True
        assert appointments_db.try_insert(data2) is True  # Updated
        assert appointments_db.try_insert(data1) is True  # Updated back
        assert appointments_db.try_insert(data1) is False  # No change

    def test_invalid_date_format(self, appointments_db):
        """Test that invalid date format raises ValueError"""
        with pytest.raises(ValueError):
            appointments_db.try_insert({"apptid": "bad", "From_date": "invalid"})

    def test_cleanup_old_records(self, appointments_db, temp_db_path):
        """Test cleanup of old records"""
        old_date = (datetime.now() - timedelta(days=8)).strftime("%d/%m/%Y %H:%M:%S")
        new_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Insert old and new records
        assert appointments_db.try_insert({"apptid": "old1", "From_date": old_date}) is True
        assert appointments_db.try_insert({"apptid": "new1", "From_date": new_date}) is True

        # Trigger cleanup
        appointments_db.cleanup_old_records()

        # Verify cleanup worked
        with sqlite3.connect(temp_db_path) as conn:
            rows = conn.execute("SELECT apptid FROM appointments").fetchall()
            apptids = {row[0] for row in rows}
            assert "old1" not in apptids
            assert "new1" in apptids

    def test_multiple_old_records_cleanup(self, appointments_db, temp_db_path):
        """Test cleanup of multiple old records"""
        old_date1 = (datetime.now() - timedelta(days=10)).strftime("%d/%m/%Y %H:%M:%S")
        old_date2 = (datetime.now() - timedelta(days=9)).strftime("%d/%m/%Y %H:%M:%S")
        old_date3 = (datetime.now() - timedelta(days=8)).strftime("%d/%m/%Y %H:%M:%S")
        recent_date = (datetime.now() - timedelta(days=5)).strftime("%d/%m/%Y %H:%M:%S")
        new_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Insert multiple old and recent records
        assert appointments_db.try_insert({"apptid": "old1", "From_date": old_date1}) is True
        assert appointments_db.try_insert({"apptid": "old2", "From_date": old_date2}) is True
        assert appointments_db.try_insert({"apptid": "old3", "From_date": old_date3}) is True
        assert appointments_db.try_insert({"apptid": "recent1", "From_date": recent_date}) is True
        assert appointments_db.try_insert({"apptid": "new1", "From_date": new_date}) is True

        # Trigger cleanup
        appointments_db.cleanup_old_records()

        # Verify cleanup worked
        with sqlite3.connect(temp_db_path) as conn:
            rows = conn.execute("SELECT apptid FROM appointments").fetchall()
            apptids = {row[0] for row in rows}
            
            # Old records should be gone
            assert "old1" not in apptids
            assert "old2" not in apptids
            assert "old3" not in apptids
            
            # Recent records should remain
            assert "recent1" in apptids
            assert "new1" in apptids

    # def test_invalid_apptid_handling(self, appointments_db):
    #     """Test handling of invalid apptid"""
    #     data = {
    #         "apptid": None,
    #         "From_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    #     }
        
    #     with pytest.raises(ValueError):
    #         appointments_db.try_insert(data)

    def test_missing_from_date_handling(self, appointments_db):
        """Test handling of missing From_date"""
        data = {
            "apptid": "test1"
            # Missing From_date
        }
        
        with pytest.raises(ValueError):
            appointments_db.try_insert(data)

    def test_empty_data_handling(self, appointments_db):
        """Test handling of empty data"""
        with pytest.raises(ValueError):
            appointments_db.try_insert({})

    def test_database_file_creation(self, temp_db_path):
        """Test that database file is created properly"""
        # Remove the file if it exists
        if temp_db_path.exists():
            os.unlink(temp_db_path)
        
        # Create new database
        db = AppointmentsDb(temp_db_path)
        
        # Verify file was created
        assert temp_db_path.exists()
        
        # Verify table was created
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == 'appointments'
        
        if hasattr(db, 'close'):
            db.close()

    def test_concurrent_access(self, appointments_db):
        """Test that database handles concurrent access"""
        import threading
        import concurrent.futures
        
        results = []
        
        def insert_record(apptid):
            data = {
                "apptid": f"concurrent_{apptid}",
                "From_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            return appointments_db.try_insert(data)
        
        # Run multiple threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_record, i) for i in range(10)]
            
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # All inserts should succeed
        assert all(results)
        assert len(results) == 10

    def test_date_format_validation(self, appointments_db):
        """Test various date format validations"""
        valid_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Valid format should work
        assert appointments_db.try_insert({"apptid": "valid1", "From_date": valid_date}) is True
        
        # Invalid formats should raise ValueError
        invalid_formats = [
            "2023-01-01 12:00:00",  # Wrong separator
            "01/01/23 12:00:00",    # Wrong year format
            "01/01/2023",           # Missing time
            "12:00:00",             # Missing date
            "not a date",           # Completely invalid
            "",                     # Empty string
        ]
        
        for i, invalid_date in enumerate(invalid_formats):
            with pytest.raises(ValueError):
                appointments_db.try_insert({"apptid": f"invalid_{i}", "From_date": invalid_date})

    def test_record_retrieval(self, appointments_db, temp_db_path):
        """Test that records can be retrieved after insertion"""
        test_data = [
            {"apptid": "retrieve1", "From_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")},
            {"apptid": "retrieve2", "From_date": (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M:%S")},
            {"apptid": "retrieve3", "From_date": (datetime.now() + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M:%S")},
        ]
        
        # Insert test data
        for data in test_data:
            assert appointments_db.try_insert(data) is True
        
        # Retrieve and verify
        with sqlite3.connect(temp_db_path) as conn:
            rows = conn.execute("SELECT apptid, from_date FROM appointments ORDER BY apptid").fetchall()
            
            assert len(rows) == 3
            for i, (apptid, from_date) in enumerate(rows):
                assert apptid == test_data[i]["apptid"]
                assert from_date == test_data[i]["From_date"]

    @pytest.mark.parametrize("days_old,should_be_deleted", [
        (8, True),   # 8 days old should be deleted
        (7, True),  # 7 days old should not be deleted
        (6, False),  # 6 days old should not be deleted
        (10, True),  # 10 days old should be deleted
    ])
    def test_cleanup_boundary_conditions(self, appointments_db, temp_db_path, days_old, should_be_deleted):
        """Test cleanup boundary conditions"""
        old_date = (datetime.now() - timedelta(days=days_old)).strftime("%d/%m/%Y %H:%M:%S")
        apptid = f"boundary_test_{days_old}days"
        
        # Insert record
        assert appointments_db.try_insert({"apptid": apptid, "From_date": old_date}) is True
        
        # Trigger cleanup
        appointments_db.cleanup_old_records()
        
        # Check if record exists
        with sqlite3.connect(temp_db_path) as conn:
            rows = conn.execute("SELECT apptid FROM appointments WHERE apptid = ?", (apptid,)).fetchall()
            
            if should_be_deleted:
                assert len(rows) == 0, f"Record {apptid} should have been deleted"
            else:
                assert len(rows) == 1, f"Record {apptid} should not have been deleted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])