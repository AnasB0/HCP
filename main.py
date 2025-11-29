import streamlit as st
import sqlite3
import datetime
import warnings

# Set page config
st.set_page_config(
    page_title="AI Healthcare System",
    layout="wide",
    page_icon="🏥"
)

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Auth imports
from auth import (
    authenticate,
    create_account,
    init_db,
    get_doctor_patients,
    get_active_emergencies
)
from views import patient_dashboard, doctor_dashboard
from config import IOT_CONFIG  # Removed security-related imports

# Cached models
@st.cache_resource
def load_models():
    from models.anomaly_detector import AnomalyDetector
    from models.risk_predictor import RiskPredictor
    return {
        'anomaly': AnomalyDetector(),
        'risk': RiskPredictor()
    }

@st.cache_resource
def get_iot_service():
    from iot_services import IoTDataService
    return IoTDataService()

# Session state init
if 'initialized' not in st.session_state:
    st.session_state.update({
        'models': load_models(),
        'iot_service': get_iot_service(),
        'initialized': True,
        'user': None,
        'iot_data': None,
        'cluster_updates': []
    })
    init_db()

# Styling (security headers removed)
st.markdown("""
    <style>
        .emergency-alert {
            border: 2px solid #ff4b4b;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .metric-card {
            border: 1px solid #e6e6e6;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
        }
    </style>
""", unsafe_allow_html=True)


def handle_login(username, password):
    user = authenticate(username, password)
    if user:
        st.session_state.user = user
        st.session_state.last_activity = datetime.datetime.now()

        if user['role'] == 'patient':
            from models.patient_cluster import PatientCluster
            cluster_model = PatientCluster()
            st.session_state.user['cluster'] = cluster_model.get_cluster(
                age=user['age'],
                bmi=user['bmi'],
                risk_score=user.get('risk_score', 0)
            )
        st.rerun()


def main_sidebar():
    st.sidebar.title("🔐 HealthGate Portal")

    if st.session_state.user:
        _show_logged_in_info()
    else:
        _show_auth_menu()


def _show_logged_in_info():
    user = st.session_state.user
    st.sidebar.subheader(f"Logged in as {user['username']}")
    st.sidebar.markdown(f"**Role**: {user['role'].capitalize()}")

    if user['role'] == 'patient':
        st.sidebar.markdown(f"**Risk Score**: {user.get('risk_score', 0)}%")
        st.sidebar.markdown(f"**Care Cluster**: Group {user.get('cluster', 0)}")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()


def _show_auth_menu():
    menu = st.sidebar.radio("Menu", ["Login", "Register"])

    if menu == "Login":
        _show_login_form()
    elif menu == "Register":
        _show_registration_form()


def _show_login_form():
    with st.sidebar.form("Login Form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")
        if submitted:
            handle_login(username, password)


def _show_registration_form():
    st.sidebar.write("### Create New Account")

    with st.sidebar.form("Registration Form"):
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        role = st.selectbox("Role", ["patient", "doctor"])
        age = st.number_input("Age", min_value=1, max_value=120, value=30)
        bmi = st.number_input("BMI", min_value=10.0, max_value=50.0, value=25.0)

        doctor_id = None
        validation_error = None

        if role == "patient":
            try:
                conn = sqlite3.connect('healthcare.db')
                c = conn.cursor()
                c.execute("SELECT id, username FROM users WHERE role='doctor'")
                doctors = c.fetchall()
                conn.close()

                if not doctors:
                    validation_error = "⚠️ No doctors available. Please ask a doctor to register first."
                else:
                    doctor_names = [f"Dr. {name} (ID: {did})" for did, name in doctors]
                    selected_doctor = st.selectbox("Select Your Doctor", doctor_names)
                    try:
                        doctor_id = int(selected_doctor.split("ID: ")[1].split(")")[0])
                    except (IndexError, ValueError):
                        validation_error = "⚠️ Invalid doctor selection."
            except Exception as e:
                validation_error = f"⚠️ Database error: {str(e)}"

        submitted = st.form_submit_button("Create Account")

        if submitted:
            if not new_user or not new_pass:
                st.error("Username and password are required.")
            elif validation_error:
                st.error(validation_error)
            else:
                success = create_account(new_user, new_pass, role, age, bmi, doctor_id)
                if success:
                    st.success("✅ Account created! Please log in.")
                    st.rerun()
                else:
                    st.error("❌ Registration failed.")


def main_content():
    if not st.session_state.user:
        st.title("AI-Powered Healthcare System")
        st.markdown("""
            <div style="text-align: center; padding: 5rem 0;">
                <h1>🏥 Next-Gen Healthcare Platform</h1>
                <p style="font-size: 1.2rem;">
                    Real-time monitoring • Predictive analytics • AI-powered insights
                </p>
            </div>
        """, unsafe_allow_html=True)
        return

    if (datetime.datetime.now() - st.session_state.last_activity).seconds > 3600:
        st.warning("Session timed out due to inactivity")
        st.session_state.user = None
        st.rerun()

    st.session_state.last_activity = datetime.datetime.now()

    if st.session_state.user['role'] == 'patient':
        patient_dashboard()
    else:
        doctor_dashboard()


if __name__ == "__main__":
    main_sidebar()
    main_content()