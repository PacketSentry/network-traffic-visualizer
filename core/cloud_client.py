import threading, requests, time
from core.system_control import kill_process_by_name

BASE_URL = "http://127.0.0.1:5000/api"

class CloudClient:
    def __init__(self):
        self.queue = []
        self.latest_status = []
        self.lock = threading.Lock()
        self.running = True
        self.token = None
        threading.Thread(target=self._worker, daemon=True).start()

    def login(self, username, password):
        try:
            r = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
            if r.status_code == 200: self.token = r.json().get("access_token"); return True
        except: pass
        return False

    def update_status(self, rates):
        """Prepares live status list: [{'name': 'Chrome', 'down': 50.0, 'up': 2.0}, ...]"""
        if not self.token: return
        status = []
        for app, (down, up) in rates.items():
            if down > 0.1 or up > 0.1: status.append({"name": app, "down": down, "up": up})
        with self.lock: self.latest_status = status

    def add_logs(self, logs):
        if self.token:
            with self.lock: self.queue.extend(logs)

    def _worker(self):
        while self.running:
            time.sleep(2)
            if not self.token: continue
            
            with self.lock:
                logs_chunk = self.queue[:50]
                del self.queue[:50]
                current_status = self.latest_status

            try:
                r = requests.post(
                    f"{BASE_URL}/sync",
                    json={"logs": logs_chunk, "status": current_status},
                    headers={"Authorization": f"Bearer {self.token}"}, timeout=3
                )
                # Execute Commands (e.g., Kill App)
                if r.status_code == 200:
                    for cmd in r.json().get("commands", []):
                        if cmd['action'] == 'kill': kill_process_by_name(cmd['target'])
            except: pass