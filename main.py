import psutil
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window

from core.packet_sniffer import PacketSniffer
from core.aggregator import TrafficAggregator
from core.pinger import NetworkPinger  
from ui.widgets import TrafficGraph, AppDashboard, LogViewer, PingGraph, LoginPopup

class NetworkApp(App):
    def build(self):
        Window.size = (900, 700)
        return Builder.load_file("ui/dashboard.kv")

    def on_start(self):
        # 1. Start Sniffer
        self.sniffer = PacketSniffer()
        self.sniffer.start()

        # 2. Start Aggregator
        self.aggregator = TrafficAggregator()
        
        # 3. Start Pinger 
        self.pinger = NetworkPinger()
        self.pinger.start()

        # 4. Schedule Updates
        Clock.schedule_interval(self.update_ui, 1.0)
        Clock.schedule_interval(self.save_database, 5.0)

        # --- NEW: Initialize Hardware Counter ---
        self.last_net_io = psutil.net_io_counters()

    def update_ui(self, dt):
        # --- Update Traffic Tab ---
        traffic_data = self.sniffer.get_traffic_data()
        rates = self.aggregator.calculate_rates(traffic_data)
        
        # --- NEW: Hybrid Speed Fix (Accurate Hardware Stats) ---
        current_net_io = psutil.net_io_counters()
        
        # Calculate bytes since last second
        bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        
        # Convert to KB/s
        download_kb = bytes_recv / 1024
        upload_kb = bytes_sent / 1024
        
        # Save for next loop
        self.last_net_io = current_net_io

        # Update the Main Graph with ACCURATE numbers
        if "main_graph" in self.root.ids:
            self.root.ids.main_graph.update_graph(download_kb, upload_kb)
        # -------------------------------------------------------

        if "dashboard" in self.root.ids:
            # Keep using Sniffer data for the App List (Details)
            self.root.ids.dashboard.update_apps(rates)
            
        # --- Update Latency Tab ---
        if "ping_graph" in self.root.ids:
            pings = self.pinger.get_pings()
            self.root.ids.ping_graph.update_graph(
                pings.get("Cloudflare (1.1.1.1)", 0),
                pings.get("Google (8.8.8.8)", 0)
            )

    def save_database(self, dt):
        if hasattr(self, 'aggregator'):
            self.aggregator.save_data()

    def open_db_view(self):
        """Opens the Log Viewer Popup"""
        viewer = LogViewer(self.aggregator)
        viewer.open()

    # --- LOGIN LOGIC ---
    def open_login_view(self):
        # If already logged in, this button acts as Logout
        if self.aggregator.cloud.token:
            self.aggregator.cloud.logout()
            self.root.ids.login_btn.text = "Cloud Login"
            return

        popup = LoginPopup(self.perform_login)
        popup.open()

    def perform_login(self, username, password, popup_instance):
        success = self.aggregator.cloud.login(username, password)
        if success:
            popup_instance.dismiss()
            self.root.ids.login_btn.text = f"Logout ({username})"
        else:
            popup_instance.show_error("Invalid Credentials or Connection Failed")

    def on_stop(self):
        if hasattr(self, 'sniffer'): self.sniffer.stop()
        if hasattr(self, 'aggregator'): self.aggregator.save_data()
        if hasattr(self, 'pinger'): self.pinger.stop() 

if __name__ == "__main__":
    NetworkApp().run()