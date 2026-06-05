import json
import os
from openai import OpenAI
from app.models.incident import IncidentRecord, TriageResult

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def triage_incident(incident: IncidentRecord) -> TriageResult:
    prompt = f"""You are an expert SRE and incident manager. Analyze the following incident and return a JSON object.

Incident:
- ID: {incident.id}
- Title: {incident.title}
- Description: {incident.description or "No description provided"}
- Reported by: {incident.reported_by or "Unknown"}
- Assigned to: {incident.assigned_to or "Unassigned"}
- Status: {incident.status or "Unknown"}
- Priority: {incident.priority or "Unknown"}
- System: {incident.system or "Unknown"}
- Tags: {incident.tags or "None"}
- Created at: {incident.created_at}
- Resolved at: {incident.resolved_at or "Not resolved"}

Return ONLY a valid JSON object with exactly these fields:
{{
  "summary": "2-3 sentence business-readable summary of the incident and its impact",
  "category": "one of: access_issue | deployment_issue | data_issue | configuration_issue | performance_issue | security_issue | compliance_issue | infrastructure_issue | unknown",
  "urgency_score": <float 0.0–10.0 based on business impact, customer exposure, SLA risk, and time sensitivity>,
  "next_actions": ["action 1", "action 2", "action 3"],
  "process_gaps": ["gap 1", "gap 2"]
}}

For next_actions: provide 2–4 concrete, immediately actionable steps an engineer or manager should take.
For process_gaps: identify missing ownership, incomplete metadata, SLA risks, compliance concerns, or poor incident hygiene. Return an empty list if none found.
For urgency_score: 9–10 = business-critical with customer/revenue/compliance impact right now; 7–8 = high impact, needs same-day resolution; 5–6 = moderate, resolve within 24–48h; 3–4 = low, schedule for next sprint; 1–2 = informational."""

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    data = json.loads(response.choices[0].message.content)

    return TriageResult(
        summary=data["summary"],
        category=data["category"],
        urgency_score=float(data["urgency_score"]),
        next_actions=data["next_actions"],
        process_gaps=data.get("process_gaps", []),
    )
