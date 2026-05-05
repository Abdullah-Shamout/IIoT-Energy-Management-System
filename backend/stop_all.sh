#!/bin/bash

echo "Stopping Energy Management System Backend..."

pkill -f "python3 pzem_reader.py"
pkill -f "python3 athom_mqtt.py"
pkill -f "python3 motor_simulator.py"
pkill -f "python3 data_aggregator.py"
pkill -f "python3 budget_alert.py"
pkill -f "python3 app.py"

echo "All services stopped!"
