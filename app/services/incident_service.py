# PERSON A — Ingest track
from typing import BinaryIO
from sqlalchemy.orm import Session
from app.schemas.incident import UploadResponse


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
    raise NotImplementedError


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
    raise NotImplementedError
