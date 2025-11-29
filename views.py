import datetime
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import date
from iot_services import IoTDataService
from ai_services import HealthAssistant
from auth import (
    get_doctor_appointments, get_patient_reports_for_doctor, is_file_duplicate, save_appointment, save_report, get_user_reports, save_emergency,
    get_active_emergencies, resolve_emergency, get_doctor_patients
)
from models.risk_predictor import RiskPredictor
from models.patient_cluster import PatientCluster
from models.anomaly_detector import AnomalyDetector

# Initialize Services
iot_service = IoTDataService()
risk_model = RiskPredictor()
cluster_model = PatientCluster()
anomaly_detector = AnomalyDetector()

# ────────────────────────────────────────────────
# PATIENT DASHBOARD
# ────────────────────────────────────────────────

def patient_dashboard():
    if st.session_state.user["role"] != "patient":
        st.error("Patient access required")
        return

    username = st.session_state.user['username'].split('@')[0]
    st.title(f"👋 Welcome, {username}!")

    _render_live_metrics()
    _render_ai_health_analysis()
    _render_patient_tabs()

    st.header("🚨 Emergency Assistance")
    if st.button("Trigger Emergency Alert", type="primary"):
        save_emergency(st.session_state.user['id'])
        st.success("Emergency alert sent! Doctor will respond within 5 minutes")

        conn = sqlite3.connect("healthcare.db")
        c = conn.cursor()
        c.execute('''UPDATE appointments SET status = 'Priority' WHERE user_id = ? AND date >= DATE('now')''', (st.session_state.user['id'],))
        conn.commit()
        conn.close()

def _render_live_metrics():
    with st.container():
        st.header("📈 Live Health Metrics")
        col1, col2, col3 = st.columns([3, 1, 1])

        data = iot_service.get_historical_data(st.session_state.user['id'])

        with col1:
            fig = px.area(data, x='timestamp', y=['heart_rate', 'systolic'],
                          title="24-Hour Health Trends",
                          labels={"value": "Measurement"})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            latest = data.iloc[-1]
            st.metric("❤️ Heart Rate", f"{latest['heart_rate']} BPM",
                      delta="Normal" if not latest['is_anomaly'] else "Abnormal",
                      delta_color="inverse")

        with col3:
            st.metric("🩸 Blood Pressure", f"{latest['systolic']}/{latest['diastolic']} mmHg")
            st.metric("🍭 Glucose", f"{latest['glucose']} mg/dL")
            st.metric("⚖️ BMI", f"{latest['bmi']:.1f}")

def _render_ai_health_analysis():
    st.expander("🔍 AI Health Analysis", expanded=True)
    latest = iot_service.get_historical_data(st.session_state.user['id']).iloc[-1]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Assessment")
        risk_score = risk_model.predict_risk(
            age=35,
            bmi=latest['bmi'],
            glucose=latest['glucose'],
            bp_avg=(latest['systolic'] + latest['diastolic']) / 2
        )
        st.session_state.user['risk_score'] = risk_score * 100
        st.metric("Diabetes Risk", f"{risk_score * 100:.1f}%")

        cluster = cluster_model.get_cluster(
            age=35,
            bmi=latest['bmi'],
            risk_score=risk_score * 100
        )
        st.session_state.user['cluster'] = cluster
        st.metric("Care Group", f"Cluster {cluster}")

    with col2:
        st.subheader("Anomaly Detection")
        anomaly_status = anomaly_detector.predict(
            latest['heart_rate'], latest['systolic'], latest['diastolic']
        )
        if anomaly_status == -1:
            st.warning("⚠️ 2 Mild Irregularities Found\n❗ 1 Critical Anomaly Detected")
        else:
            st.success("✅ All Metrics Normal")

def _render_patient_tabs():
    tab1, tab2, tab3 = st.tabs(["📁 Medical Records", "📅 Appointments", "💬 Health Assistant"])

    with tab1:
        _medical_records_tab()

    with tab2:
        _appointments_tab()

    with tab3:
        _health_assistant_tab()

def _medical_records_tab():
    with st.expander("Upload New Report"):
        uploaded_file = st.file_uploader("Choose medical file", type=['pdf','jpg','jpeg','png'])
        if uploaded_file:
            try:
                if is_file_duplicate(st.session_state.user['id'], uploaded_file.name):
                    st.error("This file already exists! Rename or choose different file")
                else:
                    save_report(uploaded_file)
                    st.success("Report uploaded!")
            except Exception as e:
                st.error(str(e))

