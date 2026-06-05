from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel


class Base(DeclarativeBase):
    pass


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

    # AI-generated fields
    summary = Column(Text)
    category = Column(String)
    urgency_score = Column(Float)
    next_actions = Column(JSON)
    process_gaps = Column(JSON)
    triage_status = Column(String, default="pending")  # pending | processing | done | error
    triage_error = Column(Text, nullable=True)
    triaged_at = Column(DateTime, nullable=True)


# --- Pydantic schemas ---

class IncidentBase(BaseModel):
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


class TriageResult(BaseModel):
    summary: str
    category: str
    urgency_score: float
    next_actions: list[str]
    process_gaps: list[str]


class IncidentResponse(IncidentBase):
    summary: Optional[str] = None
    category: Optional[str] = None
    urgency_score: Optional[float] = None
    next_actions: Optional[list[str]] = None
    process_gaps: Optional[list[str]] = None
    triage_status: str = "pending"
    triage_error: Optional[str] = None
    triaged_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    uploaded: int
    skipped: int
    incident_ids: list[str]


class TriageSummary(BaseModel):
    total: int
    done: int
    pending: int
    error: int
