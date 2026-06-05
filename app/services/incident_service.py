import io
from datetime import datetime, timezone
from typing import BinaryIO

import pandas as pd
from sqlalchemy.orm import Session

from app.models.incident import IncidentRecord, UploadResponse
from app.services.ai_service import triage_incident

REQUIRED_COLUMNS = {"id", "title"}

_PROCESS_GAP_RULES = [
    (lambda r: not r.assigned_to, "No assignee — incident ownership is unclear"),
    (lambda r: not r.reported_by, "Reporter not captured — traceability gap"),
    (lambda r: not r.description or len(r.description.strip()) < 20, "Description is missing or too brief to be actionable"),
    (lambda r: not r.system, "Affected system not specified"),
    (lambda r: r.status in (None, "", "Open") and r.created_at and
     (datetime.now() - r.created_at).total_seconds() > 86400,
     "Incident open for >24 hours with no status update"),
]


def _rule_based_gaps(record: IncidentRecord) -> list[str]:
    return [msg for check, msg in _PROCESS_GAP_RULES if check(record)]


def _parse_dt(val) -> datetime | None:
    if pd.isna(val) or val == "":
        return None
    try:
        return pd.to_datetime(val).to_pydatetime().replace(tzinfo=None)
    except Exception:
        return None


def ingest_csv(file: BinaryIO, db: Session) -> UploadResponse:
    df = pd.read_csv(file, dtype=str).fillna("")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    uploaded, skipped = 0, 0
    ids: list[str] = []

    for _, row in df.iterrows():
        incident_id = str(row["id"]).strip()
        if not incident_id:
            skipped += 1
            continue

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
            created_at=_parse_dt(row.get("created_at")),
            resolved_at=_parse_dt(row.get("resolved_at")),
            triage_status="pending",
        )
        db.add(record)
        uploaded += 1
        ids.append(incident_id)

    db.commit()
    return UploadResponse(uploaded=uploaded, skipped=skipped, incident_ids=ids)


def run_triage(incident_id: str, db: Session) -> IncidentRecord:
    record = db.get(IncidentRecord, incident_id)
    if record is None:
        raise ValueError(f"Incident {incident_id} not found")

    record.triage_status = "processing"
    db.commit()

    try:
        result = triage_incident(record)

        # Merge AI-detected gaps with rule-based gaps (deduplicated)
        rule_gaps = _rule_based_gaps(record)
        all_gaps = list({*result.process_gaps, *rule_gaps})

        record.summary = result.summary
        record.category = result.category
        record.urgency_score = result.urgency_score
        record.next_actions = result.next_actions
        record.process_gaps = all_gaps
        record.triage_status = "done"
        record.triaged_at = datetime.now()
        record.triage_error = None
    except Exception as exc:
        record.triage_status = "error"
        record.triage_error = str(exc)

    db.commit()
    db.refresh(record)
    return record
