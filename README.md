# ISO 27001:2022 Readiness Self-Assessment Chatbot

A Flask-based conversational chatbot that guides an SME through **30 ISO 27001:2022 control questions** across **7 Annex A domains**. The chatbot maps freeform text answers to specific Annex A control IDs using the **Google Gemini Free API**, scores readiness 0–100 per domain, and outputs a structured **PDF gap report** via ReportLab.

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd iso27001-chatbot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   Visit [http://localhost:5000](http://localhost:5000)

## Usage

1. Enter your company name and click **Start Assessment**
2. Answer each of the 30 questions about your organization's security practices
3. The chatbot maps your answers to ISO 27001:2022 Annex A control IDs
4. After all questions, view your domain scores and download the PDF gap report

## Project Structure

```
iso27001-chatbot/
├── app.py                    # Flask app entry point
├── requirements.txt
├── .env.example              # Environment variable template
├── config.py                 # Configuration loader
├── data/
│   └── control_map.json      # 30 control entries with IDs and descriptions
├── db/
│   └── database.py           # SQLite session and answer storage
├── modules/
│   ├── questionnaire.py      # 30 questions across 7 domains
│   ├── llm_mapper.py         # Gemini API integration for control mapping
│   ├── scorer.py             # Domain scoring logic (0–100)
│   └── pdf_generator.py      # ReportLab PDF gap report generator
├── eval/
│   ├── ambiguous_answers.json # 20 adversarial test inputs
│   ├── run_eval.py            # Evaluation runner
│   └── mapping.json           # Evaluation results artifact
├── static/
│   ├── style.css
│   └── chat.js
└── templates/
    └── index.html
```

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Serve chat UI |
| `POST` | `/api/start` | Create new session |
| `POST` | `/api/answer` | Submit answer for current question |
| `GET` | `/api/report/<session_id>` | Trigger/generate PDF report |
| `GET` | `/download/<filename>` | Serve generated PDF |
| `GET` | `/api/scores/<session_id>` | Return domain scores JSON |

## Run Evaluation

```bash
cd eval
python run_eval.py
```

The evaluation tests the LLM mapper against 20 ambiguous answers. A score of **≥ 16/20** is required to pass.

## 7 Annex A Domains Assessed

1. **Organizational Controls** (A.5) — 7 questions
2. **People Controls** (A.6) — 4 questions
3. **Physical Controls** (A.7) — 4 questions
4. **Technological Controls** (A.8) — 8 questions
5. **Asset Management** (A.5.9–A.5.12) — 3 questions
6. **Cryptography** (A.8.24) — 2 questions
7. **Incident Management** (A.5.24–A.5.28) — 2 questions

## What I Would Do With More Time

- Add voice input via Web Speech API for hands-free assessment
- Stream Gemini responses token-by-token via Server-Sent Events (SSE) for real-time feedback
- Add a multi-session dashboard with historical comparison charts
- Improve adversarial handling with few-shot examples in the Gemini prompt
- Add CVSS-style severity ratings to each identified gap
- Implement user authentication and role-based access
- Add support for multiple languages
- Create a REST API client for integration with other tools

## Technical Stack

- **Backend:** Flask (Python 3.10+)
- **LLM:** Google Gemini 1.5 Flash (free tier)
- **PDF:** ReportLab
- **Storage:** SQLite
- **Frontend:** Vanilla HTML + CSS + JavaScript

## License

MIT — For educational purposes (CHARUSAT 2026 — Groovy Web Final Technical Round — Task 09)
