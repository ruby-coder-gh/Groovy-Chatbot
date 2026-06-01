# PRD — ISO 27001 Readiness Self-Assessment Chatbot with Annex A Mapping

**Author:** Nikunj Vaghasiya  
**Project:** CHARUSAT 2026 — Groovy Web Final Technical Round — Task 09  
**Stack:** Flask · Google Gemini Free API · ReportLab · SQLite  
**Estimated Build Time:** 3–4 hours

---

## 1. Overview

Build a Flask-based conversational chatbot that guides an SME (Small or Medium Enterprise) through **30 ISO 27001:2022 control questions** across **7 Annex A domains**. The chatbot maps each freeform text answer to one or more specific Annex A control IDs using the **Google Gemini free API**, scores readiness 0–100 per domain, and outputs a structured **PDF gap report** via ReportLab.

The system must pass an **adversarial evaluation** of 20 ambiguous answers and never hallucinate control IDs outside the authored map.

---

## 2. Goals & Success Criteria

| Goal | Metric |
|---|---|
| Correct control mapping | ≥ 16 / 20 ambiguous answers mapped correctly |
| Full domain coverage | All 7 Annex A domains scored on every assessment |
| Clean PDF output | PDF renders with control IDs, descriptions, next steps |
| No hallucinated IDs | 0 invented control IDs outside authored `control_map.json` |

---

## 3. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Flask (Python 3.10+) | REST + SSE for streaming |
| LLM | Google Gemini 1.5 Flash (free tier) | `google-generativeai` SDK |
| PDF | ReportLab | `reportlab` pip package |
| Storage | SQLite via `sqlite3` stdlib | Session + assessment data |
| Frontend | Vanilla HTML + CSS + JS (served by Flask) | Single-page chat UI |
| Eval | Python script + JSON artefact | `eval/run_eval.py` + `eval/mapping.json` |

---

## 4. ISO 27001:2022 Annex A Domain Map

The 30 questions are distributed across these 7 domains:

| # | Domain | Annex A Ref | Questions |
|---|---|---|---|
| 1 | Organizational Controls | A.5 | 7 |
| 2 | People Controls | A.6 | 4 |
| 3 | Physical Controls | A.7 | 4 |
| 4 | Technological Controls | A.8 | 8 |
| 5 | Asset Management | A.5.9–A.5.12 | 3 |
| 6 | Cryptography | A.8.24 | 2 |
| 7 | Incident Management | A.5.24–A.5.28 | 2 |

---

## 5. Project File Structure

```
iso27001-chatbot/
├── app.py                    # Flask app entry point
├── requirements.txt
├── .env.example              # GEMINI_API_KEY placeholder
├── config.py                 # Config loader
│
├── data/
│   └── control_map.json      # Authored map: question_id → control_ids + descriptions
│
├── eval/
│   ├── ambiguous_answers.json  # 20 adversarial test inputs
│   ├── run_eval.py             # Evaluation runner
│   └── mapping.json            # Output artefact (committed after eval)
│
├── modules/
│   ├── questionnaire.py      # 30 questions + domain metadata
│   ├── llm_mapper.py         # Gemini API call + control ID extraction
│   ├── scorer.py             # Domain scoring logic (0–100)
│   └── pdf_generator.py      # ReportLab PDF gap report
│
├── db/
│   └── database.py           # SQLite session + result storage
│
├── static/
│   ├── style.css
│   └── chat.js
│
└── templates/
    └── index.html            # Chat UI
```

---

## 6. Core Data: `control_map.json` (Schema)

This file is **authored by you** — Gemini only picks IDs from this map, never invents new ones.

