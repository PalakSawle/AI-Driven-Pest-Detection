BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 872a37cc2c7e

CREATE TABLE crops (
    id SERIAL NOT NULL, 
    key VARCHAR(50) NOT NULL, 
    name VARCHAR(80) NOT NULL, 
    name_hi VARCHAR(80) NOT NULL, 
    growth_stages JSON NOT NULL, 
    stage_sensitivity JSON NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (key)
);

CREATE TABLE model_versions (
    id SERIAL NOT NULL, 
    name VARCHAR(80) NOT NULL, 
    version VARCHAR(40) NOT NULL, 
    architecture VARCHAR(80) NOT NULL, 
    dataset VARCHAR(200) NOT NULL, 
    classes JSON NOT NULL, 
    metrics JSON NOT NULL, 
    weights_path VARCHAR(300) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE treatment_recommendations (
    id SERIAL NOT NULL, 
    pest_key VARCHAR(80) NOT NULL, 
    common_name VARCHAR(120) NOT NULL, 
    common_name_hi VARCHAR(120), 
    scientific_name VARCHAR(120), 
    crops JSON NOT NULL, 
    symptoms JSON NOT NULL, 
    organic JSON NOT NULL, 
    biological JSON NOT NULL, 
    chemical_categories JSON NOT NULL, 
    preventive JSON NOT NULL, 
    ipm JSON NOT NULL, 
    monitoring TEXT NOT NULL, 
    etl_note TEXT, 
    "references" JSON NOT NULL, 
    severity_weight FLOAT NOT NULL, 
    curated BOOLEAN NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_treatment_recommendations_pest_key ON treatment_recommendations (pest_key);

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    hashed_password VARCHAR(255) NOT NULL, 
    full_name VARCHAR(120) NOT NULL, 
    phone VARCHAR(30), 
    role VARCHAR(20) NOT NULL, 
    language VARCHAR(10) NOT NULL, 
    email_alerts BOOLEAN NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    reset_token_hash VARCHAR(255), 
    reset_token_expires TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE alert_thresholds (
    id SERIAL NOT NULL, 
    user_id INTEGER, 
    pest_class VARCHAR(80) NOT NULL, 
    basis VARCHAR(20) NOT NULL, 
    low FLOAT NOT NULL, 
    moderate FLOAT NOT NULL, 
    high FLOAT NOT NULL, 
    critical FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (user_id, pest_class, basis)
);

CREATE INDEX ix_alert_thresholds_user_id ON alert_thresholds (user_id);

CREATE TABLE chat_conversations (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_chat_conversations_user_id ON chat_conversations (user_id);

CREATE TABLE farms (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    location_name VARCHAR(200), 
    state VARCHAR(80), 
    latitude FLOAT, 
    longitude FLOAT, 
    area_hectares FLOAT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_farms_user_id ON farms (user_id);

CREATE TABLE user_crops (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    crop_id INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(crop_id) REFERENCES crops (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (user_id, crop_id)
);

CREATE INDEX ix_user_crops_user_id ON user_crops (user_id);

CREATE TABLE weather_records (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    latitude FLOAT NOT NULL, 
    longitude FLOAT NOT NULL, 
    temperature_c FLOAT, 
    humidity_pct FLOAT, 
    rainfall_mm FLOAT, 
    wind_kmh FLOAT, 
    provider VARCHAR(30) NOT NULL, 
    payload JSON NOT NULL, 
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_weather_records_user_id ON weather_records (user_id);

CREATE TABLE chat_messages (
    id SERIAL NOT NULL, 
    conversation_id INTEGER NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    content TEXT NOT NULL, 
    language VARCHAR(10), 
    source VARCHAR(30), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(conversation_id) REFERENCES chat_conversations (id) ON DELETE CASCADE
);

CREATE INDEX ix_chat_messages_conversation_id ON chat_messages (conversation_id);

CREATE TABLE detections (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    farm_id INTEGER, 
    crop_id INTEGER, 
    model_version_id INTEGER, 
    growth_stage VARCHAR(40), 
    sample_type VARCHAR(30) NOT NULL, 
    trap_area_cm2 FLOAT, 
    observation_hours FLOAT, 
    image_key VARCHAR(300) NOT NULL, 
    annotated_key VARCHAR(300), 
    image_width INTEGER NOT NULL, 
    image_height INTEGER NOT NULL, 
    total_count INTEGER NOT NULL, 
    low_confidence_count INTEGER NOT NULL, 
    mean_confidence FLOAT, 
    inference_ms FLOAT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    notes TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(crop_id) REFERENCES crops (id) ON DELETE SET NULL, 
    FOREIGN KEY(farm_id) REFERENCES farms (id) ON DELETE SET NULL, 
    FOREIGN KEY(model_version_id) REFERENCES model_versions (id) ON DELETE SET NULL, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_detections_created_at ON detections (created_at);

CREATE INDEX ix_detections_user_created ON detections (user_id, created_at);

CREATE INDEX ix_detections_user_id ON detections (user_id);

CREATE TABLE density_observations (
    id SERIAL NOT NULL, 
    detection_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    pest_class VARCHAR(80) NOT NULL, 
    count INTEGER NOT NULL, 
    value FLOAT NOT NULL, 
    unit VARCHAR(40) NOT NULL, 
    method VARCHAR(40) NOT NULL, 
    level VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(detection_id) REFERENCES detections (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_density_observations_detection_id ON density_observations (detection_id);

CREATE INDEX ix_density_user_pest ON density_observations (user_id, pest_class, created_at);

CREATE TABLE detected_instances (
    id SERIAL NOT NULL, 
    detection_id INTEGER NOT NULL, 
    pest_class VARCHAR(80) NOT NULL, 
    confidence FLOAT NOT NULL, 
    x1 FLOAT NOT NULL, 
    y1 FLOAT NOT NULL, 
    x2 FLOAT NOT NULL, 
    y2 FLOAT NOT NULL, 
    low_confidence BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(detection_id) REFERENCES detections (id) ON DELETE CASCADE
);

CREATE INDEX ix_detected_instances_detection_id ON detected_instances (detection_id);

CREATE INDEX ix_detected_instances_pest_class ON detected_instances (pest_class);

CREATE TABLE notifications (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    type VARCHAR(30) NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    message TEXT NOT NULL, 
    level VARCHAR(20) NOT NULL, 
    detection_id INTEGER, 
    is_read BOOLEAN NOT NULL, 
    due_at TIMESTAMP WITH TIME ZONE, 
    emailed BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(detection_id) REFERENCES detections (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_created_at ON notifications (created_at);

CREATE INDEX ix_notifications_user_read ON notifications (user_id, is_read);

CREATE TABLE severity_assessments (
    id SERIAL NOT NULL, 
    detection_id INTEGER NOT NULL, 
    score FLOAT NOT NULL, 
    level VARCHAR(20) NOT NULL, 
    factors JSON NOT NULL, 
    explanation TEXT NOT NULL, 
    recommended_action TEXT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(detection_id) REFERENCES detections (id) ON DELETE CASCADE, 
    UNIQUE (detection_id)
);

CREATE INDEX ix_severity_assessments_level ON severity_assessments (level);

INSERT INTO alembic_version (version_num) VALUES ('872a37cc2c7e') RETURNING alembic_version.version_num;

COMMIT;

