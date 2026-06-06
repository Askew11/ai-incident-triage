from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# ── PERSON A — request shapes (what comes IN to the API) ──────────────────────

# TODO (Person A): Define UploadResponse
# Returned after POST /upload succeeds
# Fields to include: uploaded (int), skipped (int), incident_ids (list[str])
class UploadResponse(BaseModel):
    uploaded: int
    skipped: int
    incident_ids: list[str]
    


# ── PERSON B — response shapes (what goes OUT of the API) ─────────────────────

# TODO (Person B): Define IncidentResponse
# Returned by GET /incidents and GET /incidents/{id}
# Should include all raw incident fields plus the AI triage fields:
#   summary, category, urgency_score, next_actions, process_gaps,
#   triage_status, triage_error, triaged_at
class IncidentResponse(BaseModel):
    # raw incident fields
    id: str
    title: str
    description: Optional[str] = None
    reported_by: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    system: Optional[str] = None
    tags: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # AI triage fields
    summary: Optional[str] = None
    category: Optional[str] = None
    urgency_score: Optional[float] = None
    next_actions: Optional[list[str]] = None
    process_gaps: Optional[list[str]] = None
    triage_status: Optional[str] = None
    triage_error: Optional[str] = None
    triaged_at: Optional[datetime] = None
    triage_steps: Optional[list] = None

    class Config:
        from_attributes = True
