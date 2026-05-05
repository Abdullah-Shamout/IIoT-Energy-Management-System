import time
from datetime import datetime, timedelta
import config
from database import db

def aggregate_device_consumption():
    devices = db.get_all_devices()
    
    for device in devices:
        device_id = device['id']
        
        query = """
            SELECT SUM(power) as total_power
            FROM sensor_readings
            WHERE iot_device_id = %s
            AND reading_time >= NOW() - INTERVAL '15 seconds'
        """
        result = db.execute_one(query, (device_id,))
        
        if result and result['total_power']:
            power_sum_wh = result['total_power']
            current_total = device['device_total_consumption']
            new_total = current_total + power_sum_wh
            
            db.update_device_total_consumption(device_id, new_total)
            print(f"Device {device['device_name']} (ID={device_id}): Added {power_sum_wh}Wh, Total={new_total}Wh")

def aggregate_total_consumption():
    devices = db.get_all_devices()
    total = sum(device['device_total_consumption'] for device in devices)
    
    db.update_total_consumption(total)
    print(f"Total system consumption updated: {total}Wh ({total/1000:.2f}kWh)")

def run_aggregator():
    while True:
        try:
            print(f"\n[{datetime.now()}] Running data aggregation...")
            aggregate_device_consumption()
            aggregate_total_consumption()
            print("Aggregation complete.\n")
        except Exception as e:
            print(f"Aggregation error: {e}")
        
        time.sleep(config.DATA_COLLECTION_FREQUENCY)

if __name__ == "__main__":
    print("Starting Data Aggregator...")
    time.sleep(5)
    run_aggregator()
