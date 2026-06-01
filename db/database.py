"""
SQLite database layer for ISO 27001 chatbot.
Handles sessions, answers, and domain scores.
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "iso27001.db")


def get_connection():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            company_name TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            current_question_index INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            question_id TEXT,
            question_text TEXT,
            user_answer TEXT,
            matched_control_ids TEXT,
            answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS domain_scores (
            session_id TEXT,
            domain_name TEXT,
            score INTEGER,
            covered_questions INTEGER,
            total_questions INTEGER,
            gap_control_ids TEXT,
            PRIMARY KEY (session_id, domain_name)
        );

        CREATE TABLE IF NOT EXISTS priority_matrix (
            session_id TEXT PRIMARY KEY,
            fix_now TEXT,
            plan_for_it TEXT,
            quick_wins TEXT,
            deprioritize TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            company_name TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def create_session(session_id, company_name):
    """Create a new session and return its ID."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (id, company_name) VALUES (?, ?)",
        (session_id, company_name),
    )
    conn.commit()
    conn.close()


def get_session(session_id):
    """Get session by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def update_session_question(session_id, question_index):
    """Update the current question index."""
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET current_question_index = ? WHERE id = ?",
        (question_index, session_id),
    )
    conn.commit()
    conn.close()


def complete_session(session_id):
    """Mark session as completed."""
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def save_answer(session_id, question_id, question_text, user_answer, matched_control_ids):
    """Save an answer record."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO answers (session_id, question_id, question_text, user_answer, matched_control_ids) VALUES (?, ?, ?, ?, ?)",
        (session_id, question_id, question_text, user_answer, json.dumps(matched_control_ids)),
    )
    conn.commit()
    conn.close()


def get_answers(session_id):
    """Get all answers for a session."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM answers WHERE session_id = ? ORDER BY id ASC", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_domain_score(session_id, domain_name, score, covered_questions, total_questions, gap_control_ids):
    """Save or update a domain score."""
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO domain_scores
           (session_id, domain_name, score, covered_questions, total_questions, gap_control_ids)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, domain_name, score, covered_questions, total_questions, json.dumps(gap_control_ids)),
    )
    conn.commit()
    conn.close()


def get_domain_scores(session_id):
    """Get all domain scores for a session."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM domain_scores WHERE session_id = ?", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_priority_matrix(session_id, fix_now, plan_for_it, quick_wins, deprioritize):
    """Save or update the priority matrix for a session."""
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO priority_matrix
           (session_id, fix_now, plan_for_it, quick_wins, deprioritize)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, json.dumps(fix_now), json.dumps(plan_for_it),
         json.dumps(quick_wins), json.dumps(deprioritize)),
    )
    conn.commit()
    conn.close()


def get_priority_matrix(session_id):
    """Get the priority matrix for a session."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM priority_matrix WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["fix_now"] = json.loads(result["fix_now"])
        result["plan_for_it"] = json.loads(result["plan_for_it"])
        result["quick_wins"] = json.loads(result["quick_wins"])
        result["deprioritize"] = json.loads(result["deprioritize"])
        return result
    return None


# ============================================================
# User Authentication
# ============================================================

def create_user(email, password_hash, company_name=""):
    """Create a new user. Returns the user dict or None if email exists."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, company_name) VALUES (?, ?, ?)",
            (email, password_hash, company_name),
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        conn.close()
        return None


def get_user_by_email(email):
    """Get user by email."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    """Get user by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
