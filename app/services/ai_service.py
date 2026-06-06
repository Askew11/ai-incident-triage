# PERSON B — Intelligence track
import os
import json
from openai import OpenAI
from pydantic import BaseModel
from app.models.incident import IncidentRecord

_client = None


def get_client() -> OpenAI:
    """Create the OpenAI client on first use (not at import time).

    Building it lazily means importing this module never requires an API key —
    only actually calling the API does. This keeps tests (which mock the API)
    from crashing on import when no key is set.
    """
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


CATEGORIES = "access_issue, deployment_issue, data_issue, configuration_issue, performance_issue, security_issue, compliance_issue, infrastructure_issue"

class TriageResult(BaseModel):
    summary: str
    category: str
    urgency_score: float
    next_actions: list[str]
    process_gaps: list[str]

def _incident_context(incident: IncidentRecord) -> str:
    return f"""Incident ID: {incident.id}
Title: {incident.title}
Description: {incident.description}
Reported by: {incident.reported_by}
Assigned to: {incident.assigned_to}
Status: {incident.status}
Priority: {incident.priority}
System: {incident.system}
Tags: {incident.tags}"""


def _call(system: str, user: str) -> dict:
    response = get_client().chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)


def classify_incident(incident: IncidentRecord) -> str:
    result = _call(
        system=f"You are an IT incident classifier. Respond with JSON: {{\"category\": \"<one of: {CATEGORIES}>\"}}",
        user=_incident_context(incident),
    )
    return result["category"]


def score_urgency(incident: IncidentRecord, category: str) -> float:
    result = _call(
        system=f"You are an IT urgency scorer. This incident is categorized as '{category}'. Respond with JSON: {{\"urgency_score\": <0.0-10.0>, \"summary\": \"<2-3 sentence explanation>\"}}",
        user=_incident_context(incident),
    )
    return result["urgency_score"], result["summary"]


def recommend_actions(incident: IncidentRecord, category: str, urgency_score: float) -> list[str]:
    result = _call(
        system=f"You are an IT incident responder. Category: '{category}', Urgency: {urgency_score}/10. Respond with JSON: {{\"next_actions\": [\"...\"]}}",
        user=_incident_context(incident),
    )
    return result["next_actions"]


def triage_incident(incident: IncidentRecord) -> TriageResult:
    category = classify_incident(incident)
    urgency_score, summary = score_urgency(incident, category)
    next_actions = recommend_actions(incident, category, urgency_score)

    return TriageResult(
        summary=summary,
        category=category,
        urgency_score=urgency_score,
        next_actions=next_actions,
        process_gaps=[],
    )