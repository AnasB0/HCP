CREATE TABLE IF NOT EXISTS questionnaires (
    id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    questions TEXT  -- JSON stored as text
);

CREATE TABLE IF NOT EXISTS prom_responses (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    questionnaire_id INTEGER,
    responses TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES users(id),
    FOREIGN KEY(questionnaire_id) REFERENCES questionnaires(id)
);

-- Sample PROMs
INSERT INTO questionnaires (name, description, questions) VALUES 
('Pain Scale', 'Visual Analog Scale', '["Rate your pain (0-10):"]'),
('PHQ-9', 'Depression Assessment', '["Little interest in activities", "Feeling down", "Sleep issues"]');
