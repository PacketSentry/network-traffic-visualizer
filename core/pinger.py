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
        # 3. MTNL Mumbai (mtnl.net.in) - Mumbai's Main ISP Web Server
        self.targets = {
            "Cloudflare (1.1.1.1)": "1.1.1.1",
            "Google (8.8.8.8)": "8.8.8.8",
            "Mumbai Server": "mtnl.net.in" 
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
                
                # DEBUG: Print to terminal to verify it's working
                if name == "Mumbai Server":
                    print(f"[DEBUG] Ping to {name} ({ip}): {latency} ms")

                with self.lock:
                    self.pings[name] = latency
            time.sleep(1) 

    def _measure_ping(self, ip):
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            
            # Using 'ping' command which handles domains (mtnl.net.in) automatically
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
        except Exception as e:
            print(f"Ping Error: {e}")
            return 0.0