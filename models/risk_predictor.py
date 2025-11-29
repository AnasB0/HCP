import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

class RiskPredictor:
    def __init__(self):
        self.model = GradientBoostingClassifier(n_estimators=100)
        
    def train(self, data_path="data/patient_metrics.csv"):
        df = pd.read_csv(data_path)
        X = df[['age', 'bmi', 'glucose', 'bp_avg']]
        y = df['diabetes_risk']
        self.model.fit(X, y)
        joblib.dump(self.model, 'models/risk_model.joblib')
    
    def predict_risk(self, age, bmi, glucose, bp_avg):
        model = joblib.load('models/risk_model.joblib')
        return model.predict_proba([[age, bmi, glucose, bp_avg]])[0][1]