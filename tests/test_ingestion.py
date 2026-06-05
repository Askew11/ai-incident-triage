import io
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.incident import Base
from app.services.incident_service import ingest_csv

SAMPLE_CSV = """\
id,title,description,reported_by,assigned_to,status,priority,system,created_at
INC-TEST-1,Test incident,Something broke in prod,alice@test.com,bob@test.com,Open,High,auth-service,2026-06-05 09:00:00
INC-TEST-2,Another issue,Slow queries observed,,,Open,Medium,db,2026-06-04 08:00:00
"""


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_ingest_csv_uploads_records(db):
    result = ingest_csv(io.BytesIO(SAMPLE_CSV.encode()), db)
    assert result.uploaded == 2
    assert result.skipped == 0
    assert set(result.incident_ids) == {"INC-TEST-1", "INC-TEST-2"}


def test_ingest_csv_skips_duplicates(db):
    ingest_csv(io.BytesIO(SAMPLE_CSV.encode()), db)
    result = ingest_csv(io.BytesIO(SAMPLE_CSV.encode()), db)
    assert result.uploaded == 0
    assert result.skipped == 2


def test_ingest_csv_missing_required_column(db):
    bad_csv = b"title,description\nSome title,Some desc\n"
    with pytest.raises(ValueError, match="missing required columns"):
        ingest_csv(io.BytesIO(bad_csv), db)


def test_ingest_captures_process_gaps_no_assignee(db):
    from app.services.incident_service import _rule_based_gaps
    from app.models.incident import IncidentRecord
    record = IncidentRecord(id="X", title="Broken", assigned_to=None, reported_by="x@x.com",
                            description="Something is very broken right now", system="api", status="Open")
    gaps = _rule_based_gaps(record)
    assert any("assignee" in g.lower() for g in gaps)
