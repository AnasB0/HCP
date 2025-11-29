# App Configuration

# Security (simple string, no encryption used)
SECRET_KEY = "healthcare-ai-system-2024"

# Database Configuration
DATABASE = "healthcare.db"
UPLOAD_FOLDER = "health_reports"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'csv'}
MAX_FILE_SIZE_MB = 10

DRUG_DB = "healthcare.db"
PROM_DB = "healthcare.db"

# API_KEY moved to Streamlit secrets
MODEL_NAME = "deepseek/deepseek-chat-v3-0324"
PALM_SETTINGS = {
    "temperature": 0.7,
    "max_tokens": 1024
}

MODEL_PATHS = {
    "anomaly": "models/anomaly_model.joblib",
    "risk": "models/risk_model.joblib",
    "cluster": "models/cluster_model.joblib"
}

# IoT Device Simulation
IOT_CONFIG = {
    "mock_mode": True,
    "update_interval": 5,
    "vital_ranges": {
        "heart_rate": (60, 100),
        "systolic": (90, 140),
        "diastolic": (60, 90),
        "glucose": (70, 200),
        "bmi": (18.5, 35.0)
    },
    "anomaly_probability": 0.05
}

# Clinical Thresholds
CLINICAL_THRESHOLDS = {
    "critical_heart_rate": (40, 140),
    "hypotension": 90,
    "hypertension_stage1": 130,
    "hypertension_stage2": 140,
    "hypoglycemia": 70,
    "hyperglycemia": 126
}


# App Settings
MAX_HISTORY = 20