# PERSON A — Ingest track
import pandas as pd
from app.models.incident import IncidentRecord
from typing import BinaryIO
from sqlalchemy.orm import Session
from app.schemas.incident import UploadResponse
from datetime import datetime
from app.services import ai_service
from app.services import rules_service


def _clean(value) -> str | None:
    """Return a stripped string, or None for blank cells.

    pandas reads blank cells as NaN, and str(NaN) is "nan", so checking
    for missing values has to happen before converting to a string.
    """
    if value is None or pd.isna(value):
        return None
    return str(value).strip() or None


def _timestamp(value) -> datetime | None:
    """Parse a CSV timestamp into a naive UTC datetime, or None if blank or invalid."""
    text = _clean(value)
    if text is None:
        return None
    ts = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(ts):
        return None
    # rules_service compares against datetime.utcnow(), which is naive UTC
    return ts.tz_convert(None).to_pydatetime()


def ingest_csv(file: BinaryIO, db: Session) -> UploadResponse:
    """
    Parse the uploaded CSV file and save each row as an IncidentRecord.

    Steps to implement:
    1. Read the CSV into a pandas DataFrame
    2. Validate that required columns exist (at minimum: id, title)
    3. For each row, check if the incident already exists in the DB (skip if so)
    4. Create an IncidentRecord and add it to the session
    5. Commit and return an UploadResponse with counts

    Raise ValueError if required columns are missing.
    """
    
    df = pd.read_csv(file)
    df = df.where(pd.notna(df), None)
    
    required = {"id", "title"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}") 
    
    uploaded = 0
    skipped = 0
    ids = []
    
    for _, row in df.iterrows():
        incident_id = str(row["id"]).strip()
        existing = db.get(IncidentRecord, incident_id)
        if existing:
            skipped += 1
            continue
        
        record = IncidentRecord(
            id=incident_id,
            title=_clean(row.get("title")) or "",
            description=_clean(row.get("description")),
            reported_by=_clean(row.get("reported_by")),
            assigned_to=_clean(row.get("assigned_to")),
            status=_clean(row.get("status")),
            priority=_clean(row.get("priority")),
            system=_clean(row.get("system")),
            tags=_clean(row.get("tags")),
            created_at=_timestamp(row.get("created_at")),
            resolved_at=_timestamp(row.get("resolved_at")),
        )
        db.add(record)
        uploaded += 1
        ids.append(incident_id)
        
    db.commit()
    return UploadResponse(uploaded=uploaded, skipped=skipped, incident_ids=ids)
    
    


def run_triage(incident_id: str, db: Session):
    """
    Orchestrates triage for a single incident.

    Steps to implement:
    1. Fetch the IncidentRecord by id (raise ValueError if not found)
    2. Set triage_status = "processing" and commit
    3. Call ai_service.triage_incident(record) — this is Person B's function
    4. Save the result back to the record fields
    5. Set triage_status = "done" (or "error" on exception)
    6. Commit and return the updated record
    """
    record = db.get(IncidentRecord, incident_id)
    if record is None:
        raise ValueError(f"Incident {incident_id} not found")
    
    record.triage_status = "processing"
    db.commit()
    
    rule_gaps = rules_service.detect_process_gaps(record)
    
    try:
        result = ai_service.triage_incident(record, db)
        record.summary = result.summary
        record.category = result.category
        record.urgency_score = result.urgency_score
        record.next_actions = result.next_actions
        record.process_gaps = result.process_gaps + rule_gaps
        record.triage_steps = result.triage_steps
        record.triage_status = "done"
        record.triaged_at = datetime.utcnow()
    except Exception as e:
        record.triage_status = "error"
        record.triage_error = str(e)

    db.commit()
    return record
    
