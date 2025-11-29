CREATE TABLE IF NOT EXISTS drugs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    class TEXT,
    fda_approved INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY,
    drug1_id INTEGER,
    drug2_id INTEGER,
    severity INTEGER CHECK(severity BETWEEN 1 AND 4),
    description TEXT,
    FOREIGN KEY(drug1_id) REFERENCES drugs(id),
    FOREIGN KEY(drug2_id) REFERENCES drugs(id)
);

CREATE TABLE IF NOT EXISTS side_effects (
    drug_id INTEGER,
    effect TEXT,
    frequency REAL,
    FOREIGN KEY(drug_id) REFERENCES drugs(id)
);

-- Sample data
INSERT INTO drugs (name, class) VALUES 
('Ibuprofen', 'NSAID'),
('Aspirin', 'NSAID'),
('Warfarin', 'Anticoagulant');

INSERT INTO interactions (drug1_id, drug2_id, severity, description) VALUES
(1, 2, 3, 'Increased risk of gastrointestinal bleeding'),
(1, 3, 4, 'May potentiate anticoagulant effect');

INSERT INTO side_effects (drug_id, effect, frequency) VALUES
(1, 'Stomach irritation', 0.15),
(1, 'Headache', 0.08),
(3, 'Easy bruising', 0.25);
