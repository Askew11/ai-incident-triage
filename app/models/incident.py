# SHARED — do not edit
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, JSON
from app.database import Base


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    reported_by = Column(String)
    assigned_to = Column(String)
    status = Column(String)
    priority = Column(String)
    system = Column(String)
    tags = Column(String)
    created_at = Column(DateTime)
    resolved_at = Column(DateTime, nullable=True)

    # Filled in by AI triage (Person B)
    summary = Column(Text)
    category = Column(String)
    urgency_score = Column(Float)
    next_actions = Column(JSON)
    process_gaps = Column(JSON)
    triage_status = Column(String, default="pending")  # pending | done | error
    triage_error = Column(Text, nullable=True)
    triaged_at = Column(DateTime, nullable=True)
    triage_steps = Column(JSON, nullable=True)
