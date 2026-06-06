import io
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