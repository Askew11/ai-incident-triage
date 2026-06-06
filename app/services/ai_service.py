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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classify_incident",
            "description": "Classify the incident into a category based on its details.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
        {
        "type": "function",
        "function": {
            "name": "score_urgency",
            "description": "Score the urgency of the incident from 0 to 10 and write a summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The category previously determined by classify_incident."
                    }
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_actions",
            "description": "Recommend next actions to resolve the incident.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "urgency_score": {"type": "number"}
                },
                "required": ["category", "urgency_score"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalize_triage",
            "description": "Call this when you have enough information to complete the triage. Pass all final results as arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "category": {"type": "string"},
                    "urgency_score": {"type": "number"},
                    "next_actions": {"type": "array", "items": {"type": "string"}},
                    "process_gaps": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["summary", "category", "urgency_score", "next_actions", "process_gaps"]
            }
        }
    }                                                                                                                                                     
]

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

def _dispatch_tool(tool_name: str, args: dict, incident: IncidentRecord) -> str:
    if tool_name == "classify_incident":
        return json.dumps({"category": classify_incident(incident)})
    elif tool_name == "score_urgency":
        urgency_score, summary = score_urgency(incident, args["category"])
        return json.dumps({"urgency_score": urgency_score, "summary": summary})
    elif tool_name == "recommend_actions":
        actions = recommend_actions(incident, args["category"], args["urgency_score"])
        return json.dumps({"next_actions": actions})
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

def triage_incident(incident: IncidentRecord) -> TriageResult:
    messages = [
        {
            "role": "system",
            "content": (
                f"You are an IT incident triage agent. Use the available tools to classify, "
                f"score, and recommend actions for the incident. Valid categories: {CATEGORIES}. "
                f"When you have all the information you need, call finalize_triage."
            ),
        },
        {"role": "user", "content": _incident_context(incident)},
    ]

    for _ in range(10):
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            tools=TOOLS,
            messages=messages,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            raise RuntimeError("Agent stopped without calling finalize_triage")

        messages.append(message)

        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)

            if tool_call.function.name == "finalize_triage":
                return TriageResult(**args)

            result = _dispatch_tool(tool_call.function.name, args, incident)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    raise RuntimeError("Agent did not finalize triage within 10 steps")