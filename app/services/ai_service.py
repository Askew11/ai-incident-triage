# PERSON B — Intelligence track
import os
import json
from openai import OpenAI
from pydantic import BaseModel
from app.models.incident import IncidentRecord

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert IT incident analyst.
Analyze the incident the user gives you and respond with a JSON object containing EXACTLY these fields:
- summary: a 2-3 sentence business-readable explanation of the incident
- category: choose exactly ONE of: access_issue, deployment_issue, data_issue, configuration_issue, performance_issue, security_issue, compliance_issue, infrastructure_issue
- urgency_score: a number from 0.0 (trivial) to 10.0 (critical), based on impact and priority
- next_actions: a list of specific, actionable next steps
- process_gaps: a list of missing info or process problems (empty list if none)

Respond with ONLY the JSON object, nothing else."""


class TriageResult(BaseModel):
    summary: str                # 2-3 sentence business-readable explanation
    category: str               # one of the categories listed in the prompt
    urgency_score: float        # 0.0 to 10.0
    next_actions: list[str]
    process_gaps: list[str]


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
    user_message = f"""Incident ID: {incident.id}
Title: {incident.title}
Description: {incident.description}
Reported by: {incident.reported_by}
Assigned to: {incident.assigned_to}
Status: {incident.status}
Priority: {incident.priority}
System: {incident.system}
Tags: {incident.tags}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    data = json.loads(response.choices[0].message.content)
    return TriageResult(**data)
