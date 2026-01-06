import threading
import time
import psutil
# CHANGED: Added UDP to imports
from scapy.all import sniff, TCP, IP, UDP
from core.platform import IS_WINDOWS

if IS_WINDOWS:
    from scapy.all import conf
    conf.use_pcap = True

class PacketSniffer:
    def __init__(self):
        self.running = False
        self.traffic_data = {}
        self.lock = threading.Lock()
        self.port_cache = {}
        self.cache_timeout = 10

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._sniff_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False

    def get_traffic_data(self):
        with self.lock:
            data = self.traffic_data.copy()
            self.traffic_data.clear()
        return data

    def _sniff_loop(self):
        while self.running:
            try:
                # We still filter for IP, but the callback handles TCP vs UDP
                sniff(prn=self._on_packet, store=False, timeout=1)
            except Exception as e:
                print(f"Sniff Error: {e}")
                time.sleep(1)

    def _on_packet(self, pkt):
        if not self.running:
            return

        if IP in pkt:
            try:
                # CHANGED: Check for BOTH TCP and UDP
                if TCP in pkt:
                    layer = TCP
                elif UDP in pkt:
                    layer = UDP
                else:
                    return # Skip if it's not TCP or UDP

                size = len(pkt)
                sport = pkt[layer].sport
                dport = pkt[layer].dport
                
                # Logic to determine direction (same as before)
                direction = "up"
                app_port = sport 
                
                if self._is_local_port(dport):
                    direction = "down"
                    app_port = dport
                
                app_name = self._get_process_by_port(app_port)

                with self.lock:
                    if app_name not in self.traffic_data:
                        self.traffic_data[app_name] = [0, 0]
                    
                    if direction == "down":
                        self.traffic_data[app_name][0] += size
                    else:
                        self.traffic_data[app_name][1] += size

            except Exception:
                pass

    def _is_local_port(self, port):
        return True

    def _get_process_by_port(self, port):
        now = time.time()
        if port in self.port_cache:
            app, ts = self.port_cache[port]
            if now - ts < self.cache_timeout:
                return app

        # Try to resolve port
        try:
            for c in psutil.net_connections(kind="inet"):
                if c.laddr.port == port:
                    try:
                        p = psutil.Process(c.pid)
                        name = p.name()
                        self.port_cache[port] = (name, now)
                        return name
                    except:
                        pass
        except:
            pass
        
        return "Unknown"