import pandas as pd
import numpy as np
import random
import sqlite3
from datetime import datetime, timedelta
from models.anomaly_detector import AnomalyDetector
from models.risk_predictor import RiskPredictor
from config import IOT_CONFIG, DATABASE

class IoTDataService:
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.risk_predictor = RiskPredictor()
        self.mock_data = self._generate_mock_data()
        self.last_update = datetime.now()

    def _generate_mock_data(self):
        """Generate realistic physiological data with occasional anomalies"""
        now = datetime.now()
        num_records = 1440  # 24 hours of minute-by-minute data

        base_values = {
            'heart_rate': np.random.normal(75, 10, num_records),
            'systolic': np.random.normal(120, 15, num_records),
            'diastolic': np.random.normal(80, 10, num_records),
            'glucose': np.random.normal(100, 20, num_records),
            'bmi': np.random.uniform(18.5, 35.0, num_records)
        }

        # Inject anomalies
        for metric in base_values:
            anomaly_mask = np.random.choice(
                [False, True],
                size=num_records,
                p=[1 - IOT_CONFIG['anomaly_probability'], IOT_CONFIG['anomaly_probability']]
            )
            if metric == 'heart_rate':
                base_values[metric][anomaly_mask] *= 1.5
            elif metric == 'systolic':
                base_values[metric][anomaly_mask] += 30
            elif metric == 'glucose':
                base_values[metric][anomaly_mask] += 50

        df = pd.DataFrame({
            'timestamp': [now - timedelta(minutes=i) for i in range(num_records)][::-1],
            'heart_rate': np.clip(base_values['heart_rate'], *IOT_CONFIG['vital_ranges']['heart_rate']).astype(int),
            'systolic': np.clip(base_values['systolic'], *IOT_CONFIG['vital_ranges']['systolic']).astype(int),
            'diastolic': np.clip(base_values['diastolic'], *IOT_CONFIG['vital_ranges']['diastolic']).astype(int),
            'glucose': np.clip(base_values['glucose'], *IOT_CONFIG['vital_ranges']['glucose']).astype(int),
            'bmi': np.round(base_values['bmi'], 1)
        })

        # Calculate risk scores for mock data
        df['risk_score'] = df.apply(lambda row: 
            self.risk_predictor.predict_risk(
                age=35,  # Default age for mock data
                bmi=row['bmi'],
                glucose=row['glucose'],
                bp_avg=(row['systolic'] + row['diastolic']) / 2
            ), axis=1)

        # Add anomaly flags
        df['is_anomaly'] = df.apply(lambda row:
            self.anomaly_detector.predict(
                row['heart_rate'],
                row['systolic'],
                row['diastolic']
            ), axis=1)

        return df

    def get_live_data(self, user_id=None):
        """Return latest data point with simulated real-time updates"""
        if (datetime.now() - self.last_update).seconds > IOT_CONFIG['update_interval']:
            self._update_mock_data()

        latest_data = self.mock_data.iloc[-1].copy()
        if user_id:
            self._save_to_db(latest_data, user_id)

        return latest_data.to_frame().T

    def get_historical_data(self, user_id, days=7):
        """Retrieve historical data from the database"""
        conn = sqlite3.connect(DATABASE)
        query = '''
            SELECT timestamp, heart_rate, systolic, diastolic, 
                   glucose, bmi, is_anomaly, risk_score
            FROM health_data
            WHERE user_id = ? AND timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
        '''
        df = pd.read_sql_query(query, conn, params=(user_id, f'-{days} days'))
        conn.close()

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df

        return self.mock_data  # Fallback

    def _update_mock_data(self):
        """Add new data point and maintain rolling window"""
        new_row = self.mock_data.iloc[-1].copy()
        new_row['timestamp'] = datetime.now()

        for metric in ['heart_rate', 'systolic', 'diastolic', 'glucose']:
            new_row[metric] += random.randint(-2, 2)
            new_row[metric] = np.clip(new_row[metric], *IOT_CONFIG['vital_ranges'][metric])

        self.mock_data = pd.concat(
            [self.mock_data.iloc[1:], pd.DataFrame([new_row])],
            ignore_index=True
        )
        self.last_update = datetime.now()

    def _save_to_db(self, data, user_id):
        """Persist IoT data to database"""
        if user_id:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            
            # Calculate risk score
            risk_score = self.risk_predictor.predict_risk(
                age=35,  # Get actual age from user data
                bmi=data['bmi'],
                glucose=data['glucose'],
                bp_avg=(data['systolic'] + data['diastolic']) / 2
            )

            c.execute('''
                INSERT INTO health_data 
                (user_id, heart_rate, systolic, diastolic, glucose, 
                 bmi, timestamp, is_anomaly, risk_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                data['heart_rate'],
                data['systolic'],
                data['diastolic'],
                data['glucose'],
                data['bmi'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                data['is_anomaly'],
                risk_score
            ))
            conn.commit()
            conn.close()

    @staticmethod
    def validate_vital_signs(data):
        """Check if vital signs are within clinical thresholds"""
        alerts = []

        hr_range = IOT_CONFIG['vital_ranges']['heart_rate']
        if not hr_range[0] <= data['heart_rate'] <= hr_range[1]:
            alerts.append(f"Critical heart rate: {data['heart_rate']} BPM")

        hypertension = IOT_CONFIG['clinical_thresholds']['hypertension_stage2']
        if data['systolic'] > hypertension:
            alerts.append(f"Stage 2 hypertension: {data['systolic']} mmHg")

        hyperglycemia = IOT_CONFIG['clinical_thresholds']['hyperglycemia']
        if data['glucose'] > hyperglycemia:
            alerts.append(f"Hyperglycemia: {data['glucose']} mg/dL")

        return alerts