```json
{
  "Q01": {
    "domain": "Organizational Controls",
    "question": "Do you have a documented Information Security Policy?",
    "control_ids": ["A.5.1"],
    "descriptions": {
      "A.5.1": "Policies for information security shall be defined, approved by management, published, communicated and reviewed."
    },
    "keywords": ["policy", "document", "information security policy", "written policy"]
  },
  "Q02": {
    "domain": "Organizational Controls",
    "question": "Are roles and responsibilities for information security clearly defined?",
    "control_ids": ["A.5.2"],
    "descriptions": {
      "A.5.2": "Information security roles and responsibilities shall be defined and allocated."
    },
    "keywords": ["roles", "responsibilities", "CISO", "security team", "assigned"]
  }
}
```

> You must author all 30 entries. See Section 9 for the full 30-question list.

---

## 7. Module Specifications

### 7.1 `modules/questionnaire.py`

```python
QUESTIONS = [
    {
        "id": "Q01",
        "domain": "Organizational Controls",
        "text": "Do you have a documented Information Security Policy?",
        "hint": "e.g. written policy, reviewed annually, signed by management"
    },
    # ... 29 more
]

def get_question(index: int) -> dict:
    """Return question at index, or None if done."""

def get_all_domains() -> list[str]:
    """Return list of 7 unique domain names."""
```

### 7.2 `modules/llm_mapper.py`

**Responsibility:** Given a question ID and a freeform user answer, call Gemini and return a list of matched control IDs. The prompt **strictly constrains** Gemini to only pick IDs from `control_map.json`.

```python
import google.generativeai as genai
import json

def map_answer_to_controls(question_id: str, user_answer: str, control_map: dict) -> list[str]:
    """
    Calls Gemini Flash with a strict system prompt.
    Returns list of matched control IDs from control_map only.
    Never returns IDs not in the map.
    """
    allowed_ids = list(control_map[question_id]["control_ids"])
    prompt = f"""
You are an ISO 27001:2022 compliance analyst.
Given the question and user answer below, determine which of the ALLOWED control IDs apply.

Question: {control_map[question_id]['question']}
User Answer: {user_answer}

ALLOWED control IDs (ONLY choose from this list): {allowed_ids}

Rules:
1. Return ONLY a JSON array of matched IDs from the allowed list.
2. Do NOT invent or add any control ID not in the allowed list.
3. If the answer is vague or partial, still only pick from the allowed list.
4. Return [] if nothing matches.

Respond with ONLY valid JSON. Example: ["A.5.1"] or ["A.8.24", "A.5.10"] or []
"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    # Parse and validate — filter any ID not in allowed_ids
    raw = json.loads(response.text.strip())
    return [cid for cid in raw if cid in allowed_ids]
```

### 7.3 `modules/scorer.py`

```python
def calculate_domain_scores(session_results: list[dict], control_map: dict) -> dict:
    """
    Input: list of {question_id, matched_controls, user_answer}
    Output: {
        "Organizational Controls": {"score": 72, "matched": 5, "total": 7, "gaps": ["A.5.3"]},
        ...
    }
    Score = (matched controls / total controls in domain) * 100
    """
```

**Scoring Logic:**
- Each question has a set of expected control IDs.
- A question is "covered" if at least one expected ID is matched.
- Domain score = `(covered questions / total questions in domain) * 100`.
- Round to nearest integer.

### 7.4 `modules/pdf_generator.py`

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_gap_report(
    company_name: str,
    domain_scores: dict,
    session_results: list[dict],
    control_map: dict,
    output_path: str
) -> str:
    """
    Generates PDF at output_path.
    Sections:
      1. Cover: Company name, date, overall score
      2. Executive Summary: Table of 7 domains + scores
      3. Gap Analysis: Per-domain, list missed controls + descriptions + next steps
      4. Full Response Log: Q&A transcript
    Returns output_path.
    """
