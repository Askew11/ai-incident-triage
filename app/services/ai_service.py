# PERSON B — Intelligence track
from app.models.incident import IncidentRecord


class TriageResult:
    """
    TODO (Person B): Replace this with a proper Pydantic model.

    Fields:
    - summary: str         — 2-3 sentence business-readable explanation
    - category: str        — one of the categories listed in the prompt
    - urgency_score: float — 0.0 to 10.0
    - next_actions: list[str]
    - process_gaps: list[str]
    """
    pass


def triage_incident(incident: IncidentRecord) -> TriageResult:
    """
    Call the OpenAI API to triage the incident and return a TriageResult.

    Steps to implement:
    1. Build a prompt that includes all relevant incident fields
    2. Call the OpenAI chat completions API with response_format={"type": "json_object"}
    3. Parse the JSON response into a TriageResult
    4. Return it

    The prompt should ask the model to return exactly these fields:
    {
      "summary": "...",
      "category": "access_issue | deployment_issue | data_issue | configuration_issue | performance_issue | security_issue | compliance_issue | infrastructure_issue",
      "urgency_score": 0.0-10.0,
      "next_actions": ["...", "..."],
      "process_gaps": ["...", "..."]
    }

    Use model: "gpt-4o-mini", temperature: 0.2
    """
    raise NotImplementedError
