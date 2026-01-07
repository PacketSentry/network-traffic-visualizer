import sqlite3
import threading

class DatabaseManager:
    def __init__(self, db_name="traffic_history.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self._create_tables()

    def _create_tables(self):
        with self.lock:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_traffic (
                    app_name TEXT PRIMARY KEY,
                    download_bytes INTEGER,
                    upload_bytes INTEGER
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS instance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    app_name TEXT,
                    download_speed REAL,
                    upload_speed REAL,
                    src_ip TEXT,
                    dst_ip TEXT
                )
            """)
            self.conn.commit()

    def load_traffic(self):
        with self.lock:
            self.cursor.execute("SELECT * FROM app_traffic")
            rows = self.cursor.fetchall()
            return {row[0]: [row[1], row[2]] for row in rows}

    def save_traffic(self, traffic_dict):
        with self.lock:
            for app, (down, up) in traffic_dict.items():
                self.cursor.execute("""
                    INSERT OR REPLACE INTO app_traffic (app_name, download_bytes, upload_bytes)
                    VALUES (?, ?, ?)
                """, (app, down, up))
            self.conn.commit()

    def log_instances(self, instances):
        if not instances: return
        with self.lock:
            self.cursor.executemany("""
                INSERT INTO instance_logs (timestamp, app_name, download_speed, upload_speed, src_ip, dst_ip)
                VALUES (?, ?, ?, ?, ?, ?)
            """, instances)
            self.conn.commit()

    def fetch_logs(self, limit=100, app_filter=None):
        """Fetches logs, optionally filtering by app_name"""
        with self.lock:
            if app_filter:
                query = """
                    SELECT timestamp, app_name, download_speed, upload_speed, src_ip, dst_ip 
                    FROM instance_logs 
                    WHERE app_name LIKE ?
                    ORDER BY id DESC LIMIT ?
                """
                self.cursor.execute(query, (f"%{app_filter}%", limit))
            else:
                self.cursor.execute("""
                    SELECT timestamp, app_name, download_speed, upload_speed, src_ip, dst_ip 
                    FROM instance_logs 
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            return self.cursor.fetchall()

    def close(self):
        self.conn.close()