```

**PDF Sections:**

1. **Cover Page** — Title, company name, assessment date, overall readiness % (average of 7 domain scores)
2. **Executive Summary** — Table: Domain | Score | Status (🟢 ≥70 | 🟡 40–69 | 🔴 <40)
3. **Gap Analysis** (per domain) — missed control ID, description, suggested next step
4. **Full Q&A Transcript** — all 30 questions + user's answers

---

## 8. Flask API Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Serve chat UI (`index.html`) |
| `POST` | `/api/start` | Create new session, return session_id + first question |
| `POST` | `/api/answer` | Submit answer for current question; returns next question or `done` |
| `GET` | `/api/report/<session_id>` | Trigger PDF generation; return download URL |
| `GET` | `/download/<filename>` | Serve generated PDF file |
| `GET` | `/api/scores/<session_id>` | Return domain scores JSON (for UI chart) |

### `/api/answer` Request/Response

```json
// Request
{ "session_id": "abc123", "answer": "we kind of encrypt some laptops" }

// Response (mid-assessment)
{
  "status": "next",
  "question_index": 5,
  "question": "Do you conduct background checks on new employees?",
  "domain": "People Controls",
  "progress": "5/30"
}

// Response (assessment complete)
{
  "status": "done",
  "domain_scores": { "Organizational Controls": 72, ... },
  "report_url": "/download/report_abc123.pdf"
}
```

---

## 9. The 30 Questions (Full List)

### Organizational Controls — A.5 (7 questions)

| ID | Question | Control IDs |
|---|---|---|
| Q01 | Do you have a documented Information Security Policy? | A.5.1 |
| Q02 | Are roles and responsibilities for information security defined? | A.5.2 |
| Q03 | Do you have a process for managing information security risks? | A.5.8 |
| Q04 | Is there a process for handling supplier/third-party security? | A.5.19, A.5.20 |
| Q05 | Do you conduct internal information security audits? | A.5.35 |
| Q06 | Is there a business continuity plan that covers IT/data? | A.5.29, A.5.30 |
| Q07 | Do you have a legal/compliance register for data protection laws? | A.5.31, A.5.34 |

### People Controls — A.6 (4 questions)

| ID | Question | Control IDs |
|---|---|---|
| Q08 | Do you conduct background checks on new employees? | A.6.1 |
| Q09 | Is security training provided to all staff? | A.6.3 |
| Q10 | Do employees sign confidentiality/NDA agreements? | A.6.2 |
| Q11 | Is there a process for offboarding employees (revoking access)? | A.6.5 |

### Physical Controls — A.7 (4 questions)

| ID | Question | Control IDs |
|---|---|---|
| Q12 | Are server rooms / data centres physically secured? | A.7.1, A.7.2 |
| Q13 | Do you control visitor access to sensitive areas? | A.7.3 |
| Q14 | Is equipment protected against environmental threats? | A.7.8 |
| Q15 | Do you have a clear desk and clear screen policy? | A.7.7 |

### Technological Controls — A.8 (8 questions)

| ID | Question | Control IDs |
|---|---|---|
| Q16 | Do you use multi-factor authentication (MFA)? | A.8.5 |
| Q17 | Are access rights reviewed and revoked when no longer needed? | A.8.2, A.8.3 |
| Q18 | Are all systems patched and updated regularly? | A.8.8 |
| Q19 | Do you have antivirus / endpoint protection on all devices? | A.8.7 |
| Q20 | Is network traffic monitored for threats? | A.8.16 |
| Q21 | Do you have a Web Application Firewall (WAF) or similar? | A.8.20, A.8.21 |
| Q22 | Is data backed up regularly and tested for restore? | A.8.13 |
| Q23 | Do you conduct penetration tests or vulnerability scans? | A.8.8, A.8.25 |

### Asset Management — A.5.9–A.5.12 (3 questions)

| ID | Question | Control IDs |
|---|---|---|
| Q24 | Do you maintain an inventory of all information assets? | A.5.9 |
| Q25 | Is information classified according to sensitivity? | A.5.12 |
| Q26 | Do you have a policy for secure disposal of media/devices? | A.5.11, A.7.14 |

### Cryptography — A.8.24 (2 questions)

| ID | Question | Control IDs |
|---|---|---|
| Q27 | Are laptops and mobile devices encrypted? | A.8.24 |
| Q28 | Is sensitive data encrypted at rest and in transit? | A.8.24, A.5.10 |

### Incident Management — A.5.24–A.5.28 (2 questions)

| ID | Question | Control IDs |
|---|---|---|
| Q29 | Do you have an incident response plan? | A.5.24, A.5.25 |
| Q30 | Are security incidents logged and reviewed after resolution? | A.5.27, A.5.28 |

---

## 10. Adversarial Evaluation — 20 Ambiguous Answers

These 20 test inputs must be in `eval/ambiguous_answers.json` and run via `eval/run_eval.py`.

```json
[
  { "id": "AE01", "question_id": "Q27", "answer": "we kind of encrypt some laptops", "expected_ids": ["A.8.24"] },
  { "id": "AE02", "question_id": "Q16", "answer": "users have a second step sometimes when logging in from outside", "expected_ids": ["A.8.5"] },
  { "id": "AE03", "question_id": "Q01", "answer": "there's a document from 2019 we haven't really updated", "expected_ids": ["A.5.1"] },
  { "id": "AE04", "question_id": "Q11", "answer": "we usually remove their email after a week or so", "expected_ids": ["A.6.5"] },
  { "id": "AE05", "question_id": "Q22", "answer": "backups run automatically I think, not sure if anyone tests them", "expected_ids": ["A.8.13"] },
  { "id": "AE06", "question_id": "Q28", "answer": "we use HTTPS on our website but not sure about the database", "expected_ids": ["A.8.24", "A.5.10"] },
  { "id": "AE07", "question_id": "Q18", "answer": "IT applies patches quarterly unless something urgent comes up", "expected_ids": ["A.8.8"] },
  { "id": "AE08", "question_id": "Q09", "answer": "new hires get a 30-minute video during onboarding", "expected_ids": ["A.6.3"] },
  { "id": "AE09", "question_id": "Q24", "answer": "we have a spreadsheet somewhere listing our main servers", "expected_ids": ["A.5.9"] },
  { "id": "AE10", "question_id": "Q12", "answer": "the server room has a lock and only IT staff have the key", "expected_ids": ["A.7.1", "A.7.2"] },
  { "id": "AE11", "question_id": "Q29", "answer": "we figure it out as we go when something breaks", "expected_ids": [] },
  { "id": "AE12", "question_id": "Q25", "answer": "confidential files have a watermark, others don't have labels", "expected_ids": ["A.5.12"] },
  { "id": "AE13", "question_id": "Q17", "answer": "we did a big review last year when someone left the company", "expected_ids": ["A.8.2", "A.8.3"] },
  { "id": "AE14", "question_id": "Q08", "answer": "we check LinkedIn and call references but no formal process", "expected_ids": ["A.6.1"] },
  { "id": "AE15", "question_id": "Q19", "answer": "Windows Defender is on by default, that counts right?", "expected_ids": ["A.8.7"] },
  { "id": "AE16", "question_id": "Q04", "answer": "vendors sign an NDA before we share anything sensitive", "expected_ids": ["A.5.19", "A.5.20"] },
  { "id": "AE17", "question_id": "Q26", "answer": "we physically destroy old hard drives with a hammer", "expected_ids": ["A.5.11", "A.7.14"] },
  { "id": "AE18", "question_id": "Q23", "answer": "a friend in IT once looked for obvious holes, found nothing", "expected_ids": ["A.8.8", "A.8.25"] },
  { "id": "AE19", "question_id": "Q06", "answer": "we keep copies of important files on Google Drive", "expected_ids": ["A.5.29", "A.5.30"] },
  { "id": "AE20", "question_id": "Q30", "answer": "we tell the team what happened in the monthly meeting", "expected_ids": ["A.5.27", "A.5.28"] }
]
```

### Eval Runner — `eval/run_eval.py`

```python
import json, sys
sys.path.insert(0, "..")
from modules.llm_mapper import map_answer_to_controls

