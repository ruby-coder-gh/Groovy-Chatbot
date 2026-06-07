"""
Database layer for ISO 27001 chatbot.

Supports TWO backends automatically:
  - SQLite   (local development) — no DATABASE_URL set
  - PostgreSQL (Vercel/production) — set DATABASE_URL env var

All public functions have identical signatures regardless of backend.
"""

import json
import os
import sys

# ──────────────────────────────────────────────
# Backend selection
# ──────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # ══════════════════════════════════════════
    # POSTGRESQL BACKEND
    # ══════════════════════════════════════════
    import psycopg2
    import psycopg2.extras
    from psycopg2 import sql as psql

    # Fix: Serverless (Vercel) needs the Supabase pooler on port 6543 + IPv4
    _db_url = DATABASE_URL
    # Auto-switch to pooler port 6543 for serverless environments
    if ":5432/" in _db_url and os.environ.get("VERCEL", "").lower() == "true":
        _db_url = _db_url.replace(":5432/", ":6543/")
    # Append connect_timeout if not present
    if "connect_timeout" not in _db_url:
        separator = "&" if "?" in _db_url else "?"
        _db_url += f"{separator}connect_timeout=10"

    def get_connection():
        """Return a PostgreSQL connection (dict-like rows)."""
        conn = psycopg2.connect(_db_url, sslmode="require")
        conn.autocommit = False
        return conn

    def _fetchone_dict(conn, query, params=()):
        """Execute query, return one row as dict or None."""
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def _fetchall_dicts(conn, query, params=()):
        """Execute query, return all rows as list of dicts."""
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def _execute(conn, query, params=()):
        """Execute a write query, return cursor."""
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur

    # ── Schema ───────────────────────────────
    SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            company_name TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            current_question_index INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS answers (
            id SERIAL PRIMARY KEY,
            session_id TEXT REFERENCES sessions(id),
            question_id TEXT,
            question_text TEXT,
            user_answer TEXT,
            matched_control_ids TEXT,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            company_name TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS remediation_plans (
            session_id TEXT NOT NULL,
            control_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            description TEXT NOT NULL,
            effort_hours INTEGER NOT NULL DEFAULT 0,
            owner TEXT NOT NULL DEFAULT '',
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, control_id)
        );

        CREATE TABLE IF NOT EXISTS policy_templates (
            session_id TEXT NOT NULL,
            control_id TEXT NOT NULL,
            title TEXT NOT NULL,
            clause TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, control_id)
        );
    """

    # ── Public API ───────────────────────────

    # ── Fallback flag ─────────────────────────
    _pg_healthy = True

    def init_db():
        """Create tables if they don't exist. Graceful on connection failure."""
        global _pg_healthy
        conn = None
        try:
            conn = get_connection()
        except Exception as e:
            print(f"⚠️ PostgreSQL connection failed: {e}")
            _pg_healthy = False
            return

        try:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            conn.commit()
            _pg_healthy = True
        except Exception as e:
            print(f"⚠️ PostgreSQL init failed: {e}")
            _pg_healthy = False
        finally:
            if conn:
                conn.close()

    def _require_pg():
        """Check that PostgreSQL is healthy before every operation."""
        if not _pg_healthy:
            raise RuntimeError(
                "Database unavailable. Please check your DATABASE_URL "
                "environment variable and ensure Supabase is running."
            )

    def create_session(session_id, company_name):
        conn = get_connection()
        try:
            _execute(conn,
                "INSERT INTO sessions (id, company_name) VALUES (%s, %s)",
                (session_id, company_name),
            )
            conn.commit()
        finally:
            conn.close()

    def get_session(session_id):
        conn = get_connection()
        try:
            row = _fetchone_dict(conn, "SELECT * FROM sessions WHERE id = %s", (session_id,))
            return row
        finally:
            conn.close()

    def update_session_question(session_id, question_index):
        conn = get_connection()
        try:
            _execute(conn,
                "UPDATE sessions SET current_question_index = %s WHERE id = %s",
                (question_index, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def complete_session(session_id):
        conn = get_connection()
        try:
            _execute(conn,
                "UPDATE sessions SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = %s",
                (session_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def save_answer(session_id, question_id, question_text, user_answer, matched_control_ids):
        conn = get_connection()
        try:
            _execute(conn,
                "INSERT INTO answers (session_id, question_id, question_text, user_answer, matched_control_ids) VALUES (%s, %s, %s, %s, %s)",
                (session_id, question_id, question_text, user_answer, json.dumps(matched_control_ids)),
            )
            conn.commit()
        finally:
            conn.close()

    def get_answers(session_id):
        conn = get_connection()
        try:
            return _fetchall_dicts(conn,
                "SELECT * FROM answers WHERE session_id = %s ORDER BY id ASC",
                (session_id,),
            )
        finally:
            conn.close()

    def save_domain_score(session_id, domain_name, score, covered_questions, total_questions, gap_control_ids):
        conn = get_connection()
        try:
            _execute(conn,
                """INSERT INTO domain_scores (session_id, domain_name, score, covered_questions, total_questions, gap_control_ids)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (session_id, domain_name)
                   DO UPDATE SET score = EXCLUDED.score,
                                 covered_questions = EXCLUDED.covered_questions,
                                 total_questions = EXCLUDED.total_questions,
                                 gap_control_ids = EXCLUDED.gap_control_ids""",
                (session_id, domain_name, score, covered_questions, total_questions, json.dumps(gap_control_ids)),
            )
            conn.commit()
        finally:
            conn.close()

    def get_domain_scores(session_id):
        conn = get_connection()
        try:
            return _fetchall_dicts(conn,
                "SELECT * FROM domain_scores WHERE session_id = %s", (session_id,),
            )
        finally:
            conn.close()

    def save_priority_matrix(session_id, fix_now, plan_for_it, quick_wins, deprioritize):
        conn = get_connection()
        try:
            _execute(conn,
                """INSERT INTO priority_matrix (session_id, fix_now, plan_for_it, quick_wins, deprioritize)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (session_id)
                   DO UPDATE SET fix_now = EXCLUDED.fix_now,
                                 plan_for_it = EXCLUDED.plan_for_it,
                                 quick_wins = EXCLUDED.quick_wins,
                                 deprioritize = EXCLUDED.deprioritize""",
                (session_id, json.dumps(fix_now), json.dumps(plan_for_it),
                 json.dumps(quick_wins), json.dumps(deprioritize)),
            )
            conn.commit()
        finally:
            conn.close()

    def get_priority_matrix(session_id):
        conn = get_connection()
        try:
            row = _fetchone_dict(conn,
                "SELECT * FROM priority_matrix WHERE session_id = %s", (session_id,),
            )
            if row:
                row["fix_now"] = json.loads(row["fix_now"])
                row["plan_for_it"] = json.loads(row["plan_for_it"])
                row["quick_wins"] = json.loads(row["quick_wins"])
                row["deprioritize"] = json.loads(row["deprioritize"])
            return row
        finally:
            conn.close()

    def create_user(email, password_hash, company_name=""):
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO users (email, password_hash, company_name) VALUES (%s, %s, %s) RETURNING id",
                    (email, password_hash, company_name),
                )
                user_id = cur.fetchone()["id"]
            conn.commit()
            return get_user_by_id(user_id)
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            return None
        finally:
            conn.close()

    def get_user_by_email(email):
        conn = get_connection()
        try:
            return _fetchone_dict(conn,
                "SELECT * FROM users WHERE email = %s", (email,),
            )
        finally:
            conn.close()

    def get_user_by_id(user_id):
        conn = get_connection()
        try:
            return _fetchone_dict(conn,
                "SELECT * FROM users WHERE id = %s", (user_id,),
            )
        finally:
            conn.close()

    def save_remediation_plan(session_id, control_id, domain, description, effort_hours, owner):
        conn = get_connection()
        try:
            _execute(conn,
                """INSERT INTO remediation_plans (session_id, control_id, domain, description, effort_hours, owner)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (session_id, control_id)
                   DO UPDATE SET domain = EXCLUDED.domain,
                                 description = EXCLUDED.description,
                                 effort_hours = EXCLUDED.effort_hours,
                                 owner = EXCLUDED.owner""",
                (session_id, control_id, domain, description, effort_hours, owner),
            )
            conn.commit()
        finally:
            conn.close()

    def get_remediation_plans(session_id):
        conn = get_connection()
        try:
            return _fetchall_dicts(conn,
                "SELECT * FROM remediation_plans WHERE session_id = %s ORDER BY domain, control_id",
                (session_id,),
            )
        finally:
            conn.close()

    def delete_remediation_plans(session_id):
        conn = get_connection()
        try:
            _execute(conn, "DELETE FROM remediation_plans WHERE session_id = %s", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def save_policy_template(session_id, control_id, title, clause):
        conn = get_connection()
        try:
            _execute(conn,
                """INSERT INTO policy_templates (session_id, control_id, title, clause)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (session_id, control_id)
                   DO UPDATE SET title = EXCLUDED.title, clause = EXCLUDED.clause""",
                (session_id, control_id, title, clause),
            )
            conn.commit()
        finally:
            conn.close()

    def get_policy_templates(session_id):
        conn = get_connection()
        try:
            return _fetchall_dicts(conn,
                "SELECT * FROM policy_templates WHERE session_id = %s ORDER BY control_id",
                (session_id,),
            )
        finally:
            conn.close()

    def delete_policy_templates(session_id):
        conn = get_connection()
        try:
            _execute(conn, "DELETE FROM policy_templates WHERE session_id = %s", (session_id,))
            conn.commit()
        finally:
            conn.close()

else:
    # ══════════════════════════════════════════
    # SQLITE BACKEND (local development)
    # ══════════════════════════════════════════
    import sqlite3

    # Import the canonical DB_PATH from config, with a fallback for standalone use
    try:
        from config import DB_PATH
    except ImportError:
        _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DB_PATH = os.environ.get("DB_PATH", os.path.join(_BASE, "iso27001.db"))

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

            CREATE TABLE IF NOT EXISTS remediation_plans (
                session_id TEXT NOT NULL,
                control_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                description TEXT NOT NULL,
                effort_hours INTEGER NOT NULL DEFAULT 0,
                owner TEXT NOT NULL DEFAULT '',
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, control_id)
            );

            CREATE TABLE IF NOT EXISTS policy_templates (
                session_id TEXT NOT NULL,
                control_id TEXT NOT NULL,
                title TEXT NOT NULL,
                clause TEXT NOT NULL,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, control_id)
            );
        """)
        conn.commit()
        conn.close()

    def create_session(session_id, company_name):
        conn = get_connection()
        conn.execute(
            "INSERT INTO sessions (id, company_name) VALUES (?, ?)",
            (session_id, company_name),
        )
        conn.commit()
        conn.close()

    def get_session(session_id):
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def update_session_question(session_id, question_index):
        conn = get_connection()
        conn.execute(
            "UPDATE sessions SET current_question_index = ? WHERE id = ?",
            (question_index, session_id),
        )
        conn.commit()
        conn.close()

    def complete_session(session_id):
        conn = get_connection()
        conn.execute(
            "UPDATE sessions SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )
        conn.commit()
        conn.close()

    def save_answer(session_id, question_id, question_text, user_answer, matched_control_ids):
        conn = get_connection()
        conn.execute(
            "INSERT INTO answers (session_id, question_id, question_text, user_answer, matched_control_ids) VALUES (?, ?, ?, ?, ?)",
            (session_id, question_id, question_text, user_answer, json.dumps(matched_control_ids)),
        )
        conn.commit()
        conn.close()

    def get_answers(session_id):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM answers WHERE session_id = ? ORDER BY id ASC", (session_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_domain_score(session_id, domain_name, score, covered_questions, total_questions, gap_control_ids):
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
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM domain_scores WHERE session_id = ?", (session_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_priority_matrix(session_id, fix_now, plan_for_it, quick_wins, deprioritize):
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

    def create_user(email, password_hash, company_name=""):
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
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(user_id):
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def save_remediation_plan(session_id, control_id, domain, description, effort_hours, owner):
        conn = get_connection()
        conn.execute(
            """INSERT OR REPLACE INTO remediation_plans
               (session_id, control_id, domain, description, effort_hours, owner)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, control_id, domain, description, effort_hours, owner),
        )
        conn.commit()
        conn.close()

    def get_remediation_plans(session_id):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM remediation_plans WHERE session_id = ? ORDER BY domain, control_id",
            (session_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_remediation_plans(session_id):
        conn = get_connection()
        conn.execute("DELETE FROM remediation_plans WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def save_policy_template(session_id, control_id, title, clause):
        conn = get_connection()
        conn.execute(
            """INSERT OR REPLACE INTO policy_templates
               (session_id, control_id, title, clause)
               VALUES (?, ?, ?, ?)""",
            (session_id, control_id, title, clause),
        )
        conn.commit()
        conn.close()

    def get_policy_templates(session_id):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM policy_templates WHERE session_id = ? ORDER BY control_id",
            (session_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_policy_templates(session_id):
        conn = get_connection()
        conn.execute("DELETE FROM policy_templates WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
