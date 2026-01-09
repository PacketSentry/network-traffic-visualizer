import psutil

def kill_process_by_name(app_name):
    """Terminates processes matching the given name."""
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == app_name:
                proc.terminate()
    except: pass