import json
import paho.mqtt.client as mqtt
import time
import config
from database import db

BROKER_IP = config.MQTT_BROKER_IP
BROKER_PORT = config.MQTT_BROKER_PORT
DEVICE_TOPIC = config.MQTT_DEVICE_TOPIC

STATE_TOPIC = f"stat/{DEVICE_TOPIC}/POWER"
SENSOR_TOPIC = f"tele/{DEVICE_TOPIC}/SENSOR"
COMMAND_TOPIC = f"cmnd/{DEVICE_TOPIC}/POWER"

current_value = 0
voltage_value = 0
power_value = 0

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Connected to MQTT broker at {BROKER_IP}:{BROKER_PORT}")
        client.subscribe(STATE_TOPIC)
        client.subscribe(SENSOR_TOPIC)
        print(f"Subscribed to {STATE_TOPIC} and {SENSOR_TOPIC}")
    else:
        print(f"MQTT connection failed with code {rc}")

def on_message(client, userdata, msg):
    global current_value, voltage_value, power_value

    topic = msg.topic
    payload = msg.payload.decode("utf-8", errors="replace")

    if topic == STATE_TOPIC:
        status = 'ON' if payload == 'ON' else 'OFF'
        db.update_device_status(config.LIGHT_BULB_ID, status)
        print(f"Light Bulb status updated: {status}")
        return

    if topic == SENSOR_TOPIC:
        try:
            data = json.loads(payload)
            energy = data.get("ENERGY", {})

            current_value = energy.get("Current", 0)
            voltage_value = energy.get("Voltage", 0)
            power_value = energy.get("Power", 0)

            device = db.get_device(config.LIGHT_BULB_ID)
            if device and device['device_status'].lower() == 'off':
                current_value = 0
                voltage_value = 0
                power_value = 0

            db.insert_sensor_reading(config.LIGHT_BULB_ID, voltage_value, current_value, power_value)
            print(f"Light Bulb data inserted: V={voltage_value}V, I={current_value}A, P={power_value}W")

        except Exception as e:
            print(f"Failed to parse SENSOR payload: {e}")

def turn_on():
    client.publish(COMMAND_TOPIC, "ON")
    print("Sent ON command to Light Bulb")

def turn_off():
    client.publish(COMMAND_TOPIC, "OFF")
    print("Sent OFF command to Light Bulb")

# Create MQTT client with v3.1.1 protocol (compatible with Athom plug)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message

# Standalone function for start_all.sh script
def start_mqtt_client():
    """Runs when executed as standalone script via start_all.sh"""
    print("Starting MQTT client for Athom plug...")
    client.connect(BROKER_IP, BROKER_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    start_mqtt_client()
