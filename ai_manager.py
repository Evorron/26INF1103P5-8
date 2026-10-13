import json
import os
import requests
from dotenv import load_dotenv
import time
from requests.exceptions import ConnectionError, Timeout


# Load environment variables from .env
load_dotenv(override=True)

# Define default API URL endpoint and specific AI model to use
DEFAULT_ENDPOINT = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/interactions").strip()
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()


## System instructions for the AI model to follow when generating forecasts.
SYSTEM_INSTRUCTIONS = """
You are a reliable and renowned advisor that helps food-and-beverage businesses
estimate how many portions to prepare for one food item.

Your role is to analyse only the supplied historical sales records and the
user-provided future context. Your role is not to choose the final quantity;
the application calculates and validates the final recommendation locally.

Use the historical data to suggest one positive demand-impact factor:

- A factor near 1.00 means demand is rather neutral as compared to historical patterns.
- A factor above 1.00 means demand may increase.
- A factor below 1.00 means demand may decrease.

Use only the evidence provided in the request. Do not invent or assume:
weather, public holidays, nearby events, promotions, market trends, or
customer behaviour that was not supplied.

When future context is provided, analyse and interpret the supplied information, before explaining how it may affect demand. 
You may interpret patterns in the supplied sales records and explain how
the user-provided future context may affect demand.

Do not invent or claim facts that are not present in the supplied data.
Do not state that weather, public holidays, promotions, events, or market
conditions will affect demand unless the user explicitly supplied them.

Do not choose the final number of portions to prepare. Return only a
demand-impact factor and supporting analysis. The application calculates,
limits, and validates the final recommendation using local historical data.
When no future context is provided, indicate that the recommendation is mainly based on
historical sales.

Explain the target-weekday pattern when relevant. If there are insufficient records
for the target weekday, clearly state that weekday evidence is limited.

Use concise, plain business language suitable for a food stall owner that is easy to understand. Be
honest about uncertainty and limited historical data. Do not make claims that
cannot be supported by the supplied records.

Return only a valid JSON object that follows the required response schema.
Do not include Markdown, headings, code fences, or text outside the JSON.
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
        "weekday_analysis": {"type": "string"},
        "data_limitations": {"type": "string"},
    },
    "required": ["demand_impact_factor", "context_assessment", "confidence_score", "factors_considered", "weekday_analysis", "data_limitations",],
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

# Set up HTTP headers for the API request including authentication
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
# Send POST request to the Gemini API endpoint with 30 seconds timeout limit
        for attempt in range(3):
            try:
                response = requests.post(
                    DEFAULT_ENDPOINT,
                    headers=headers,
                    json=request_body,
                    timeout=(5, 60),
                )
                break

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as error:
                if attempt == 2:
                    print(
                        "\n[AI Manager Exception] "
                        f"Failed to reach Gemini API: {error}"
                    )
                    return fallback_response

                wait_seconds = 2 ** attempt
                print(
                    f"\nGemini is slow. Retrying in "
                    f"{wait_seconds} second(s)..."
                )
                time.sleep(wait_seconds)

        if response.status_code == 200:
            result_body = response.json()
# Extract text safely from the Interactions API steps structure
            steps = result_body.get("steps", [])
            for step in steps:
                content_list = step.get("content", [])
                for content in content_list:
                    if (
                        content.get("type") == "text"
                        and "text" in content
                    ):
                        parsed_json = json.loads(content["text"])
                        parsed_json["status"] = "success"
                        return parsed_json
                        

# Returns error code & message if the API response is not successful and return fallback response
        print(
            f"\n[AI Manager Error] "
            f"HTTP {response.status_code}: {response.text}"
        )
        return fallback_response

# Catch network crashes or timeout errors and return fallback response
    except Exception as error:
        print(
            "\n[AI Manager Exception] "
            f"Failed to process Gemini API response: {error}"
        )
        return fallback_response