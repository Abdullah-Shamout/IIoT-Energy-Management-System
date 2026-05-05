import minimalmodbus
import serial
import time
import config
from database import db

PORT = config.PZEM_PORT
SLAVE_ID = config.PZEM_SLAVE_ID

instrument = minimalmodbus.Instrument(PORT, SLAVE_ID)
instrument.serial.baudrate = 9600
instrument.serial.bytesize = 8
instrument.serial.parity = serial.PARITY_NONE
instrument.serial.stopbits = 2
instrument.serial.timeout = 1
instrument.mode = minimalmodbus.MODE_RTU
instrument.clear_buffers_before_each_transaction = True

def read_pzem():
    try:
        regs = instrument.read_registers(0, 8, functioncode=4)

        voltage = regs[0] / 100.0
        current = regs[1] / 100.0
        power = ((regs[3] << 16) | regs[2]) / 10.0

        return {
            "voltage_v": voltage,
            "current_a": current,
            "power_w": power,
        }
    except Exception as e:
        print(f"PZEM Read Error: {e}")
        return None

def collect_fan_data():
    while True:
        try:
            device = db.get_device(config.FAN_ID)
            if not device:
                print("Fan device not found in database")
                time.sleep(config.DATA_COLLECTION_FREQUENCY)
                continue

            data = read_pzem()
            
            if data:
                voltage = data['voltage_v']
                current = data['current_a']
                power = data['power_w']

                if device['device_status'].lower() == 'off':
                    voltage = 0
                    current = 0
                    power = 0

                db.insert_sensor_reading(config.FAN_ID, voltage, current, power)
                print(f"Fan data inserted: V={voltage}V, I={current}A, P={power}W")
            else:
                print("Failed to read PZEM data")

        except Exception as e:
            print(f"Fan collection error: {e}")

        time.sleep(config.DATA_COLLECTION_FREQUENCY)

if __name__ == "__main__":
    print("Starting PZEM-017 Fan data collector...")
    collect_fan_data()
