import sqlite3
from flask import g
import os

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'dr_detection.db')

def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'doctor',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            patient_name TEXT NOT NULL,
            patient_email TEXT,
            patient_age TEXT,
            patient_id TEXT,
            image_path TEXT NOT NULL,
            severity_level INTEGER NOT NULL,
            severity_label TEXT NOT NULL,
            confidence REAL NOT NULL,
            model_predictions TEXT,
            recommendations TEXT,
            gradcam_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES users(id)
        );
    ''')

    columns = {row[1] for row in db.execute("PRAGMA table_info(scans)").fetchall()}
    if 'gradcam_path' not in columns:
        db.execute('ALTER TABLE scans ADD COLUMN gradcam_path TEXT')

    db.commit()

    # Ensure backward-compatible patient columns exist
    existing = {row[1] for row in db.execute("PRAGMA table_info(scans)").fetchall()}
    to_add = []
    if 'patient_gender' not in existing:
        to_add.append("ALTER TABLE scans ADD COLUMN patient_gender TEXT")
    if 'patient_phone' not in existing:
        to_add.append("ALTER TABLE scans ADD COLUMN patient_phone TEXT")
    if 'diabetes_duration' not in existing:
        to_add.append("ALTER TABLE scans ADD COLUMN diabetes_duration TEXT")
    if 'medical_history' not in existing:
        to_add.append("ALTER TABLE scans ADD COLUMN medical_history TEXT")
    if 'eye_side' not in existing:
        to_add.append("ALTER TABLE scans ADD COLUMN eye_side TEXT")
    for stmt in to_add:
        try:
            db.execute(stmt)
        except Exception:
            pass
    db.commit()
