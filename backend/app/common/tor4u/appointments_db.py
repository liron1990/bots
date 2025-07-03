import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict

class AppointmentsDb:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.table_name = "appointments"
        self._init_db()

    def _init_db(self):
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            # Remove WAL mode for testing to avoid additional files
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    apptid TEXT PRIMARY KEY,
                    from_date TEXT
                );
            """)
            conn.commit()

    def cleanup_old_records(self):
        with sqlite3.connect(self.db_path, timeout=10) as conn:
            conn.execute("BEGIN IMMEDIATE")
            one_week_ago = datetime.now() - timedelta(days=7)
            # Fetch all to avoid date string parsing in SQL
            rows = conn.execute(f"SELECT apptid, from_date FROM {self.table_name}").fetchall()
            for apptid, from_date in rows:
                try:
                    dt = datetime.strptime(from_date, "%d/%m/%Y %H:%M:%S")
                    if dt < one_week_ago:
                        conn.execute(f"DELETE FROM {self.table_name} WHERE apptid = ?", (apptid,))
                except ValueError:
                    continue  # skip invalid dates silently
            conn.commit()

    def try_insert(self, data: Dict) -> bool:
        try:
            apptid = str(data["apptid"])
            from_date = data["From_date"]
            datetime.strptime(from_date, "%d/%m/%Y %H:%M:%S")  # validate format
        except Exception as e:
            raise ValueError(f"Invalid input data: {e}")

        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute("BEGIN IMMEDIATE")

                cur = conn.execute(f"SELECT from_date FROM {self.table_name} WHERE apptid = ?", (apptid,))
                row = cur.fetchone()

                if row is None:
                    conn.execute(f"""
                        INSERT INTO {self.table_name} (apptid, from_date)
                        VALUES (?, ?)
                    """, (apptid, from_date))
                    conn.commit()
                    return True
                elif row[0] == from_date:
                    return False
                else:
                    conn.execute(f"""
                        UPDATE {self.table_name}
                        SET from_date = ?
                        WHERE apptid = ?
                    """, (from_date, apptid))
                    conn.commit()
                    return True

        except sqlite3.Error as e:
            print("DB Error:", e)
            return False

    def close(self):
        """Explicitly close any remaining connections"""
        # Force garbage collection to close any lingering connections
        import gc
        gc.collect()