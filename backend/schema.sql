CREATE TABLE iot_devices (
    id SERIAL PRIMARY KEY,
    device_name TEXT NOT NULL,
    device_intensity TEXT,
    device_status TEXT,
    device_total_consumption DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE TABLE sensor_readings (
    id SERIAL,
    iot_device_id INT NOT NULL,
    reading_time TIMESTAMPTZ NOT NULL,
    voltage DOUBLE PRECISION,
    current DOUBLE PRECISION,
    power DOUBLE PRECISION,
    PRIMARY KEY (reading_time, id) 
);

SELECT create_hypertable(
    'sensor_readings',
    'reading_time'
);

CREATE TABLE energy_consumption (
    id SERIAL PRIMARY KEY,
    iot_device_id INT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    remaining_budget DOUBLE PRECISION NOT NULL,
    consumption_status TEXT
);

CREATE TABLE llm_plans (
    id SERIAL PRIMARY KEY,
    iot_device_id INT NOT NULL,
    proposed_schedule JSON NOT NULL,
    estimated_consumption DOUBLE PRECISION,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE system_configuration (
    id SERIAL PRIMARY KEY,
    data_collection_frequency INT NOT NULL,
    energy_budget DOUBLE PRECISION NOT NULL,
    comparison_period TEXT NOT NULL,
    total_consumption DOUBLE PRECISION NOT NULL DEFAULT 0
);

ALTER TABLE sensor_readings
ADD CONSTRAINT fk_sensor_device
FOREIGN KEY (iot_device_id)
REFERENCES iot_devices(id);

ALTER TABLE energy_consumption
ADD CONSTRAINT fk_energy_device
FOREIGN KEY (iot_device_id)
REFERENCES iot_devices(id);

ALTER TABLE llm_plans
ADD CONSTRAINT fk_llm_device
FOREIGN KEY (iot_device_id)
REFERENCES iot_devices(id);

CREATE INDEX idx_sensor_device_time
ON sensor_readings (iot_device_id, reading_time DESC);

INSERT INTO iot_devices (id, device_name, device_intensity, device_status, device_total_consumption) VALUES
(1, 'Fan', NULL, 'ON', 0),
(2, 'Motor', '0', 'OFF', 0),
(3, 'Light Bulb', NULL, 'OFF', 0);

INSERT INTO system_configuration (id, data_collection_frequency, energy_budget, comparison_period, total_consumption) VALUES
(1, 15, 1000000, 'today', 0);
