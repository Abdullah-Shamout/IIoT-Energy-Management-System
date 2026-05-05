import time
from datetime import datetime, timedelta
import config
from database import db

last_alert_time = None
ALERT_INTERVAL_MINUTES = 10

def check_budget_and_alert():
    global last_alert_time
    
    try:
        system_config = db.get_system_config()
        if not system_config:
            print("System configuration not found")
            return

        total_consumption_wh = system_config['total_consumption']
        energy_budget_kwh = system_config['energy_budget']
        energy_budget_wh = energy_budget_kwh * 1000

        if total_consumption_wh > energy_budget_wh:
            current_time = datetime.now()
            
            if last_alert_time is None or (current_time - last_alert_time) >= timedelta(minutes=ALERT_INTERVAL_MINUTES):
                exceeded_by = total_consumption_wh - energy_budget_wh
                print(f"\n{'='*60}")
                print(f"ALERT: Energy budget exceeded!")
                print(f"Budget: {energy_budget_kwh:.2f} kWh")
                print(f"Current Consumption: {total_consumption_wh/1000:.2f} kWh")
                print(f"Exceeded by: {exceeded_by/1000:.2f} kWh")
                print(f"{'='*60}\n")
                
                last_alert_time = current_time
                
        else:
            print(f"Budget OK: {total_consumption_wh/1000:.2f} kWh / {energy_budget_kwh:.2f} kWh")

    except Exception as e:
        print(f"Budget alert error: {e}")

def run_budget_monitor():
    print("Starting Budget Alert Monitor...")
    while True:
        check_budget_and_alert()
        time.sleep(60)

if __name__ == "__main__":
    run_budget_monitor()
