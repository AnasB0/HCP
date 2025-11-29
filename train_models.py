# train_models.py
from models.anomaly_detector import AnomalyDetector
from models.risk_predictor import RiskPredictor
from models.patient_cluster import PatientCluster
import time

def train_anomaly_model():
    print("Training Anomaly Detector...")
    model = AnomalyDetector()
    model.train(data_path="data/historical_vitals.csv")
    print("✅ Anomaly model saved to models/anomaly_model.joblib")

def train_risk_model():
    print("Training Risk Predictor...")
    model = RiskPredictor()
    model.train(data_path="data/patient_metrics.csv")
    print("✅ Risk model saved to models/risk_model.joblib")

def train_cluster_model():
    print("Training Patient Cluster...")
    model = PatientCluster()
    model.train(data_path="data/patient_data.csv")
    print("✅ Cluster model saved to models/cluster_model.joblib")

if __name__ == "__main__":
    start = time.time()
    
    train_anomaly_model()
    train_risk_model()
    train_cluster_model()
    
    print(f"Training completed in {time.time()-start:.2f} seconds")