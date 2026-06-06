from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.incident import IncidentRecord
from app.schemas.incident import IncidentResponse, UploadResponse
from app.services import incident_service


router = APIRouter(prefix="/api/v1", tags=["incidents"])


# ── PERSON A — POST /upload ───────────────────────────────────────────────────

# TODO (Person A): Implement POST /incidents/upload
# - Accept a CSV file upload
# - Call incident_service.ingest_csv(file.file, db)
# - Optionally kick off background triage for each uploaded incident
# - Return UploadResponse
@router.post("/incidents/upload", response_model=UploadResponse)
def upload_incidents(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        result =  incident_service.ingest_csv(file.file, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    
    for incident_id in result.incident_ids:
        background_tasks.add_task(incident_service.run_triage, incident_id, db)
    return result

# ── PERSON B — GET /incidents and GET /incidents/{id} ────────────────────────

@router.get("/incidents", response_model=list[IncidentResponse])
def list_incidents(
    status: Optional[str] = None,
    category: Optional[str] = None,
    triage_status: Optional[str] = None,
    min_urgency: Optional[float] = None,
    db: Session = Depends(get_db),
):
    query = db.query(IncidentRecord)

    if status is not None:
        query = query.filter(IncidentRecord.status == status)
    if category is not None:
        query = query.filter(IncidentRecord.category == category)
    if triage_status is not None:
        query = query.filter(IncidentRecord.triage_status == triage_status)
    if min_urgency is not None:
        query = query.filter(IncidentRecord.urgency_score >= min_urgency)

    return query.order_by(IncidentRecord.urgency_score.desc().nullslast()).all()


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = (
        db.query(IncidentRecord)
        .filter(IncidentRecord.id == incident_id)
        .first()
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/incidents/{incident_id}/retriage", response_model=IncidentResponse)
def retriage_incident(incident_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    incident = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    background_tasks.add_task(incident_service.run_triage, incident_id, db)
    return incident




