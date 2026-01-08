import time
from core.database import DatabaseManager
from core.cloud_client import CloudClient # <--- IMPORT THIS

class TrafficAggregator:
    def __init__(self):
        self.last_check_time = time.time()
        self.db = DatabaseManager()
        self.global_totals = self.db.load_traffic()
        
        # Initialize Cloud Client
        self.cloud = CloudClient() # <--- INITIALIZE

    def calculate_rates(self, fresh_traffic_data):
        now = time.time()
        elapsed = now - self.last_check_time
        if elapsed < 0.1: elapsed = 0.1
        self.last_check_time = now
        
        current_rates_ui = {app: [0.0, 0.0] for app in self.global_totals.keys()}
        log_entries = []
        
        for (app_name, src_ip, dst_ip), (new_down, new_up) in fresh_traffic_data.items():
            if app_name not in self.global_totals:
                self.global_totals[app_name] = [0, 0]
                if app_name not in current_rates_ui:
                    current_rates_ui[app_name] = [0.0, 0.0]
            
            self.global_totals[app_name][0] += new_down
            self.global_totals[app_name][1] += new_up
            
            down_speed = (new_down / 1024) / elapsed
            up_speed = (new_up / 1024) / elapsed
            
            current_rates_ui[app_name][0] += down_speed
            current_rates_ui[app_name][1] += up_speed
            
            if new_down > 0 or new_up > 0:
                # Format: (ts, app, down_spd, up_spd, src, dst)
                log_entries.append((
                    now, app_name, down_speed, up_speed, src_ip, dst_ip
                ))

        if log_entries:
            # Save to Local DB
            self.db.log_instances(log_entries)
            # Send to Cloud
            self.cloud.add_logs(log_entries) # <--- PUSH TO CLOUD
            
        return current_rates_ui

    def save_data(self):
        self.db.save_traffic(self.global_totals)

    def get_logs(self, app_filter=None):
        return self.db.fetch_logs(limit=100, app_filter=app_filter)