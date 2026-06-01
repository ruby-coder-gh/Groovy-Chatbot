"""
Flask application for ISO 27001:2022 Readiness Self-Assessment Chatbot.
Provides 6 API routes for session management, Q&A, reporting, and PDF download.
"""

import os
import uuid
import json
from datetime import datetime

from flask import Flask, request, jsonify, render_template, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash

from config import CONTROL_MAP, PDF_DIR
import google.generativeai as genai
from db.database import (
    init_db, create_session, get_session, update_session_question,
    complete_session, save_answer, get_answers, save_domain_score,
    get_domain_scores, save_priority_matrix, get_priority_matrix,
    create_user, get_user_by_email, get_user_by_id,
)
from modules.questionnaire import (
    get_question, get_all_domains, get_total_questions,
    DOMAIN_QUESTIONS,
)
from modules.llm_mapper import map_answer_to_controls
from modules.scorer import calculate_domain_scores, get_overall_score
from modules.pdf_generator import generate_gap_report

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "iso27001-chatbot-dev-key-change-in-production")

# Ensure DB tables exist on startup
init_db()


# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    """Serve the chat UI."""
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def api_start():
    """
    Create a new session.
    Request: {"company_name": "Acme Corp"}
    Response: {"session_id": "abc123", "first_question": {...}, "total_questions": 30}
    """
    data = request.get_json() or {}
    company_name = data.get("company_name", "Anonymous")

    session_id = str(uuid.uuid4())[:12]
    create_session(session_id, company_name)

    first_q = get_question(0)
    if not first_q:
        return jsonify({"error": "No questions available"}), 500

    return jsonify({
        "session_id": session_id,
        "question": first_q,
        "question_index": 0,
        "total_questions": get_total_questions(),
        "progress": f"1/{get_total_questions()}",
    })


