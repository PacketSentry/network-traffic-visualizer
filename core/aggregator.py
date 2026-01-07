import time
from core.database import DatabaseManager

class TrafficAggregator:
    def __init__(self):
        self.last_check_time = time.time()
        self.db = DatabaseManager()
        # Load history from DB so we don't start at 0 every time
        self.global_totals = self.db.load_traffic()

    def calculate_rates(self, fresh_traffic_data):
        """
        Calculates rates and ensures idle apps remain in the list (Stability Fix).
        """
        now = time.time()
        elapsed = now - self.last_check_time
        if elapsed < 0.1: elapsed = 0.1
        self.last_check_time = now
        
        # 1. STABILITY FIX: Initialize UI rates with 0 for ALL known apps.
        # This ensures apps don't disappear from the UI just because they are idle.
        current_rates_ui = {app: [0.0, 0.0] for app in self.global_totals.keys()}
        
        log_entries = []
        
        # 2. Process fresh traffic
        for (app_name, src_ip, dst_ip), (new_down, new_up) in fresh_traffic_data.items():
            
            # Update Global Totals (The "Time Machine" part)
            if app_name not in self.global_totals:
                self.global_totals[app_name] = [0, 0]
                # If it's a brand new app, add it to current UI map immediately
                if app_name not in current_rates_ui:
                    current_rates_ui[app_name] = [0.0, 0.0]
            
            self.global_totals[app_name][0] += new_down
            self.global_totals[app_name][1] += new_up
            
            # Calculate Speed (The "Live Graph" part)
            down_speed = (new_down / 1024) / elapsed
            up_speed = (new_up / 1024) / elapsed
            
            # Add to UI totals (Aggregating multiple IPs for the same App)
            current_rates_ui[app_name][0] += down_speed
            current_rates_ui[app_name][1] += up_speed
            
            # Prepare Log Entry if there is traffic
            if new_down > 0 or new_up > 0:
                log_entries.append((
                    now, app_name, down_speed, up_speed, src_ip, dst_ip
                ))

        # 3. Save Logs
        if log_entries:
            self.db.log_instances(log_entries)
            
        return current_rates_ui

    def save_data(self):
        """Triggers a database save of the global totals"""
        self.db.save_traffic(self.global_totals)

    def get_logs(self, app_filter=None):
        """Helper to fetch logs for UI"""
        return self.db.fetch_logs(limit=100, app_filter=app_filter)