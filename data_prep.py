# data_prep.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create synthetic data directory
import os
os.makedirs("data", exist_ok=True)

# 1. Generate Historical Vitals Data (For Anomaly Detection)
def generate_vitals_data():
    timestamps = [datetime.now() - timedelta(minutes=i) for i in range(5000)]
    data = pd.DataFrame({
        'timestamp': timestamps,
        'heart_rate': np.random.normal(75, 15, 5000).astype(int),
        'systolic': np.random.randint(90, 180, 5000),
        'diastolic': np.random.randint(60, 120, 5000),
        'glucose': np.random.randint(70, 300, 5000),
        'is_anomaly': np.random.choice([0,1], 5000, p=[0.95,0.05])
    })
    data.to_csv("data/historical_vitals.csv", index=False)

# 2. Generate Patient Metrics (For Risk Prediction)
def generate_risk_data():
    data = pd.DataFrame({
        'age': np.random.randint(18, 90, 1000),
        'bmi': np.random.uniform(18.5, 45.0, 1000),
        'glucose': np.random.randint(70, 300, 1000),
        'bp_avg': np.random.randint(90, 160, 1000),
        'diabetes_risk': np.random.choice([0,1], 1000, p=[0.7,0.3])
    })
    data.to_csv("data/patient_metrics.csv", index=False)

# 3. Generate Patient Clustering Data
def generate_cluster_data():
    data = pd.DataFrame({
        'age': np.random.randint(18, 90, 500),
        'bmi': np.random.uniform(18.5, 45.0, 500),
        'risk_score': np.random.uniform(0, 100, 500)
    })
    data.to_csv("data/patient_data.csv", index=False)

if __name__ == "__main__":
    generate_vitals_data()
    generate_risk_data()
    generate_cluster_data()