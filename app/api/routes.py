from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import IncidentRecord, IncidentResponse, UploadResponse, TriageSummary
from app.services.incident_service import ingest_csv, run_triage

router = APIRouter(prefix="/api/v1", tags=["incidents"])


@router.post("/incidents/upload", response_model=UploadResponse, summary="Upload a CSV of incidents")
async def upload_incidents(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV file with incident records"),
    auto_triage: bool = True,
    db: Session = Depends(get_db),
):
    """
    Upload a CSV file containing incident records. Columns: id, title, description,
    reported_by, assigned_to, status, priority, system, tags, created_at, resolved_at.

    Set `auto_triage=true` (default) to kick off AI triage for all uploaded incidents
    in the background.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        result = ingest_csv(file.file, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if auto_triage:
        for incident_id in result.incident_ids:
            background_tasks.add_task(run_triage, incident_id, db)

    return result


@router.post("/incidents/{incident_id}/triage", response_model=IncidentResponse, summary="Triage a single incident")
def triage_incident_endpoint(incident_id: str, db: Session = Depends(get_db)):
    """Run AI triage on a single incident synchronously. Returns the updated record."""
    try:
        record = run_triage(incident_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return record


@router.get("/incidents", response_model=list[IncidentResponse], summary="List all incidents")
def list_incidents(
    status: str | None = None,
    category: str | None = None,
    triage_status: str | None = None,
    min_urgency: float | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List incidents with optional filters. Results are ordered by urgency score (highest first)."""
    query = db.query(IncidentRecord)
    if status:
        query = query.filter(IncidentRecord.status == status)
    if category:
        query = query.filter(IncidentRecord.category == category)
    if triage_status:
        query = query.filter(IncidentRecord.triage_status == triage_status)
    if min_urgency is not None:
        query = query.filter(IncidentRecord.urgency_score >= min_urgency)

    query = query.order_by(IncidentRecord.urgency_score.desc().nullslast())
    return query.offset(offset).limit(limit).all()


@router.get("/incidents/summary", response_model=TriageSummary, summary="Triage status summary")
def triage_summary(db: Session = Depends(get_db)):
    """Returns a count of incidents by triage status."""
    records = db.query(IncidentRecord).all()
    counts = {"done": 0, "pending": 0, "processing": 0, "error": 0}
    for r in records:
        counts[r.triage_status] = counts.get(r.triage_status, 0) + 1
    return TriageSummary(
        total=len(records),
        done=counts["done"],
        pending=counts["pending"] + counts["processing"],
        error=counts["error"],
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse, summary="Get a single incident")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    record = db.get(IncidentRecord, incident_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id!r} not found")
    return record


@router.delete("/incidents/{incident_id}", summary="Delete an incident record")
def delete_incident(incident_id: str, db: Session = Depends(get_db)):
    record = db.get(IncidentRecord, incident_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id!r} not found")
    db.delete(record)
    db.commit()
    return {"deleted": incident_id}
