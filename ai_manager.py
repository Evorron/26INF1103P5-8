import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Define default API URL endpoint and specific AI model to use
DEFAULT_ENDPOINT = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/interactions").strip()
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

SYSTEM_INSTRUCTIONS = """
You are Hawker AI, an intelligent F&B demand forecasting assistant.
Analyze the provided historical sales records and future context for the food item.
Return ONLY a valid JSON object matching the requested schema.
""".strip()

# Defining the exact structure of the expected response from the AI
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "demand_impact_factor": {"type": "number"},                                   # demand_impact_factor: Numerical factor indicating the expected impact on demand (eg. 1.0 for norm day, 0.8 if heavy rain is expected)
        "context_assessment": {"type": "string"},                                     # context_assessment: reasoning behind the demand impact factor
        "confidence_score": {"type": "string", "enum": ["high", "medium", "low"]},    # confidence_score: how sure the AI is about its own prediction
        "factors_considered": {"type": "array", "items": {"type": "string"}},         # factors_considered: list of factors that AI looked at to make its decision
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

# Get API key from environment variables
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

# Safety fallback response in case of API failure or missing key
    fallback_response = {
        "status": "fallback",
        "demand_impact_factor": 1.0,
        "context_assessment": "Gemini API unavailable or key unconfigured. Triggering historical median baseline.",
        "confidence_score": "low",
        "factors_considered": ["API Connection Unavailable"]
    }
    
# If no key found, log warning and return fallback response
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
            "schema": RESPONSE_SCHEMA,          # Forces AI to obey schema rules
        },
        "store": False,
    }

# Set up HTTP headers for the API request, including authentication
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
# Send POST request to the Gemini API endpoint with 20 seconds timeout limit
        response = requests.post(DEFAULT_ENDPOINT, headers=headers, json=request_body, timeout=20)

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
                    
# Returns error code & message if the API response is not successful and return fallback response
        print(f"\n[AI Manager Error] HTTP {response.status_code}: {response.text}")
        return fallback_response

# Catch network crashes or timeout errors and return fallback response
    except Exception as e:
        print(f"\n[AI Manager Exception] Failed to reach Gemini API: {e}")
        return fallback_response