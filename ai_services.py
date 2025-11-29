from logging import Logger
import requests
import pandas as pd
import numpy as np
import streamlit as st
import sqlite3
import json

from config import MODEL_NAME, DATABASE, DRUG_DB, PALM_SETTINGS, PROM_DB
import streamlit as st  # Ensure st is available for secrets
from models.risk_predictor import RiskPredictor
from models.patient_cluster import PatientCluster
from models.anomaly_detector import AnomalyDetector


@st.cache_resource
def init_db_connection(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection failed: {str(e)}")
        raise

class HealthAssistant:
    def __init__(self):
        self.med_conn = init_db_connection(DATABASE)
        st.session_state.setdefault('chat_history', [])

    def _call_ai_api(self, messages):
        try:
            headers = {
                "Authorization": f"Bearer {st.secrets.get('API_KEY', 'fallback-key')}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                **PALM_SETTINGS
            }

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )

            if response.status_code != 200:
                st.error(f"API Error {response.status_code}: {response.text[:300]}")
                return "⚠️ API error or model not responding properly."

            data = response.json()

            if 'choices' in data and data['choices']:
                return data['choices'][0]['message'].get('content', "⚠️ No response from AI.")
            else:
                return "⚠️ Unexpected API response format."

        except Exception as e:
            st.error(f"AI API call failed: {str(e)}")
            return "⚠️ AI service unavailable."

    def chat(self, prompt, mode):
        try:
            handlers = {
                1: self._handle_medicine,
                2: self._handle_remedies,
                3: self._handle_assessment
            }
            return handlers.get(mode, self._handle_medicine)(prompt)
        except Exception as e:
            st.error(f"Chat error: {str(e)}")
            return "⚠️ Chat system error."

    def _handle_medicine(self, prompt):
        system_prompt = (
    "You are a clinical pharmacology AI. Provide a **concise summary** of a drug with these sections:\n"
    "1. 📄 Name\n2. 💊 Uses\n3. 📏 Dose (range only)\n4. ⚠️ Key Side Effects\n5. 📋 Prescription/OTC\n\n"
    "Be brief: each section should be 1–2 sentences max. If the user wants more, they will ask.\n"
    "No extra notes unless asked. Use Markdown format, not full HTML."
)

        return self._call_ai_api([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt.strip()}
        ])

    def _handle_remedies(self, prompt):
        return self._call_ai_api([
            {"role": "system", "content": "You are a natural remedies advisor. Provide safe, science-backed remedies for symptoms or conditions."},
            {"role": "user", "content": prompt.strip()}
        ])

    def _handle_assessment(self, prompt):
        return self._call_ai_api([
            {"role": "system", "content": "You are a health assessment tool. Help the user understand their symptoms and recommend whether to seek professional help."},
            {"role": "user", "content": prompt.strip()}
        ])

    def _get_patient_context(self):
        if 'user' not in st.session_state:
            return ""
        user_id = st.session_state.user['id']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT risk_score, cluster FROM users WHERE id = ?", (user_id,))
        risk, cluster = c.fetchone() or (0, 0)
        c.execute('''
            SELECT heart_rate, systolic, diastolic, glucose, bmi
            FROM health_data
            WHERE user_id = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (user_id,))
        vitals = c.fetchone()
        conn.close()
        context = f"Patient Context:\n- Risk: {risk}%\n- Cluster: {cluster}\n"
        if vitals:
            context += f"- Vitals: HR {vitals[0]}, BP {vitals[1]}/{vitals[2]}, Glucose {vitals[3]}, BMI {vitals[4]}"
        return context


    def _enhance_with_ml(self, response, prompt):
        prompt = prompt.lower()
        enhancements = []

        if any(metric in prompt for metric in ["blood pressure", "heart rate", "glucose", "bmi"]):
            enhancements.append(self._get_anomaly_status())

        return f"{response}\n\n---\n" + "\n\n".join(enhancements) if enhancements else response

    def _get_anomaly_status(self):
        try:
            conn = sqlite3.connect(DATABASE)
            df = pd.read_sql('''
                SELECT is_anomaly
                FROM health_data
                WHERE user_id = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', conn, params=(st.session_state.user['id'],))
            conn.close()

            if not df.empty and df.iloc[0]['is_anomaly']:
                return "🚨 Recent vitals indicate an anomaly. Please seek medical attention."
            return "✅ Vitals appear stable."
        except:
            return "⚠️ Could not assess anomaly status."

    def get_recommendation(self, patient_data):
        try:
            trend = self._predict_risk_progression(patient_data['id'])
            guidelines = self._get_cluster_guidelines(patient_data['cluster'])

            return f"""
            ### 🧠 AI Treatment Recommendation

            **Patient:** {patient_data['name']}  
            **Risk Profile:** {patient_data['risk_score']}% ({trend})  
            **Care Group:** Cluster {patient_data['cluster']}

            {guidelines}
            """
        except Exception as e:
            return f"⚠️ Recommendation Error: {str(e)}"

    def _predict_risk_progression(self, user_id):
        conn = sqlite3.connect(DATABASE)
        df = pd.read_sql_query('''
            SELECT timestamp, risk_score
            FROM health_data
            WHERE user_id = ?
            ORDER BY timestamp
        ''', conn, params=(user_id,))
        conn.close()

        if df.empty or len(df) < 2:
            return "Not enough data"

        trend = np.polyfit(np.arange(len(df)), df['risk_score'], 1)[0]
        return "↑ Increasing" if trend > 0 else "↓ Decreasing"

    def _get_cluster_guidelines(self, cluster):
        return {
            0: "🟢 **Standard Care**: Monthly checkups and wellness tracking.",
            1: "🟡 **Enhanced Monitoring**: Bi-weekly checkups and dietary coaching.",
            2: "🟠 **High Risk**: Weekly reviews with medical supervision.",
            3: "🔴 **Critical Protocol**: Daily monitoring with specialist support.",
        }.get(cluster, "Default care applies.")

    def analyze_trends(self, days=7):
        try:
            df = pd.read_sql('''
                SELECT timestamp, heart_rate, systolic, diastolic
                FROM health_data
                WHERE user_id = ? AND timestamp >= DATE('now', ?)
            ''', sqlite3.connect(DATABASE), params=(st.session_state.user['id'], f'-{days} days'))

            if df.empty:
                return "No data available for trend analysis."

            analysis = []
            for metric in ['heart_rate', 'systolic', 'diastolic']:
                stats = df[metric].agg(['mean', 'std', 'max', 'min'])
                analysis.append(f"""
                **{metric.replace('_', ' ').title()}**
                - Average: {stats['mean']:.1f}
                - Variability: ±{stats['std']:.1f}
                - Range: {stats['min']} to {stats['max']}
                """)
            return "\n".join(analysis)

        except Exception as e:
            return f"⚠️ Error in trend analysis: {str(e)}"
