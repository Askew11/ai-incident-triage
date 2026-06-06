# PERSON A — Ingest track
import pandas as pd
from app.models.incident import IncidentRecord
from typing import BinaryIO
from sqlalchemy.orm import Session
from app.schemas.incident import UploadResponse
from datetime import datetime
from app.services import ai_service


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
            title=str(row.get("title", "")).strip(),
            description=str(row.get("description", "")).strip() or None,
            reported_by=str(row.get("reported_by", "")).strip() or None,
            assigned_to=str(row.get("assigned_to", "")).strip() or None,
            status=str(row.get("status", "")).strip() or None,
            priority=str(row.get("priority", "")).strip() or None,
            system=str(row.get("system", "")).strip() or None,
            tags=str(row.get("tags", "")).strip() or None,
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
    
    try:
        result = ai_service.triage_incident(record)
        record.summary = result.summary
        record.category = result.category
        record.urgency_score = result.urgency_score
        record.next_actions = result.next_actions
        record.process_gaps = result.process_gaps
        record.triage_status = "done"
        record.triaged_at = datetime.utcnow()
    except Exception as e:
        record.triage_status = "error"
        record.triage_error = str(e)

    db.commit()
    return record
    
