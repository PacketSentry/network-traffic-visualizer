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
        self.traffic_data = {} # Key: (app_name, src_ip, dst_ip), Value: [down, up]
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
                direction = "down"
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst

                # A. Handle TCP/UDP
                if TCP in pkt or UDP in pkt:
                    if TCP in pkt: layer = TCP
                    else: layer = UDP
                        
                    sport = pkt[layer].sport
                    dport = pkt[layer].dport
                    
                    app_by_dst = self._get_process_by_port(dport)
                    
                    if app_by_dst != "Unknown":
                        app_name = app_by_dst
                        direction = "down"
                    else:
                        app_by_src = self._get_process_by_port(sport)
                        if app_by_src != "Unknown":
                            app_name = app_by_src
                            direction = "up"
                        else:
                            app_name = "System (Unknown)"
                            direction = "down"

                elif pkt[IP].proto == 1:
                    app_name = "System (ICMP/Ping)"
                    direction = "down" 
                else:
                    proto_id = pkt[IP].proto
                    app_name = f"System (Proto {proto_id})"
                    direction = "down"

                # Update Data with IPs
                key = (app_name, src_ip, dst_ip)
                
                with self.lock:
                    if key not in self.traffic_data:
                        self.traffic_data[key] = [0, 0]
                    
                    if direction == "down":
                        self.traffic_data[key][0] += size
                    else:
                        self.traffic_data[key][1] += size

            except Exception:
                pass
        
        elif "ARP" in pkt:
            # ARP doesn't have IP layers in the same way, skip or log simply
            pass

    def _get_process_by_port(self, port):
        now = time.time()
        if port in self.port_cache:
            app, ts = self.port_cache[port]
            if now - ts < self.cache_timeout:
                return app

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