with open("ambiguous_answers.json") as f:
    cases = json.load(f)

with open("../data/control_map.json") as f:
    control_map = json.load(f)

results = []
passed = 0

for case in cases:
    predicted = map_answer_to_controls(case["question_id"], case["answer"], control_map)
    expected = set(case["expected_ids"])
    got = set(predicted)
    correct = expected == got or (not expected and not got)
    if correct:
        passed += 1
    results.append({
        "id": case["id"],
        "question_id": case["question_id"],
        "answer": case["answer"],
        "expected": case["expected_ids"],
        "predicted": predicted,
        "pass": correct
    })
    print(f"{'✓' if correct else '✗'} {case['id']}: expected={case['expected_ids']} got={predicted}")

print(f"\nResult: {passed}/20 passed")

with open("mapping.json", "w") as f:
    json.dump({"score": f"{passed}/20", "results": results}, f, indent=2)
```

---

## 11. Database Schema (SQLite)

```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    company_name TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    current_question_index INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- Answers table
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    question_id TEXT,
    question_text TEXT,
    user_answer TEXT,
    matched_control_ids TEXT,   -- JSON array stored as string
    answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Domain scores table
CREATE TABLE domain_scores (
    session_id TEXT,
    domain_name TEXT,
    score INTEGER,
    covered_questions INTEGER,
    total_questions INTEGER,
    gap_control_ids TEXT,       -- JSON array
    PRIMARY KEY (session_id, domain_name)
);
```

---

## 12. Chat UI Specification

Simple single-page HTML served by Flask at `/`.

**Components:**
- Message bubbles (user = right, bot = left)
- Progress bar: `Question X of 30 | Domain: Organizational Controls`
- Domain score cards shown after all 30 questions answered
- "Download PDF Report" button (calls `/api/report/<session_id>`)
- Company name input at start of session

**No frontend framework needed** — plain HTML + CSS + `fetch()` JS.

---

## 13. Environment Variables

`.env` (not committed):
```
GEMINI_API_KEY=your_key_here
```

`.env.example` (committed):
```
GEMINI_API_KEY=your_gemini_api_key_here
```

Load via `python-dotenv` in `config.py`.

---

## 14. `requirements.txt`

```
flask>=3.0.0
google-generativeai>=0.5.0
reportlab>=4.0.0
python-dotenv>=1.0.0
```

---

## 15. `README.md` Sections (Required for Submission)

```markdown
## Setup
1. Clone repo
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add `GEMINI_API_KEY`
4. `python app.py`
5. Open http://localhost:5000

