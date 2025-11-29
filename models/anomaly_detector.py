# models/anomaly_detector.py

import os
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """
    Detects anomalies in patient vital signs using Isolation Forest.
    Features used: heart rate, systolic pressure, diastolic pressure.
    """

    def __init__(self, model_path='models/anomaly_model.joblib'):
        self.features = ['heart_rate', 'systolic', 'diastolic']
        self.model_path = model_path
        self.model = self._load_or_initialize_model()

    def _load_or_initialize_model(self):
        """
        Loads the trained model if available, otherwise initializes a new one.
        """
        if os.path.exists(self.model_path):
            try:
                return joblib.load(self.model_path)
            except Exception as e:
                print(f"⚠️ Failed to load saved model: {e}")
        
        print("📦 Initializing new Isolation Forest model.")
        return IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )

    def train(self, data_path="data/historical_vitals.csv"):
        """
        Trains the anomaly detection model using historical patient data.
        """
        try:
            df = pd.read_csv(data_path)
            self.model.fit(df[self.features])
            joblib.dump(self.model, self.model_path)
            print("✅ Anomaly model trained and saved successfully.")
        except Exception as e:
            print(f"❌ Training failed: {e}")

    def predict(self, heart_rate, systolic, diastolic):
        """
        Predicts anomaly (-1) or normal (1) for a new set of vital signs.
        """
        try:
            input_df = pd.DataFrame([[heart_rate, systolic, diastolic]], columns=self.features)
            prediction = self.model.predict(input_df)
            return int(prediction[0])
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return 1  # Default to "normal" in case of failure
