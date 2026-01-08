import threading
import requests
import json
import time

# --- CONFIGURATION ---
SERVER_URL = "http://127.0.0.1:5000/api/upload"
# REPLACE THIS WITH THE KEY FROM YOUR DASHBOARD AFTER REGISTERING
API_KEY = "REPLACE_WITH_YOUR_API_KEY" 

class CloudClient:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()
        self.running = True
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def add_logs(self, log_entries):
        """Add logs to the upload queue"""
        if not API_KEY or "REPLACE" in API_KEY:
            return # Not configured yet

        with self.lock:
            self.queue.extend(log_entries)

    def _worker_loop(self):
        while self.running:
            time.sleep(5) # Upload every 5 seconds
            
            payload = []
            with self.lock:
                if not self.queue:
                    continue
                # Take chunk of logs
                payload = self.queue[:50]
                del self.queue[:50]

            if payload:
                try:
                    requests.post(
                        SERVER_URL, 
                        json={"api_key": API_KEY, "logs": payload},
                        timeout=3
                    )
                    print(f"Uploaded {len(payload)} logs to cloud.")
                except Exception as e:
                    print(f"Cloud Upload Failed: {e}")
                    # Optionally put back in queue, but discarding prevents memory leaks for now