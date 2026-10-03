-- PostgreSQL Schema for Indian Vehicle Number Plate Recognition

-- 1. Cameras Table
CREATE TABLE IF NOT EXISTS cameras (
    id SERIAL PRIMARY KEY,
    camera_code VARCHAR(50) UNIQUE NOT NULL,
    camera_name VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    source_type VARCHAR(50) DEFAULT 'WEBCAM',
    source VARCHAR(255) DEFAULT '0',
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed default webcam
INSERT INTO cameras (camera_code, camera_name, location, source_type, source, status)
VALUES ('CAM-01', 'Default Webcam', 'Main Gate', 'WEBCAM', '0', 'ACTIVE')
ON CONFLICT (camera_code) DO NOTHING;

-- 2. College Vehicles Table (Master List)
CREATE TABLE IF NOT EXISTS college_vehicles (
    id SERIAL PRIMARY KEY,
    vehicle_number VARCHAR(32) UNIQUE NOT NULL,
    vehicle_name VARCHAR(128) NOT NULL,
    vehicle_type VARCHAR(64) DEFAULT 'BUS' NOT NULL,
    status VARCHAR(32) DEFAULT 'ACTIVE' NOT NULL,
    current_status VARCHAR(32) DEFAULT 'OUTSIDE' NOT NULL,
    last_movement_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_college_vehicles_number ON college_vehicles(vehicle_number);

-- Seed Initial College Buses / Vehicles
INSERT INTO college_vehicles (vehicle_number, vehicle_name, vehicle_type, status, current_status)
VALUES 
    ('TN45BD7321', 'College Bus 01', 'BUS', 'ACTIVE', 'OUTSIDE'),
    ('TN45BD8456', 'College Bus 02', 'BUS', 'ACTIVE', 'OUTSIDE'),
    ('TN45BD9999', 'College Van 01', 'VAN', 'ACTIVE', 'OUTSIDE')
ON CONFLICT (vehicle_number) DO NOTHING;

-- 3. General / Other Vehicles Table
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    plate_number VARCHAR(32) UNIQUE NOT NULL,
    vehicle_category VARCHAR(32) DEFAULT 'OTHER_VEHICLE' NOT NULL,
    current_status VARCHAR(32) DEFAULT 'OUTSIDE' NOT NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_sightings INTEGER DEFAULT 1,
    notes VARCHAR(256)
);

CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON vehicles(plate_number);

-- 4. Recognition Events Table (Live In/Out Events)
CREATE TABLE IF NOT EXISTS recognition_events (
    id SERIAL PRIMARY KEY,
    plate_number VARCHAR(32) NOT NULL,
    college_vehicle_id INTEGER REFERENCES college_vehicles(id) ON DELETE SET NULL,
    vehicle_category VARCHAR(32) DEFAULT 'OTHER_VEHICLE' NOT NULL,
    vehicle_name VARCHAR(128),
    movement_type VARCHAR(32) DEFAULT 'ENTRY' NOT NULL,
    current_status VARCHAR(32) DEFAULT 'INSIDE' NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    entry_time TIMESTAMP WITH TIME ZONE,
    exit_time TIMESTAMP WITH TIME ZONE,
    yolo_confidence FLOAT NOT NULL,
    ocr_confidence FLOAT NOT NULL,
    vehicle_image_path VARCHAR(512),
    plate_image_path VARCHAR(512),
    camera_id VARCHAR(64) DEFAULT 'CAM-01',
    frames_observed INTEGER DEFAULT 1,
    status VARCHAR(32) DEFAULT 'VERIFIED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast query and filtering
CREATE INDEX IF NOT EXISTS idx_recognition_events_plate ON recognition_events(plate_number);
CREATE INDEX IF NOT EXISTS idx_recognition_events_detected_at ON recognition_events(detected_at);
CREATE INDEX IF NOT EXISTS idx_recognition_events_camera ON recognition_events(camera_id);
CREATE INDEX IF NOT EXISTS idx_recognition_events_category ON recognition_events(vehicle_category);
CREATE INDEX IF NOT EXISTS idx_recognition_events_movement ON recognition_events(movement_type);