@app.route("/api/answer", methods=["POST"])
def api_answer():
    """
    Submit answer for the current question.
    Request: {"session_id": "abc123", "answer": "we kind of encrypt some laptops"}
    Response (mid-assessment): {"status": "next", "question": {...}, ...}
    Response (done): {"status": "done", "domain_scores": {...}, "report_url": "...", "overall_score": 65}
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")
    user_answer = data.get("answer", "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    current_index = session["current_question_index"]
    question = get_question(current_index)

    if not question:
        return jsonify({"error": "No question found at current index"}), 400

    # Map answer to control IDs via Gemini
    matched_controls = map_answer_to_controls(
        question["id"], user_answer, CONTROL_MAP
    )

    # Save answer
    save_answer(
        session_id, question["id"], question["text"],
        user_answer, matched_controls,
    )

    next_index = current_index + 1
    next_question = get_question(next_index)

    if next_question:
        # Update session to next question
        update_session_question(session_id, next_index)
        return jsonify({
            "status": "next",
            "question": next_question,
            "question_index": next_index,
            "progress": f"{next_index + 1}/{get_total_questions()}",
            "matched_controls": matched_controls,
        })
    else:
        # Assessment complete — calculate scores
        complete_session(session_id)

        # Get all answers
        all_answers = get_answers(session_id)
        session_results = []
        for ans in all_answers:
            session_results.append({
                "question_id": ans["question_id"],
                "matched_controls": json.loads(ans["matched_control_ids"]),
                "user_answer": ans["user_answer"],
                "question_text": ans["question_text"],
            })

        # Calculate domain scores
        domain_scores = calculate_domain_scores(session_results, CONTROL_MAP)
        overall_score = get_overall_score(domain_scores)

        # Persist domain scores
        for domain, info in domain_scores.items():
            save_domain_score(
                session_id, domain, info["score"],
                info["matched"], info["total"], info["gaps"],
            )

        # Generate PDF report
        report_filename = f"report_{session_id}.pdf"
        report_path = os.path.join(PDF_DIR, report_filename)
        generate_gap_report(
            session["company_name"],
            domain_scores,
            session_results,
            CONTROL_MAP,
            report_path,
        )

        # Build response scores dict
        scores_dict = {k: v["score"] for k, v in domain_scores.items()}

        return jsonify({
            "status": "done",
            "domain_scores": scores_dict,
            "overall_score": overall_score,
            "report_url": f"/download/{report_filename}",
            "matched_controls": matched_controls,
        })


@app.route("/api/report/<session_id>", methods=["GET"])
def api_report(session_id):
    """
    Trigger PDF generation (or return existing URL).
    Returns download URL for the PDF report.
    """
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    report_filename = f"report_{session_id}.pdf"
    report_path = os.path.join(PDF_DIR, report_filename)

    # Check for cached priority matrix (may need to regenerate PDF to include it)
    priority_matrix = get_priority_matrix(session_id)
    needs_rebuild = priority_matrix is not None or not os.path.exists(report_path)

    if needs_rebuild:
        all_answers = get_answers(session_id)
        if not all_answers:
            return jsonify({"error": "No answers found for this session"}), 404

        session_results = []
        for ans in all_answers:
            session_results.append({
                "question_id": ans["question_id"],
                "matched_controls": json.loads(ans["matched_control_ids"]),
                "user_answer": ans["user_answer"],
                "question_text": ans["question_text"],
            })

        db_scores = get_domain_scores(session_id)
        if db_scores:
            domain_scores = {}
            for ds in db_scores:
                domain_scores[ds["domain_name"]] = {
                    "score": ds["score"],
                    "matched": ds["covered_questions"],
                    "total": ds["total_questions"],
                    "gaps": json.loads(ds["gap_control_ids"]),
                }
        else:
            domain_scores = calculate_domain_scores(session_results, CONTROL_MAP)

        generate_gap_report(
            session["company_name"],
            domain_scores,
            session_results,
            CONTROL_MAP,
            report_path,
            priority_matrix=priority_matrix,
        )

    return jsonify({
        "report_url": f"/download/{report_filename}",
    })


@app.route("/download/<filename>")
def download_file(filename):
    """Serve generated PDF files."""
    return send_from_directory(PDF_DIR, filename, as_attachment=False)


@app.route("/api/scores/<session_id>", methods=["GET"])
def api_scores(session_id):
    """Return domain scores JSON for the UI chart."""
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    db_scores = get_domain_scores(session_id)
    if db_scores:
        scores_dict = {}
        domain_details = {}
        for ds in db_scores:
            scores_dict[ds["domain_name"]] = ds["score"]
            domain_details[ds["domain_name"]] = {
                "score": ds["score"],
                "covered": ds["covered_questions"],
                "total": ds["total_questions"],
                "gaps": json.loads(ds["gap_control_ids"]),
            }
        overall = round(sum(scores_dict.values()) / len(scores_dict)) if scores_dict else 0
        return jsonify({
            "domain_scores": scores_dict,
            "domain_details": domain_details,
            "overall_score": overall,
            "company_name": session["company_name"],
        })
    else:
        # If not in DB, compute from answers
        all_answers = get_answers(session_id)
        if not all_answers:
            return jsonify({"error": "No assessment data found"}), 404

        session_results = []
        for ans in all_answers:
            session_results.append({
                "question_id": ans["question_id"],
                "matched_controls": json.loads(ans["matched_control_ids"]),
                "user_answer": ans["user_answer"],
                "question_text": ans["question_text"],
            })

        domain_scores = calculate_domain_scores(session_results, CONTROL_MAP)
        scores_dict = {k: v["score"] for k, v in domain_scores.items()}
        overall = get_overall_score(domain_scores)

        return jsonify({
            "domain_scores": scores_dict,
            "domain_details": domain_scores,
            "overall_score": overall,
            "company_name": session["company_name"],
        })


@app.route("/api/priority/<session_id>", methods=["POST"])
def api_priority_matrix(session_id):
    """
    Generate a Remediation Priority Matrix using Gemini.
    Classifies all gap control IDs into 4 quadrants based on effort vs impact.
    Returns JSON with fix_now, plan_for_it, quick_wins, deprioritize.
    """
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Check if we already have a cached matrix
    cached = get_priority_matrix(session_id)
    if cached:
        return jsonify({
            "fix_now": cached["fix_now"],
            "plan_for_it": cached["plan_for_it"],
            "quick_wins": cached["quick_wins"],
            "deprioritize": cached["deprioritize"],
        })

    # Fetch all gap control IDs from domain_scores
    db_scores = get_domain_scores(session_id)
    all_gap_ids = []
    for ds in db_scores:
        gaps = json.loads(ds["gap_control_ids"])
        all_gap_ids.extend(gaps)

    # Deduplicate
    all_gap_ids = sorted(set(all_gap_ids))

    if not all_gap_ids:
        # No gaps — everything is covered
        empty = jsonify({
            "fix_now": [],
            "plan_for_it": [],
            "quick_wins": [],
            "deprioritize": [],
        })
        # Cache the empty result
        save_priority_matrix(session_id, [], [], [], [])
        return empty

    # Build a map of control_id -> description from control_map.json
    control_desc_map = {}
    for q_id, q_data in CONTROL_MAP.items():
        for ctrl_id, desc in q_data.get("descriptions", {}).items():
            if ctrl_id not in control_desc_map:
                control_desc_map[ctrl_id] = desc

    # Build the gap list with descriptions for the prompt
    gap_list_with_descriptions = []
    for cid in all_gap_ids:
        desc = control_desc_map.get(cid, "")
        gap_list_with_descriptions.append({"id": cid, "description": desc})

    # Build prompt for Gemini
    prompt = f"""You are an ISO 27001 consultant. Classify each of these gap control IDs into one of 4 quadrants based on typical SME implementation effort and security impact. Return ONLY valid JSON, no explanation, no markdown.

