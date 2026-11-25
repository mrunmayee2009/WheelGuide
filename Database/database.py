"""
Database/database.py
---------------------
All SQLite setup and CRUD helper functions for WheelGuide.
sqlite3 is part of Python's standard library — no pip install needed.
"""

import sqlite3
import os
import sys
import hashlib
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't already exist. Call once at app start."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            latitude REAL,
            longitude REAL,
            category TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accessibility_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id INTEGER,
            score REAL,
            reasoning TEXT,
            has_ramp INTEGER,
            has_elevator INTEGER,
            has_accessible_toilet INTEGER,
            scored_at TEXT,
            FOREIGN KEY(place_id) REFERENCES places(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            phone TEXT,
            relation TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sos_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            latitude REAL,
            longitude REAL,
            message TEXT,
            triggered_by TEXT,
            sent_online INTEGER,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS medical_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            original_filename TEXT,
            summary TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(username, password, full_name="", phone="",
                 emergency_contact_name="", emergency_contact_phone=""):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, password_hash, full_name, phone,
                emergency_contact_name, emergency_contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, hash_password(password), full_name, phone,
              emergency_contact_name, emergency_contact_phone,
              datetime.datetime.now().isoformat()))
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def verify_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and row["password_hash"] == hash_password(password):
        return dict(row)
    return None


def save_place_score(name, address, lat, lon, category, score, reasoning,
                      has_ramp, has_elevator, has_toilet):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO places (name, address, latitude, longitude, category)
        VALUES (?, ?, ?, ?, ?)
    """, (name, address, lat, lon, category))
    place_id = cur.lastrowid
    cur.execute("""
        INSERT INTO accessibility_scores
            (place_id, score, reasoning, has_ramp, has_elevator,
             has_accessible_toilet, scored_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (place_id, score, reasoning, int(has_ramp), int(has_elevator),
          int(has_toilet), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return place_id


def log_sos(user_id, lat, lon, message, triggered_by, sent_online):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sos_logs (user_id, latitude, longitude, message,
            triggered_by, sent_online, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, lat, lon, message, triggered_by, int(sent_online),
          datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_emergency_contacts(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM emergency_contacts WHERE user_id = ?", (user_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_emergency_contact(user_id, name, phone, relation=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO emergency_contacts (user_id, name, phone, relation)
        VALUES (?, ?, ?, ?)
    """, (user_id, name, phone, relation))
    conn.commit()
    conn.close()


def save_medical_report(user_id, filename, summary):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO medical_reports (user_id, original_filename, summary, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, filename, summary, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")