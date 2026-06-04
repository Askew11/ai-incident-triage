# ai-incident-triage
# AI Incident Triage Assistant

A backend AI service that ingests incident records, summarizes issues, classifies tickets, flags process gaps, and recommends next actions.

---

## What It Does

1. **Ingest** — accepts incident data via CSV upload or API
2. **Parse & Clean** — normalizes and validates fields
3. **Summarize** — generates a short, business-readable summary per incident
4. **Classify** — categorizes each incident (access / deployment / data / configuration / other)
5. **Score** — assigns an urgency score and flags SLA risk
6. **Flag Gaps** — detects missing fields, incomplete ownership, poor descriptions
7. **Recommend** — suggests next actions using rules + LLM reasoning
8. **Store & Retrieve** — saves results to a database, exposes them through REST endpoints

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Data Validation | Pydantic |
| ORM | SQLAlchemy |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Data Processing | pandas, openpyxl |
| AI | OpenAI API (structured JSON outputs) |
| Testing | pytest |

---

## Project Structure

```
ai-incident-triage/
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── routes/           # API endpoints
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic request/response shapes
│   ├── services/         # Business logic (parsing, AI calls, rules)
│   └── db.py             # Database connection
├── data/
│   └── sample_incidents.csv
├── tests/
│   └── test_upload.py
├── .env.example          # Environment variable template
├── requirements.txt
└── README.md
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/ai-incident-triage.git
cd ai-incident-triage
```

### 2. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your-key-here
DATABASE_URL=sqlite:///./incidents.db
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

API is live at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

---

## API Endpoints (MVP)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/upload` | Upload a CSV of incidents |
| GET | `/incidents` | Retrieve all processed incidents |
| GET | `/incidents/{id}` | Retrieve a single processed incident |

---

## Sample Input (CSV)

```
incident_id,title,description,reported_by,date_reported,status,priority
INC-001,Login failure for client X,Users unable to log in after deployment,Jane Smith,2024-06-01,Open,High
INC-002,Data export missing records,Monthly export job returned 0 rows,John Doe,2024-06-02,Open,
```

---

## Sample Output (per incident)

```json
{
  "incident_id": "INC-001",
  "summary": "Post-deployment login failure impacting client X users. Likely an authentication config issue.",
  "category": "deployment_issue",
  "urgency_score": 8,
  "process_flags": [],
  "recommended_action": "Roll back the latest deployment and verify auth service configuration."
}
```

---

## Roadmap

### Version 1 (MVP)
- [x] Project scaffold
- [ ] CSV upload and parsing
- [ ] AI summarization and classification
- [ ] Urgency scoring
- [ ] Results stored and retrievable via API

### Version 2
- [ ] Rules engine for process/compliance gap detection
- [ ] Duplicate incident detection
- [ ] Cluster similar incidents
- [ ] Reprocessing support
- [ ] Basic dashboard

---

## Contributing

1. Branch off `main` using the format `feature/your-feature-name`
2. Keep PRs focused — one feature or fix per PR
3. Run `pytest` before opening a PR

---

## License

MIT
