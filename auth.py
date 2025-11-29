import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
import streamlit as st
from config import DATABASE, UPLOAD_FOLDER

# ───────────────────────────────────────
# DATABASE SETUP
# ───────────────────────────────────────

def create_connection():
    return sqlite3.connect(DATABASE)

def init_db():
    conn = create_connection()
    c = conn.cursor()

    # Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            age INTEGER NOT NULL DEFAULT 30,
            bmi REAL NOT NULL DEFAULT 25.0,
            risk_score REAL DEFAULT 0,
            cluster INTEGER DEFAULT 0,
            doctor_id INTEGER,
            last_checked DATETIME,
            FOREIGN KEY(doctor_id) REFERENCES users(id)
        )
    ''')

    # Health data
    c.execute('''
        CREATE TABLE IF NOT EXISTS health_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            heart_rate REAL,
            systolic INTEGER,
            diastolic INTEGER,
            glucose REAL,
            bmi REAL,
            timestamp DATETIME,
            is_anomaly INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Appointments
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'Scheduled',
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(doctor_id) REFERENCES users(id)
        )
    ''')

    # Medical reports
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            uploaded_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Emergency events
    c.execute('''
        CREATE TABLE IF NOT EXISTS emergencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME,
            status TEXT DEFAULT 'Pending',
            resolved_by INTEGER,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(resolved_by) REFERENCES users(id)
        )
    ''')

    c.execute("CREATE INDEX IF NOT EXISTS idx_user_role ON users(role)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_emergency_status ON emergencies(status)")

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn.commit()
    conn.close()

# ───────────────────────────────────────
# AUTHENTICATION
# ───────────────────────────────────────

def authenticate(username, password):
    conn = create_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and user[2] == password:
            return {
                'id': user[0],
                'username': user[1],
                'role': user[3],
                'age': user[4],
                'bmi': user[5],
                'risk_score': user[6],
                'cluster': user[7],
                'doctor_id': user[8]
            }
    except Exception as e:
        print(f"[Auth Error] {e}")
    finally:
        conn.close()
    return None

def create_account(username, password, role, age=30, bmi=25.0, doctor_id=None):
    try:
        conn = create_connection()
        conn.execute('''
            INSERT INTO users (username, password, role, age, bmi, doctor_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password, role, age, bmi, doctor_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"[Account Creation Error] {e}")
        return False
    finally:
        conn.close()

# ───────────────────────────────────────
# PATIENT / DOCTOR UTILITIES
# ───────────────────────────────────────

def get_doctor_patients(doctor_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, username, age, bmi, risk_score, cluster
        FROM users
        WHERE role = 'patient' AND doctor_id = ?
    ''', (doctor_id,))
    rows = c.fetchall()
    conn.close()
    return [{
        'id': r[0],
        'name': r[1],
        'age': r[2],
        'bmi': r[3],
        'risk_score': r[4],
        'cluster': r[5]
    } for r in rows]

# ───────────────────────────────────────
# EMERGENCY MANAGEMENT
# ───────────────────────────────────────

def save_emergency(user_id):
    conn = create_connection()
    conn.execute('''
        INSERT INTO emergencies (user_id, timestamp)
        VALUES (?, ?)
    ''', (user_id, datetime.now()))
    conn.commit()
    conn.close()

def get_active_emergencies():
    conn = create_connection()
    c = conn.cursor()
    c.execute('''
        SELECT e.id, u.username, e.timestamp
        FROM emergencies e
        JOIN users u ON e.user_id = u.id
        WHERE e.status = 'Pending'
    ''')
    results = c.fetchall()
    conn.close()
    return [{
        'id': row[0],
        'username': row[1],
        'timestamp': row[2]
    } for row in results]

def resolve_emergency(emergency_id, doctor_id, notes=""):
    conn = create_connection()
    conn.execute('''
        UPDATE emergencies
        SET status = 'Resolved',
            resolved_by = ?,
            notes = ?,
            timestamp = ?
        WHERE id = ?
    ''', (doctor_id, notes, datetime.now(), emergency_id))
    conn.commit()
    conn.close()

# ───────────────────────────────────────
# FILE UPLOADS & REPORTS
# ───────────────────────────────────────

def save_report(file):
    user_id = st.session_state.user['id']
    filename = secure_filename(file.name)
    if is_file_duplicate(user_id, filename):
        raise ValueError(f"File '{filename}' already exists!")
    
    user_folder = os.path.join(UPLOAD_FOLDER, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    file_path = os.path.join(user_folder, filename)
    with open(file_path, "wb") as f:
        f.write(file.getbuffer())

    conn = create_connection()
    conn.execute('''
        INSERT INTO reports (user_id, filename, filepath, uploaded_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, filename, file_path, datetime.now()))
    conn.commit()
    conn.close()

def get_user_reports(user_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute("SELECT filename, uploaded_at FROM reports WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return [{'filename': row[0], 'uploaded_at': row[1]} for row in results]

def get_patient_reports_for_doctor(doctor_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute('''
        SELECT r.filename, r.uploaded_at, u.username 
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE u.doctor_id = ?
    ''', (doctor_id,))
    reports = [{
        'filename': row[0],
        'uploaded_at': row[1],
        'patient': row[2]
    } for row in c.fetchall()]
    conn.close()
    return reports

def is_file_duplicate(user_id, filename):
    conn = create_connection()
    c = conn.cursor()
    c.execute('''
        SELECT 1 FROM reports 
        WHERE user_id = ? AND filename = ?
    ''', (user_id, filename))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# ───────────────────────────────────────
# APPOINTMENT SCHEDULING
# ───────────────────────────────────────

def save_appointment(user_id, doctor_id, date, time):
    conn = sqlite3.connect("healthcare.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO appointments (user_id, doctor_id, date, time, status)
        VALUES (?, ?, ?, ?, 'Scheduled')
    """, (user_id, doctor_id, str(date), str(time)))
    conn.commit()
    conn.close()


def get_doctor_appointments(doctor_id):
    """Always returns fresh data from database"""
    conn = sqlite3.connect('healthcare.db')
    c = conn.cursor()
    c.execute('''
        SELECT a.id, u.username, a.date, a.time, a.status 
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        WHERE a.doctor_id = ?
        ORDER BY a.date DESC, a.time DESC
    ''', (doctor_id,))
    appointments = [{
        'id': row[0],
        'patient': row[1],
        'date': row[2],
        'time': row[3],
        'status': row[4]
    } for row in c.fetchall()]
    conn.close()
    return appointments
