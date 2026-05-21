CREATE TABLE iot_devices (
    device_id VARCHAR(50) PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL REFERENCES regions(region_code),
    sensor_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    last_ping_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE iot_telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) REFERENCES iot_devices(device_id),
    value DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
