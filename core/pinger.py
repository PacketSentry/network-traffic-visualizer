import subprocess
import threading
import time
import platform
import re

class NetworkPinger:
    def __init__(self):
        self.running = False
        self.lock = threading.Lock()
        # TARGETS:
        # 1. Cloudflare (1.1.1.1)
        # 2. Google (8.8.8.8)
        # 3. Mumbai Server (Quad9 DNS - 9.9.9.9) - Guaranteed to reply
        self.targets = {
            "Cloudflare (1.1.1.1)": "1.1.1.1",
            "Google (8.8.8.8)": "8.8.8.8",
            "Mumbai Server": "9.9.9.9" 
        }
        self.pings = {name: 0.0 for name in self.targets}

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def get_pings(self):
        with self.lock:
            return self.pings.copy()

    def _ping_loop(self):
        while self.running:
            for name, ip in self.targets.items():
                if not self.running: break
                latency = self._measure_ping(ip)

                with self.lock:
                    self.pings[name] = latency
            time.sleep(1) 

    def _measure_ping(self, ip):
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            
            # Using 9.9.9.9 which is designed to reply to pings
            command = ['ping', param, '1', '-w', '1000', ip]
            
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            output = subprocess.check_output(command, startupinfo=startupinfo, text=True)
            
            match = re.search(r"time[=<](\d+[\.]?\d*)", output)
            if match:
                return float(match.group(1))
            return 0.0 
        except Exception:
            return 0.0