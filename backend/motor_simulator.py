import time
import config
from database import db

MOTOR_MAX_POWER = 350

def calculate_motor_power(intensity):
    return (intensity / 100.0) * MOTOR_MAX_POWER

def simulate_motor():
    while True:
        try:
            device = db.get_device(config.MOTOR_ID)
            if not device:
                print("Motor device not found in database")
                time.sleep(config.DATA_COLLECTION_FREQUENCY)
                continue

            intensity = float(device['device_intensity'] or 0)
            status = device['device_status']

            if status.lower() == 'off':
                power = 0
                voltage = 0
                current = 0
            else:
                power = calculate_motor_power(intensity)
                voltage = 220.0
                current = power / voltage if voltage > 0 else 0

            db.insert_sensor_reading(config.MOTOR_ID, voltage, current, power)
            print(f"Motor data inserted: Intensity={intensity}%, V={voltage}V, I={current:.2f}A, P={power}W")

        except Exception as e:
            print(f"Motor simulation error: {e}")

        time.sleep(config.DATA_COLLECTION_FREQUENCY)

if __name__ == "__main__":
    print("Starting Motor simulator...")
    simulate_motor()
