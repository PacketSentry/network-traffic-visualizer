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
        # 1. Cloudflare (Anycast - connects to nearest city, likely Mumbai/Delhi)
        # 2. Google (Anycast)
        # 3. Mumbai Data Center (Linode Mumbai) - Acts as a proxy for CS2 Mumbai latency
        self.targets = {
            "Cloudflare (1.1.1.1)": "1.1.1.1",
            "Google (8.8.8.8)": "8.8.8.8",
            "CS2 (Mumbai Proxy)": "139.162.200.1" 
        }
        # Store latest ping results
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
            time.sleep(1) # Wait 1 second before next batch

    def _measure_ping(self, ip):
        """Runs the system ping command and parses the time."""
        try:
            # -n 1 (Windows) or -c 1 (Linux) -> Send 1 packet
            # -w 1000 -> Timeout 1000ms
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            
            # Use shell=True to hide window properly on some Windows versions
            # But normally specific startupinfo flags are cleaner (used below)
            command = ['ping', param, '1', '-w', '1000', ip]
            
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            output = subprocess.check_output(command, startupinfo=startupinfo, text=True)
            
            # Extract time=XXms
            match = re.search(r"time[=<](\d+[\.]?\d*)", output)
            if match:
                return float(match.group(1))
            return 0.0 # Timeout
        except Exception:
            return 0.0 # Error/Offline