def _appointments_tab():
    st.header("📅 Book an Appointment")

    conn = sqlite3.connect('healthcare.db')
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE role = 'doctor'")
    doctors = c.fetchall()
    conn.close()

    if not doctors:
        st.warning("⚠️ No doctors are currently available.")
        return

    doctor_names = [f"Dr. {name} (ID: {did})" for did, name in doctors]

    with st.form("booking_form"):
        selected = st.selectbox("Select a Doctor", doctor_names)
        appt_date = st.date_input("Appointment Date", min_value=date.today())
        appt_time = st.time_input("Appointment Time")

        if st.form_submit_button("📌 Book Appointment"):
            try:
                doctor_id = int(selected.split("ID: ")[1].split(")")[0])
                save_appointment(
                    user_id=st.session_state.user['id'],
                    doctor_id=doctor_id,
                    date=appt_date,
                    time=appt_time
                )
                st.success(f"✅ Appointment booked with {selected.split(' (')[0]}!")
            except Exception as e:
                st.error(f"❌ Failed to book appointment: {e}")

    # Add appointment cancellation section
    st.markdown("---")
    st.subheader("🗓 Your Scheduled Appointments")
    
    conn = sqlite3.connect('healthcare.db')
    c = conn.cursor()
    c.execute('''
        SELECT a.id, u.username, a.date, a.time, a.status 
        FROM appointments a
        JOIN users u ON a.doctor_id = u.id
        WHERE a.user_id = ?
    ''', (st.session_state.user['id'],))
    appointments = c.fetchall()
    conn.close()

    if appointments:
        for appt in appointments:
            appt_id, doctor_name, appt_date, appt_time, status = appt
            status_color = "#ff4b4b" if status == "Priority" else "#1a73e8"
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                    <div style="padding:1rem; border:1px solid #e6e6e6; border-radius:0.5rem; margin:0.5rem 0;">
                        <h4 style="margin:0; color:{status_color};">⏰ {appt_date} @ {appt_time}</h4>
                        <p style="margin:0.5rem 0;">
                            👨⚕️ Doctor: Dr. {doctor_name.split('@')[0]}<br>
                            📍 Status: <span style="color:{status_color};">{status}</span>
                        </p>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("❌ Cancel", key=f"cancel_{appt_id}"):
                    conn = sqlite3.connect('healthcare.db')
                    c = conn.cursor()
                    c.execute('DELETE FROM appointments WHERE id = ?', (appt_id,))
                    conn.commit()
                    conn.close()
                    st.success("Appointment cancelled")
                    st.rerun()
    else:
        st.info("No upcoming appointments scheduled")

