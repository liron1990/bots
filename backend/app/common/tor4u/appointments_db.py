import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
from filelock import FileLock, Timeout


class AppointmentsDb:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.table_name = "appointments"
        self.lock_path = self.db_path.with_suffix(".lock")
        self.lock = FileLock(str(self.lock_path))
        self._init_db()

    def _init_db(self):
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        apptid TEXT PRIMARY KEY,
                        from_date TEXT,
                        staffname TEXT
                    );
                """)
                conn.commit()

    def cleanup_old_records(self):
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute("BEGIN IMMEDIATE")
                one_week_ago = datetime.now() - timedelta(days=7)
                rows = conn.execute(f"SELECT apptid, from_date FROM {self.table_name}").fetchall()
                for apptid, from_date in rows:
                    try:
                        dt = datetime.strptime(from_date, "%d/%m/%Y %H:%M:%S")
                        if dt < one_week_ago:
                            conn.execute(f"DELETE FROM {self.table_name} WHERE apptid = ?", (apptid,))
                    except ValueError:
                        continue
                conn.commit()

    def try_insert(self, data: Dict) -> bool:
        try:
            apptid = str(data["apptid"])
            from_date = data["From_date"]
            staffname = str(data.get("staffname", "").strip())
            datetime.strptime(from_date, "%d/%m/%Y %H:%M:%S")  # validate format
        except Exception as e:
            raise ValueError(f"Invalid input data: {e}")

        try:
            with self.lock:
                with sqlite3.connect(self.db_path, timeout=10) as conn:
                    conn.execute("BEGIN IMMEDIATE")

                    cur = conn.execute(f"SELECT from_date, staffname FROM {self.table_name} WHERE apptid = ?", (apptid,))
                    row = cur.fetchone()

                    if row is None:
                        conn.execute(f"""
                            INSERT INTO {self.table_name} (apptid, from_date, staffname)
                            VALUES (?, ?, ?)
                        """, (apptid, from_date, staffname))
                        conn.commit()
                        return True
                    else:
                        existing_from_date, existing_staffname = row
                        if existing_from_date != from_date or existing_staffname != staffname:
                            conn.execute(f"""
                                UPDATE {self.table_name}
                                SET from_date = ?, staffname = ?
                                WHERE apptid = ?
                            """, (from_date, staffname, apptid))
                            conn.commit()
                            return True
                        return False
        except sqlite3.Error as e:
            print("DB Error:", e)
            return False

    def close(self):
        import gc
        gc.collect()
