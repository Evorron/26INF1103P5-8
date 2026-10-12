"""
ai_manager.py - AI Processing Layer
100% procedural module for Hawker AI using the Interactions API and gemini-3.8-flash.
"""

import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DEFAULT_ENDPOINT = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/interactions").strip()
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

SYSTEM_INSTRUCTIONS = """
You are Hawker AI, an intelligent F&B demand forecasting assistant.
Analyze the provided historical sales records and future context for the food item.
Return ONLY a valid JSON object matching the requested schema.
""".strip()

RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "demand_impact_factor": {"type": "number"},
        "context_assessment": {"type": "string"},
        "confidence_score": {"type": "string", "enum": ["high", "medium", "low"]},
        "factors_considered": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["demand_impact_factor", "context_assessment", "confidence_score", "factors_considered"]
}


def generate_forecast(
    evidence_payload: dict,
    feedback: list | None = None,
    log_path=None,
    deadline=None
) -> dict:
    """
    Calls Gemini using the Interactions API endpoint and gemini-3.8-flash.
    Parses the steps structure returned by the v1beta interactions endpoint.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    fallback_response = {
        "status": "fallback",
        "demand_impact_factor": 1.0,
        "context_assessment": "Gemini API unavailable or key unconfigured. Triggering historical median baseline.",
        "confidence_score": "low",
        "factors_considered": ["API Connection Unavailable"]
    }

    if not api_key:
        print("\n[AI Manager Warning] GEMINI_API_KEY not found in .env file.")
        return fallback_response

    user_input = json.dumps(
        {"evidence": evidence_payload, "correction_feedback": feedback or None},
        ensure_ascii=False
    )

    request_body = {
        "model": DEFAULT_MODEL,
        "input": user_input,
        "system_instruction": SYSTEM_INSTRUCTIONS,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": RESPONSE_SCHEMA,
        },
        "store": False,
    }

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(DEFAULT_ENDPOINT, headers=headers, json=request_body, timeout=40)

        if response.status_code == 200:
            result_body = response.json()

            # Extract text safely from the Interactions API steps structure
            steps = result_body.get("steps", [])
            for step in steps:
                content_list = step.get("content", [])
                for content in content_list:
                    if content.get("type") == "text" and "text" in content:
                        parsed_json = json.loads(content["text"])
                        parsed_json["status"] = "success"
                        return parsed_json

        print(f"\n[AI Manager Error] HTTP {response.status_code}: {response.text}")
        return fallback_response

    except Exception as e:
        print(f"\n[AI Manager Exception] Failed to reach Gemini API: {e}")
        return fallback_response
