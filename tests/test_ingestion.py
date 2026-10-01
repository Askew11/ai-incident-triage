import io
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.incident import IncidentRecord
from app.services.incident_service import ingest_csv


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_ingest_valid_csv(db):
    csv_data = "id,title,description\nINC-001,Test incident,Something broke\n"
    file = io.BytesIO(csv_data.encode())

    result = ingest_csv(file, db)

    assert result.uploaded == 1
    assert result.skipped == 0
    assert "INC-001" in result.incident_ids
    
def test_ingest_skips_duplicates(db):
    csv_data = "id,title\nINC-001,Test incident\n"
    file = io.BytesIO(csv_data.encode())

    ingest_csv(file, db)

    file2 = io.BytesIO(csv_data.encode())
    result = ingest_csv(file2, db)

    assert result.uploaded == 0
    assert result.skipped == 1
    
def test_ingest_missing_columns_raises(db):
    csv_data = "name,description\nSome incident,Something broke\n"
    file = io.BytesIO(csv_data.encode())

    with pytest.raises(ValueError):
        ingest_csv(file, db)
        
def test_ingest_partial_duplicate(db):
    existing = IncidentRecord(id="INC-001", title="Already exists")
    db.add(existing)
    db.commit()

    csv_data = "id,title\nINC-001,Already exists\nINC-002,New incident\n"
    file = io.BytesIO(csv_data.encode())

    result = ingest_csv(file, db)

    assert result.uploaded == 1
    assert result.skipped == 1
    assert "INC-002" in result.incident_ids
    
def test_upload_bad_csv_returns_400(db):
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    csv_data = "name,description\nSome incident,Something broke\n"
    file = io.BytesIO(csv_data.encode())

    response = client.post(
        "/api/v1/incidents/upload",
        files={"file": ("bad.csv", file, "text/csv")},
    )

    assert response.status_code == 400
    assert "missing required columns" in response.json()["detail"]
    

def test_rules_detect_missing_fields(db):
    from app.services.rules_service import detect_process_gaps
    
    record = IncidentRecord(id="INC-TEST", title="Test", description="short")
    gaps = detect_process_gaps(record)
    
    assert any("assignee" in g.lower() for g in gaps)
    assert any("priority" in g.lower() for g in gaps)
    assert any("vague" in g.lower() for g in gaps)

def test_ingest_blank_fields_stored_as_none(db):
    csv_data = (
        "id,title,description,assigned_to,priority\n"
        "INC-001,Login failure,Users unable to log in after deploy,,\n"
    )
    ingest_csv(io.BytesIO(csv_data.encode()), db)

    record = db.get(IncidentRecord, "INC-001")
    assert record.assigned_to is None
    assert record.priority is None


def test_ingest_parses_timestamps(db):
    csv_data = (
        "id,title,created_at,resolved_at\n"
        "INC-001,Has dates,2026-06-05 11:30:00,\n"
        "INC-002,Bad date,not-a-date,\n"
    )
    ingest_csv(io.BytesIO(csv_data.encode()), db)

    assert db.get(IncidentRecord, "INC-001").created_at == datetime(2026, 6, 5, 11, 30)
    assert db.get(IncidentRecord, "INC-001").resolved_at is None
    assert db.get(IncidentRecord, "INC-002").created_at is None


def test_rules_flag_gaps_on_ingested_incident(db):
    from app.services.rules_service import detect_process_gaps

    csv_data = (
        "id,title,description,assigned_to,status,priority,created_at\n"
        "INC-001,Old unowned ticket,Rollback requested but nobody picked it up,,Open,,2020-01-01 09:00:00\n"
    )
    ingest_csv(io.BytesIO(csv_data.encode()), db)

    gaps = detect_process_gaps(db.get(IncidentRecord, "INC-001"))
    assert any("assignee" in g.lower() for g in gaps)
    assert any("priority" in g.lower() for g in gaps)
    assert any("open for" in g.lower() for g in gaps)
