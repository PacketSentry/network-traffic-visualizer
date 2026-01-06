from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window

# Import your backend logic
from core.packet_sniffer import PacketSniffer
from core.aggregator import TrafficAggregator

# Import your UI widgets (Essential so Kivy finds them)
from ui.widgets import TrafficGraph, AppDashboard

class NetworkApp(App):
    def build(self):
        # Set a reasonable window size
        Window.size = (900, 700)
        
        # Load the layout
        return Builder.load_file("ui/dashboard.kv")

    def on_start(self):
        # 1. Start the Backend Sniffer
        self.sniffer = PacketSniffer()
        self.sniffer.start()

        # 2. Start the Aggregator (The Math Guy)
        self.aggregator = TrafficAggregator()

        # 3. Schedule UI updates (Every 1 second)
        Clock.schedule_interval(self.update_ui, 1.0)

    def update_ui(self, dt):
        # A. Get fresh data from the sniffer
        # (This dictionary looks like: {'chrome.exe': (1024, 2048), ...})
        traffic_data = self.sniffer.get_traffic_data()
        
        # B. Calculate speeds (Kbps)
        rates = self.aggregator.calculate_rates(traffic_data)
        
        # C. Calculate Total Download Speed for the Graph
        total_download = sum(down for down, up in rates.values())
        
        # --- THE FIX IS HERE ---
        # Old Code: self.root.get_screen("main").ids... (CRASHED)
        # New Code: self.root.ids... (WORKS)
        
        # Update the Graph
        if "main_graph" in self.root.ids:
            self.root.ids.main_graph.update_graph(total_download)

        # Update the App List
        if "dashboard" in self.root.ids:
            self.root.ids.dashboard.update_apps(rates)

    def on_stop(self):
        # Clean up threads when you close the window
        if hasattr(self, 'sniffer'):
            self.sniffer.stop()

if __name__ == "__main__":
    NetworkApp().run()