Controls to classify: {json.dumps(gap_list_with_descriptions, indent=2)}

Return this exact format:
{{
  "fix_now":        [{{"id": "A.5.1", "label": "Short 4-word action"}}],
  "plan_for_it":    [{{"id": "A.8.24", "label": "Short 4-word action"}}],
  "quick_wins":     [{{"id": "A.6.3", "label": "Short 4-word action"}}],
  "deprioritize":   [{{"id": "A.7.7", "label": "Short 4-word action"}}]
}}

Quadrant definitions:
- fix_now: high impact + low effort (do immediately)
- plan_for_it: high impact + high effort (schedule a project)
- quick_wins: low impact + low effort (easy improvements)
- deprioritize: low impact + high effort (not worth it now)"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Extract JSON object from response
        import re
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            raw_text = json_match.group()

        parsed = json.loads(raw_text)

        # Validate structure
        quadrants = ["fix_now", "plan_for_it", "quick_wins", "deprioritize"]
        result = {q: [] for q in quadrants}

        for q in quadrants:
            items = parsed.get(q, [])
            if not isinstance(items, list):
                items = []
            # Filter: only keep IDs that exist in control_map.json
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    cid = item["id"]
                    if cid in control_desc_map and cid in all_gap_ids:
                        label = item.get("label", "")
                        # Ensure label is max ~30 chars
                        if len(label) > 40:
                            label = label[:37] + "..."
                        result[q].append({"id": cid, "label": label})

        # Cache the result
        save_priority_matrix(
            session_id,
            result["fix_now"],
            result["plan_for_it"],
            result["quick_wins"],
            result["deprioritize"],
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Failed to generate priority matrix: {str(e)}"}), 500


# ============================================================
# Authentication Routes
# ============================================================

@app.route("/api/register", methods=["POST"])
def api_register():
    """
    Register a new user.
    Request: {"email": "...", "password": "...", "company_name": "..."}
    Response: {"success": true, "user": {"id": ..., "email": "..."}}
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    company_name = data.get("company_name", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if "@" not in email or "." not in email:
        return jsonify({"error": "Invalid email address"}), 400

    password_hash = generate_password_hash(password)
    user = create_user(email, password_hash, company_name)

    if not user:
        return jsonify({"error": "An account with this email already exists"}), 409

    # Log the user in
    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return jsonify({
        "success": True,
        "user": {"id": user["id"], "email": user["email"], "company_name": user["company_name"]},
    })


@app.route("/api/login", methods=["POST"])
def api_login():
    """
    Log in an existing user.
    Request: {"email": "...", "password": "..."}
    Response: {"success": true, "user": {...}}
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Log the user in
    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return jsonify({
        "success": True,
        "user": {"id": user["id"], "email": user["email"], "company_name": user["company_name"]},
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Log out the current user."""
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me", methods=["GET"])
def api_me():
    """Return the currently logged-in user, or null."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None})

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"user": None})

    return jsonify({
        "user": {"id": user["id"], "email": user["email"], "company_name": user["company_name"]},
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")
    print(f" * ISO 27001 Readiness Chatbot starting on http://localhost:{port} (debug={debug_mode})")
    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)
