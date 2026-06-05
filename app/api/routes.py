from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["incidents"])


# ── PERSON A — POST /upload ───────────────────────────────────────────────────

# TODO (Person A): Implement POST /incidents/upload
# - Accept a CSV file upload
# - Call incident_service.ingest_csv(file.file, db)
# - Optionally kick off background triage for each uploaded incident
# - Return UploadResponse


# ── PERSON B — GET /incidents and GET /incidents/{id} ────────────────────────

# TODO (Person B): Implement GET /incidents
# - Optional query params: status, category, triage_status, min_urgency
# - Order by urgency_score descending (nulls last)
# - Return list[IncidentResponse]

# TODO (Person B): Implement GET /incidents/{incident_id}
# - Return a single IncidentResponse or 404
