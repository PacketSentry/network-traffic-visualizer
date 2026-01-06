import time

class TrafficAggregator:
    def __init__(self):
        self.last_check_time = time.time()

    def calculate_rates(self, traffic_data):
        """
        Takes raw bytes data: {'Chrome': [10240, 2048]}
        Returns speed: {'Chrome': (10.0 KB/s, 2.0 KB/s)}
        """
        now = time.time()
        elapsed = now - self.last_check_time
        
        # Avoid division by zero if called too fast
        if elapsed < 0.1:
            elapsed = 0.1
            
        self.last_check_time = now
        
        rates = {}
        
        # traffic_data format is: { 'AppName': [Download_Bytes, Upload_Bytes] }
        for app_name, (down_bytes, up_bytes) in traffic_data.items():
            
            # Convert Bytes to Kilobytes (KB)
            # Divide by 'elapsed' to get Speed per Second
            down_speed = (down_bytes / 1024) / elapsed
            up_speed = (up_bytes / 1024) / elapsed
            
            rates[app_name] = (down_speed, up_speed)
            
        return rates