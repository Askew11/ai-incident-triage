from app.models.incident import IncidentRecord
from datetime import datetime

def detect_process_gaps(record: IncidentRecord) -> list[str]:
    gaps = []
    
    if not record.assigned_to:
        gaps.append("No assignee - incident is unowned")
        
    if not record.priority:
        gaps.append("No priority set")
    
    if not record.description or len(record.description.strip()) < 20:
        gaps.append("Description is too vague or missing")
    
    if record.created_at:
        age = (datetime.utcnow() - record.created_at).days
        if age > 7 and record.status != "Resolved":
            gaps.append(f"Incident has been open for {age} days without resolution")
    
    return gaps