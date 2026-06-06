# AI Incident Triage Assistant

A backend AI service that ingests IT incident records, classifies and summarizes tickets, detects process gaps, and recommends next actions — using an agentic tool-calling pipeline powered by OpenAI.

---

## What It Does

1. **Ingest** — accepts incident data via CSV upload
2. **Parse & Clean** — normalizes and validates fields, skips duplicates
3. **Rules Check** — deterministically flags missing owners, priorities, vague descriptions, and stale tickets
4. **AI Agent Triage** — an LLM agent decides which tools to call and in what order:
   - Classifies the incident into a category
   - Scores urgency from 0–10
   - Writes a business-readable summary
   - Recommends specific next actions
5. **Store & Retrieve** — saves all results to a database, exposes them through filterable REST endpoints

---

## How the AI Agent Works

Instead of a fixed pipeline, the triage agent uses OpenAI tool calling to decide its own steps. It is given four tools:

| Tool | What it does |
|---|---|
| `classify_incident` | Picks a category based on the incident details |
| `score_urgency` | Scores urgency 0–10 and writes a summary |
| `recommend_actions` | Returns a list of next steps |
| `finalize_triage` | Signals the agent is done and submits the final result |

The model calls tools in whatever order it chooses, reads the results, and continues until it calls `finalize_triage`. This means it can skip steps it doesn't need or revisit a step with new context.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Data Validation | Pydantic |
| ORM | SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod-ready) |
| Data Processing | pandas |
| AI | OpenAI API — gpt-4o-mini with tool calling |
| Testing | pytest |

---

## Project Structure

```
ai-incident-triage/
├── app/
│   ├── main.py                   # FastAPI app entry point
│   ├── database.py               # SQLAlchemy engine and session
│   ├── api/
│   │   └── routes.py             # REST endpoints
│   ├── models/
│   │   └── incident.py           # IncidentRecord database model
│   ├── schemas/
│   │   └── incident.py           # Pydantic request/response shapes
│   └── services/
│       ├── ai_service.py         # Agentic triage pipeline
│       ├── incident_service.py   # Ingest and triage orchestration
│       └── rules_service.py      # Deterministic process gap detection
├── data/
│   └── sample_incidents.csv
├── tests/
│   └── test_ingestion.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/Askew11/ai-incident-triage.git
cd ai-incident-triage
```

### 2. Set up virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows
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

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/incidents/upload` | Upload a CSV of incidents and trigger triage |
| GET | `/api/v1/incidents` | Retrieve all incidents, sorted by urgency |
| GET | `/api/v1/incidents/{id}` | Retrieve a single incident |

### Query filters for `GET /api/v1/incidents`

| Parameter | Example | Description |
|---|---|---|
| `status` | `Open` | Filter by incident status |
| `category` | `deployment_issue` | Filter by AI-assigned category |
| `triage_status` | `done` | Filter by triage state (`pending`, `done`, `error`) |
| `min_urgency` | `7.0` | Return only incidents at or above this urgency score |

---

## Sample Input (CSV)

```
id,title,description,reported_by,assigned_to,status,priority,system,tags
INC-001,Login failure for client X,Users unable to log in after the latest deployment,Jane Smith,,Open,High,Auth Service,login;auth
INC-002,Data export missing records,Monthly export job returned 0 rows with no error logged,John Doe,,Open,,Reporting,export;data
```

---

## Sample Output (per incident)

```json
{
  "id": "INC-001",
  "title": "Login failure for client X",
  "summary": "The login failure for client X is a critical access issue affecting users after a recent deployment. Given the high priority and the potential impact on user operations, this incident requires immediate attention to restore access.",
  "category": "access_issue",
  "urgency_score": 8.5,
  "next_actions": [
    "Investigate the deployment logs for any errors related to the Auth Service.",
    "Check for any changes made to authentication configurations during the latest deployment.",
    "Consider rolling back the latest deployment if a critical issue is found."
  ],
  "process_gaps": [],
  "triage_status": "done",
  "triaged_at": "2026-06-06T21:44:15.138995"
}
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Roadmap

### Done
- [x] CSV upload and parsing
- [x] Duplicate detection and skipping
- [x] Deterministic rules engine for process gap detection
- [x] AI agent triage with OpenAI tool calling
- [x] Urgency scoring and categorization
- [x] Filterable REST API with results sorted by urgency

### Up Next
- [ ] Async background triage (don't block the upload response)
- [ ] Docker + PostgreSQL + GitHub Actions CI
- [ ] Similar incident lookup tool (give the agent historical context)
- [ ] Agent step logging (observe which tools the agent called and in what order)
- [ ] Retriage endpoint (`POST /incidents/{id}/retriage`)
- [ ] Test coverage for the AI service layer

---

## License

MIT