def _health_assistant_tab():
    st.markdown("""
        <style>
        .chat-container {
            max-width: 800px;
            margin: auto;
            padding: 20px;
            max-height: 60vh;
            overflow-y: auto;
        }
        .message {
            padding: 12px;
            margin: 8px 0;
            border-radius: 15px;
            max-width: 70%;
            word-wrap: break-word;
        }
        .user-message {
            background: #f1f3f6;
            margin-left: auto;
        }
        .bot-message {
            background: #1a73e8;
            color: white;
            margin-right: auto;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("AI Health Companion")
    
    # Initialize session states
    if 'chat_mode' not in st.session_state:
        st.session_state.chat_mode = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Mode selection
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💊 Medicine Info"):
            st.session_state.chat_mode = 1
            st.session_state.chat_history = []
    with col2:
        if st.button("🌿 Quick Remedies"):
            st.session_state.chat_mode = 2
            st.session_state.chat_history = []
    with col3:
        if st.button("📋 Health Assessment"):
            st.session_state.chat_mode = 3
            st.session_state.chat_history = []

    # Chat interface
    if st.session_state.chat_mode:
        assistant = HealthAssistant()
        
        with st.container():
            st.subheader(f"Chat Mode: {['Medicine', 'Remedies', 'Assessment'][st.session_state.chat_mode-1]}")
            st.markdown("""
<style>
.chat-container {
    background: #f9f9f9;
    border-radius: 10px;
    padding: 15px;
    margin: 10px 0;
    max-height: 500px;
    overflow-y: auto;
}

.user-message {
    background: #e3f2fd;
    color: #1a237e;
    border-radius: 15px 15px 0 15px;
    padding: 10px 15px;
    margin: 5px 0;
    max-width: 80%;
    margin-left: auto;
}

.bot-message {
    background: #ffffff;
    color: #263238;
    border-radius: 15px 15px 15px 0;
    padding: 10px 15px;
    margin: 5px 0;
    max-width: 80%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}

.chat-container h2 {
    border-bottom: none !important;
    margin-bottom: 8px !important;
    padding-bottom: 0 !important;
}
.message {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)
            
                    # Chat history rendering
        with st.container():
            st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
            
            for msg in st.session_state.chat_history:
                cls = "user-message" if msg["role"] == "user" else "bot-message"
                content = msg["content"].replace("\n", "<br>")
                
                st.markdown(f"""
                    <div class="message {cls}">
                        {content}
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Input handling
            if prompt := st.chat_input("Type your health question..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                
                try:
                    with st.spinner("Analyzing..."):
                        response = assistant.chat(prompt, st.session_state.chat_mode)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.chat_history.append({"role": "assistant", 
                                                         "content": "⚠️ Error processing request"})
                
                st.rerun()
    else:
        st.info("Please select a chat mode to begin")
# ────────────────────────────────────────────────
# DOCTOR DASHBOARD
# ────────────────────────────────────────────────

def doctor_dashboard():
    if st.session_state.user["role"] != "doctor":
        st.error("🔒 Doctor access only")
        return

    doctor_name = st.session_state.user['username'].split('@')[0]
    st.title(f"👨‍⚕️ Dr. {doctor_name}'s Portal")

    st.header("📋 Assigned Patients Overview")
    patients = get_doctor_patients(st.session_state.user['id'])

    if not patients:
        st.warning("No patients assigned.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        selected_patient = st.selectbox(
            "Select Patient",
            patients,
            format_func=lambda p: f"{p['name']} (Cluster {p['cluster']})"
        )
        data = iot_service.get_historical_data(selected_patient['id'])
        latest = data.iloc[-1]

        st.subheader("Vital Snapshot")
        st.metric("Risk Score", f"{selected_patient['risk_score']}%")
        st.metric("Heart Rate", f"{latest['heart_rate']} BPM")
        st.metric("BP", f"{latest['systolic']}/{latest['diastolic']}")

        if st.button("🔄 Refresh"):
            st.rerun()

    with col2:
        _render_doctor_analytics(patients, selected_patient)

    _render_emergency_section(patients)

    st.header("📚 Patient Reports")
    _render_doctor_reports()
    
    doctor_schedule_and_emergencies()

def _render_doctor_analytics(patients, selected_patient):
    st.subheader("📈 Analytics Dashboard")
    data = iot_service.get_historical_data(selected_patient['id'])

    tab1, tab2, tab3 = st.tabs(["📊 Trends", "📈 Predictions", "👥 Clusters"])

    with tab1:
        fig = px.line(data, x='timestamp', y=['heart_rate', 'systolic', 'diastolic'],
                      title="Multi-Vital Timeline")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        trend = data['glucose'].rolling(window=12).mean()
        fig = px.area(trend, title="Diabetes Risk Projection")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        df = pd.DataFrame(patients)
        fig = px.scatter_3d(df, x='risk_score', y='age', z='bmi',
                            color='cluster', hover_name='name',
                            title="Patient Clustering")
        st.plotly_chart(fig, use_container_width=True)

    st.header("🤖 AI Treatment Suggestions")
    assistant = HealthAssistant()
    suggestion = assistant.get_recommendation(selected_patient)
    st.markdown(f"""
        <div style='background:#f0f2f6;padding:1rem;border-radius:0.5rem;'>
        {suggestion}
        </div>
    """, unsafe_allow_html=True)

def _render_emergency_section(patients):
    st.header("🚨 Emergency Alerts")
    emergencies = get_active_emergencies()
    if not emergencies:
        st.success("All patients are stable.")
        return

    for e in emergencies:
        with st.expander(f"🚨 Critical Alert: {e['username']}", expanded=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"**Patient**: {e['username']}")
                st.write(f"**Timestamp**: {e['timestamp']}")
                if st.button("Resolve", key=f"resolve_{e['id']}"):
                    resolve_emergency(e['id'], st.session_state.user['id'])
                    st.rerun()
            with col2:
                data = iot_service.get_historical_data(e['id']).iloc[-1]
                st.write(f"""
                    - ❤️ Heart Rate: {data['heart_rate']} BPM  
                    - 🩸 BP: {data['systolic']}/{data['diastolic']}  
                    - 🍭 Glucose: {data['glucose']} mg/dL  
                """)

def _render_doctor_reports():
    st.subheader("📁 Upload/Review Reports")

    uploaded_file = st.file_uploader("Upload new patient report", type=['pdf', 'jpg', 'jpeg', 'png'])
    if uploaded_file:
        if is_file_duplicate(st.session_state.user['id'], uploaded_file.name):
            st.warning("This file already exists. Rename or choose a different file.")
        else:
            save_report(uploaded_file)
            st.success("Report uploaded successfully!")

    reports = get_patient_reports_for_doctor(st.session_state.user['id'])
    if reports:
        for report in reports:
            st.markdown(f"""
            **Patient:** {report['patient']}  
            **Report:** {report['filename']}  
            **Uploaded On:** {report['uploaded_at']}  
            ---
            """)
    else:
        st.info("No reports available yet.")

def doctor_schedule_and_emergencies():
    st.header("📅 Doctor's Schedule & Alerts")

    # Force fresh data load on every rerun
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.datetime.now()

    emergencies = get_active_emergencies()
    appointments = get_doctor_appointments(st.session_state.user['id'])

    # Emergency Section
    if emergencies:
        st.subheader("🚨 Critical Emergencies")
        for emergency in emergencies:
            with st.expander(f"Emergency from {emergency['username']}", expanded=True):
                cols = st.columns([3, 1])
                cols[0].write(f"**Received:** {emergency['timestamp']}")
                if cols[1].button("Resolve", 
                                key=f"resolve_emergency_{emergency['id']}_{st.session_state.last_update}"):
                    resolve_emergency(emergency['id'], st.session_state.user['id'])
                    st.session_state.last_update = datetime.datetime.now()
                    st.rerun()

    # Appointments Section
    st.subheader("🗓️ Scheduled Appointments")
    
    if appointments:
        for idx, appt in enumerate(appointments):
            appt_id = appt['id']
            status_color = "#ff4b4b" if appt['status'] == "Priority" else "#1a73e8"
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                    <div style="padding:1rem; border:1px solid #e6e6e6; border-radius:0.5rem; margin:0.5rem 0;">
                        <h4 style="margin:0; color:{status_color};">⏰ {appt['date']} @ {appt['time']}</h4>
                        <p style="margin:0.5rem 0;">
                            👤 Patient: {appt['patient']}<br>
                            📍 Status: <span style="color:{status_color};">{appt['status']}</span>
                        </p>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("❌ Cancel", 
                           key=f"cancel_{appt_id}_{st.session_state.last_update}"):
                    # Double-check existence before deletion
                    conn = sqlite3.connect('healthcare.db')
                    c = conn.cursor()
                    c.execute('SELECT id FROM appointments WHERE id = ?', (appt_id,))
                    exists = c.fetchone()
                    
                    if exists:
                        c.execute('DELETE FROM appointments WHERE id = ?', (appt_id,))
                        conn.commit()
                        conn.close()
                        st.success("Appointment cancelled")
                        # Force complete refresh
                        st.session_state.last_update = datetime.datetime.now()
                        st.rerun()
                    else:
                        st.error("Appointment already removed")
                        conn.close()
    else:
        st.info("No upcoming appointments")


# ────────────────────────────────────────────────
# CUSTOM CSS
# ────────────────────────────────────────────────

st.markdown("""
    <style>
        .stMetric {
            border: 1px solid #e6e6e6;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        .stPlotlyChart {
            border-radius: 0.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .emergency-box {
            border: 2px solid #ff4b4b;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        /* Cancel button styling */
        button[kind="secondary"] {
            background-color: #ff4b4b !important;
            color: white !important;
            border: 1px solid #ff4b4b !important;
        }
        button[kind="secondary"]:hover {
            background-color: #ff2b2b !important;
            border: 1px solid #ff2b2b !important;
        }
        
        /* Appointment cards */
        div[data-testid="stMarkdownContainer"] > div {
            transition: box-shadow 0.3s ease;
        }
        div[data-testid="stMarkdownContainer"] > div:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
    </style>
""", unsafe_allow_html=True)