import threading
import time
import psutil
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
                sniff(prn=self._on_packet, store=False, timeout=1)
            except Exception as e:
                print(f"Sniff Error: {e}")
                time.sleep(1)

    def _on_packet(self, pkt):
        if not self.running:
            return
        
        if IP in pkt:
            try:
                size = len(pkt)
                app_name = "System (Unknown)"
                direction = "down" # Default assumption

                # A. Handle TCP/UDP
                if TCP in pkt or UDP in pkt:
                    if TCP in pkt:
                        layer = TCP
                    else:
                        layer = UDP
                        
                    sport = pkt[layer].sport
                    dport = pkt[layer].dport
                    
                    # LOGIC FIX: Determine direction by checking which port is local
                    
                    # 1. Check if DESTINATION port belongs to a local app (Download)
                    app_by_dst = self._get_process_by_port(dport)
                    
                    if app_by_dst != "Unknown":
                        app_name = app_by_dst
                        direction = "down"
                    else:
                        # 2. Check if SOURCE port belongs to a local app (Upload)
                        app_by_src = self._get_process_by_port(sport)
                        if app_by_src != "Unknown":
                            app_name = app_by_src
                            direction = "up"
                        else:
                            # 3. Neither port matches a known app
                            app_name = "System (Unknown)"
                            direction = "down"

                # B. Handle ICMP (Ping)
                elif pkt[IP].proto == 1:
                    app_name = "System (ICMP/Ping)"
                    direction = "down" 

                # C. Handle Other Protocols
                else:
                    proto_id = pkt[IP].proto
                    app_name = f"System (Proto {proto_id})"
                    direction = "down"

                # Save Data
                with self.lock:
                    if app_name not in self.traffic_data:
                        self.traffic_data[app_name] = [0, 0]
                    
                    if direction == "down":
                        self.traffic_data[app_name][0] += size
                    else:
                        self.traffic_data[app_name][1] += size

            except Exception:
                pass
        
        elif "ARP" in pkt:
            with self.lock:
                name = "System (ARP)"
                if name not in self.traffic_data:
                    self.traffic_data[name] = [0, 0]
                self.traffic_data[name][0] += len(pkt)

    def _get_process_by_port(self, port):
        now = time.time()
        # 1. Check Cache
        if port in self.port_cache:
            app, ts = self.port_cache[port]
            if now - ts < self.cache_timeout:
                return app

        # 2. Resolve Port (Expensive)
        try:
            # We scan connections to find which process owns this port
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