## Run Evaluation
cd eval
python run_eval.py

## What I Would Do With More Time
- Add voice input via Web Speech API
- Stream Gemini responses token-by-token via SSE
- Add a multi-session dashboard with historical comparisons
- Improve adversarial handling with few-shot examples in the prompt
- Add CVSS-style severity to each gap
```

---

## 16. Quality Gate Checklist

Before submission, verify all of these:

- [ ] `eval/run_eval.py` outputs `≥ 16/20 passed`
- [ ] `eval/mapping.json` is committed with full results
- [ ] All 7 Annex A domains appear in every assessment's score output
- [ ] PDF renders without errors, contains control IDs + descriptions
- [ ] Grep `control_map.json` keys — no ID in any output that isn't in the map
- [ ] `README.md` has setup, run, eval, and "what I'd do with more time" sections
- [ ] Demo video (3–6 min) shows: happy path chat → score cards → PDF download → eval run

---

## 17. Build Order (Recommended)

1. **Hour 1** — Author `control_map.json` (30 entries) + `questionnaire.py` + SQLite schema
2. **Hour 2** — `llm_mapper.py` (Gemini integration) + `scorer.py` + Flask API routes
3. **Hour 3** — Chat UI (HTML/CSS/JS) + `pdf_generator.py` (ReportLab)
4. **Hour 4** — `eval/run_eval.py` + fix failures + README + demo video recording