import unittest
from pathlib import Path
import tempfile
import time
from app.common.tor4u.appointments_db import AppointmentsDb
from datetime import datetime, timedelta
import sqlite3
import os
import gc


class TestAppointmentsDb(unittest.TestCase):
    def setUp(self):
        # Use a named temp file with delete=False to avoid Windows lock
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_file.name)
        self.temp_file.close()  # close handle so SQLite can use it
        self.db = AppointmentsDb(self.db_path)

    def tearDown(self):
        # Properly close the database and clean up
        if hasattr(self, 'db'):
            self.db.close()
            del self.db
        
        # Force garbage collection to ensure all connections are closed
        gc.collect()
        
        # Small delay to ensure Windows releases file handles
        time.sleep(0.1)
        
        # Clean up WAL and SHM files if they exist
        wal_file = Path(str(self.db_path) + '-wal')
        shm_file = Path(str(self.db_path) + '-shm')
        
        for file_path in [wal_file, shm_file, self.db_path]:
            if file_path.exists():
                try:
                    os.unlink(file_path)
                except PermissionError as e:
                    print(f"⚠️ Could not delete file {file_path}: {e}")

    def test_insert_new_record(self):
        data = {
            "apptid": "a1",
            "From_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        self.assertTrue(self.db.try_insert(data))

    def test_insert_duplicate_same_date(self):
        date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data = {"apptid": "a2", "From_date": date}
        self.assertTrue(self.db.try_insert(data))
        self.assertFalse(self.db.try_insert(data))  # No change

    def test_update_existing_record(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        later = (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M:%S")
        data1 = {"apptid": "a3", "From_date": now}
        data2 = {"apptid": "a3", "From_date": later}
        self.assertTrue(self.db.try_insert(data1))
        self.assertTrue(self.db.try_insert(data2))  # Updated
        self.assertTrue(self.db.try_insert(data1))
        self.assertFalse(self.db.try_insert(data1))

    def test_invalid_date_format(self):
        with self.assertRaises(ValueError):
            self.db.try_insert({"apptid": "bad", "From_date": "invalid"})

    def test_cleanup_old_records(self):
        old_date = (datetime.now() - timedelta(days=8)).strftime("%d/%m/%Y %H:%M:%S")
        new_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Insert old and new
        self.assertTrue(self.db.try_insert({"apptid": "old1", "From_date": old_date}))
        self.assertTrue(self.db.try_insert({"apptid": "new1", "From_date": new_date}))

        # Trigger cleanup by inserting a new record
        self.db.cleanup_old_records()

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT apptid FROM appointments").fetchall()
            apptids = {row[0] for row in rows}
            self.assertNotIn("old1", apptids)
            self.assertIn("new1", apptids)

if __name__ == "__main__":
    unittest.main()