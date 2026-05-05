#!/bin/bash

echo "Starting Energy Management System Backend..."

python3 pzem_reader.py &
PZEM_PID=$!
echo "Started PZEM Reader (PID: $PZEM_PID)"

python3 athom_mqtt.py &
ATHOM_PID=$!
echo "Started Athom MQTT Client (PID: $ATHOM_PID)"

python3 motor_simulator.py &
MOTOR_PID=$!
echo "Started Motor Simulator (PID: $MOTOR_PID)"

sleep 5

python3 data_aggregator.py &
AGGREGATOR_PID=$!
echo "Started Data Aggregator (PID: $AGGREGATOR_PID)"

python3 budget_alert.py &
BUDGET_PID=$!
echo "Started Budget Alert Monitor (PID: $BUDGET_PID)"

python3 app.py &
FLASK_PID=$!
echo "Started Flask API (PID: $FLASK_PID)"

echo ""
echo "All services started!"
echo "PZEM Reader PID: $PZEM_PID"
echo "Athom MQTT PID: $ATHOM_PID"
echo "Motor Simulator PID: $MOTOR_PID"
echo "Data Aggregator PID: $AGGREGATOR_PID"
echo "Budget Alert PID: $BUDGET_PID"
echo "Flask API PID: $FLASK_PID"
echo ""
echo "To stop all services, run: kill $PZEM_PID $ATHOM_PID $MOTOR_PID $AGGREGATOR_PID $BUDGET_PID $FLASK_PID"

wait
