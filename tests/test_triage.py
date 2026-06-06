import json
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.models.incident import IncidentRecord
from app.services import ai_service, incident_service
from app.services.ai_service import TriageResult


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def make_incident():
    return IncidentRecord(
        id="INC-TEST",
        title="Login failure",
        description="Users unable to log in after latest deployment",
        reported_by="Jane Smith",
        assigned_to="Bob",
        status="Open",
        priority="High",
        system="Auth Service",
        tags="login",
    )


def make_tool_response(name, arguments, tool_id="call_1"):
    tool_call = MagicMock()
    tool_call.function.name = name
    tool_call.function.arguments = json.dumps(arguments)
    tool_call.id = tool_id

    message = MagicMock()
    message.tool_calls = [tool_call]

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message = message
    return response


# ── ai_service tests ──────────────────────────────────────────────────────────

def test_triage_incident_returns_valid_result(db):
    incident = make_incident()

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        make_tool_response("classify_incident", {}),
        make_tool_response("score_urgency", {"category": "access_issue"}),
        make_tool_response("recommend_actions", {"category": "access_issue", "urgency_score": 8.0}),
        make_tool_response("finalize_triage", {
            "summary": "Test summary",
            "category": "access_issue",
            "urgency_score": 8.0,
            "next_actions": ["Roll back deployment"],
            "process_gaps": [],
        }),
    ]

    with patch("app.services.ai_service.get_client", return_value=mock_client), \
         patch("app.services.ai_service.classify_incident", return_value="access_issue"), \
         patch("app.services.ai_service.score_urgency", return_value=(8.0, "Test summary")), \
         patch("app.services.ai_service.recommend_actions", return_value=["Roll back deployment"]), \
         patch("app.services.ai_service.lookup_similar_incidents", return_value=[]):

        result = ai_service.triage_incident(incident, db)

    assert isinstance(result, TriageResult)
    assert result.category == "access_issue"
    assert result.urgency_score == 8.0
    assert result.summary == "Test summary"
    assert result.next_actions == ["Roll back deployment"]


def test_triage_incident_records_steps(db):
    incident = make_incident()

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        make_tool_response("classify_incident", {}),
        make_tool_response("finalize_triage", {
            "summary": "Test summary",
            "category": "access_issue",
            "urgency_score": 8.0,
            "next_actions": ["Fix it"],
            "process_gaps": [],
        }),
    ]

    with patch("app.services.ai_service.get_client", return_value=mock_client), \
         patch("app.services.ai_service.classify_incident", return_value="access_issue"), \
         patch("app.services.ai_service.lookup_similar_incidents", return_value=[]):

        result = ai_service.triage_incident(incident, db)

    tools_called = [s["tool"] for s in result.triage_steps]
    assert "classify_incident" in tools_called
    assert "finalize_triage" in tools_called


def test_triage_incident_raises_if_no_finalize(db):
    incident = make_incident()

    mock_client = MagicMock()
    message = MagicMock()
    message.tool_calls = None
    mock_client.chat.completions.create.return_value.choices = [MagicMock()]
    mock_client.chat.completions.create.return_value.choices[0].message = message

    with patch("app.services.ai_service.get_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="finalize_triage"):
            ai_service.triage_incident(incident, db)


# ── incident_service tests ────────────────────────────────────────────────────

def test_run_triage_saves_result_to_db(db):
    incident = IncidentRecord(id="INC-SAVE", title="Save test", description="Test description")
    db.add(incident)
    db.commit()

    mock_result = TriageResult(
        summary="Mock summary",
        category="data_issue",
        urgency_score=7.0,
        next_actions=["Fix the pipeline"],
        process_gaps=[],
        triage_steps=[{"step": 1, "tool": "finalize_triage"}],
    )

    with patch("app.services.ai_service.triage_incident", return_value=mock_result):
        incident_service.run_triage("INC-SAVE", db)

    db.refresh(incident)
    assert incident.triage_status == "done"
    assert incident.category == "data_issue"
    assert incident.urgency_score == 7.0
    assert incident.summary == "Mock summary"
    assert incident.triage_steps is not None


def test_run_triage_sets_error_on_failure(db):
    incident = IncidentRecord(id="INC-ERR", title="Error test", description="Test description")
    db.add(incident)
    db.commit()

    with patch("app.services.ai_service.triage_incident", side_effect=RuntimeError("OpenAI timeout")):
        incident_service.run_triage("INC-ERR", db)

    db.refresh(incident)
    assert incident.triage_status == "error"
    assert "OpenAI timeout" in incident.triage_error


def test_run_triage_raises_for_unknown_incident(db):
    with pytest.raises(ValueError, match="not found"):
        incident_service.run_triage("INC-MISSING", db)


# ── retriage endpoint tests ───────────────────────────────────────────────────

def _make_test_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_retriage_endpoint_returns_200():
    from fastapi.testclient import TestClient
    from app.main import app

    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    test_db = TestSession()

    incident = IncidentRecord(id="INC-RETRIAGE", title="Retriage test", description="Test")
    test_db.add(incident)
    test_db.commit()

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    with patch("app.services.incident_service.run_triage"):
        response = client.post("/api/v1/incidents/INC-RETRIAGE/retriage")

    app.dependency_overrides.clear()
    test_db.close()

    assert response.status_code == 200


def test_retriage_endpoint_returns_404():
    from fastapi.testclient import TestClient
    from app.main import app

    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    test_db = TestSession()

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.post("/api/v1/incidents/INC-NONEXISTENT/retriage")

    app.dependency_overrides.clear()
    test_db.close()

    assert response.status_code == 404
