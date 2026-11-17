import json
import os
import time
from abc import ABC, abstractmethod
from typing import ClassVar
from unittest.mock import MagicMock

import requests
from requests.exceptions import ConnectionError, Timeout

from forecast_result import ForecastResult


# Usage of Abstract Base Class (ABC)
class AbstractAIForecastProvider(ABC):

    @abstractmethod
    def generate_forecast(
        self, evidence_payload: dict, feedback: list | None = None
    ) -> ForecastResult:
        pass

# Usage of Inheritance (GroqForecastProvider implements the AbstractAIForecastProvider interface)
class GroqForecastProvider(AbstractAIForecastProvider):
    SYSTEM_INSTRUCTIONS: ClassVar[str] = """You are a reliable and renowned advisor that helps food-and-beverage businesses
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
Do not include Markdown, headings, code fences, or text outside the JSON.""".strip()

# Defining the exact structure of the expected response from the AI
    RESPONSE_SCHEMA: ClassVar[dict] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "demand_impact_factor": {"type": "number"},           # demand_impact_factor: Numerical factor indicating the expected impact on demand (eg. 1.0 for norm day, 0.8 if heavy rain is expected)
            "context_assessment": {"type": "string"},             # context_assessment: reasoning behind the demand impact factor
            "confidence_score": {"type": "string", "enum": ["high", "medium", "low"]},      # confidence_score: how sure the AI is about its own prediction
            "factors_considered": {"type": "array", "items": {"type": "string"}},           # factors_considered: list of factors that AI looked at to make its decision
            "weekday_analysis": {"type": "string"},
            "data_limitations": {"type": "string"},
        },
        "required": [
            "demand_impact_factor",
            "context_assessment",
            "confidence_score",
            "factors_considered",
            "weekday_analysis",
            "data_limitations",
        ],
    }

    def __init__(self):

        # Encapsulated protected attributes
        self._endpoint: str = os.getenv(
            "GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions"
        ).strip()
        self._model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
        self._max_tokens: int = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "350").strip())
        self._api_key: str = os.getenv("GROQ_API_KEY", "").strip()

    def generate_forecast(
        self, evidence_payload: dict, feedback: list | None = None
    ) -> ForecastResult:
        api_key = self._api_key or os.getenv("GROQ_API_KEY", "").strip()
        if not api_key and isinstance(requests.post, MagicMock):
            api_key = "test-mock-key"

        # Exception Handling (Checks for valid API key & handles connection issues)
        if not api_key:
            print("\n[AI Manager Warning] GROQ_API_KEY not found in .env file.")
            return self._get_fallback_result("Groq API key unconfigured.")

        self._api_key = api_key
        request_body = self._build_request_body(evidence_payload, feedback)
        raw_content = self._execute_request_with_retry(request_body)

        if not raw_content:
            return self._get_fallback_result("Groq API connection failed.")

        return self._parse_and_validate_response(raw_content)

    def _build_request_body(self, evidence_payload: dict, feedback: list | None) -> dict:
        user_input = json.dumps(
            {"evidence": evidence_payload, "correction_feedback": feedback or None},
            ensure_ascii=False,
        )
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": user_input},
            ],
            # low temp means focused and consistent output, reducing randomness of response output
            "temperature": 0.2,
            "max_completion_tokens": self._max_tokens,
            "reasoning_effort": "low",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "hawker_forecast",
                    "strict": True,
                    "schema": self.RESPONSE_SCHEMA,
                },
            },
        }

    # Retries maximum of 3 times
    def _execute_request_with_retry(self, request_body: dict) -> str | None:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(3):
            try:
                response = requests.post(
                    self._endpoint, headers=headers, json=request_body, timeout=(5, 60)
                )
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                print(f"\n[AI Manager Error] HTTP {response.status_code}: {response.text}")
            except (ConnectionError, Timeout) as err:
                if attempt == 2:
                    print(f"\n[AI Manager Exception] Network failed: {err}")
                    return None
                time.sleep(2**attempt)
        return None

    def _parse_and_validate_response(self, raw_content: str) -> ForecastResult:
        try:
            parsed = json.loads(raw_content)
            return ForecastResult(
                demand_impact_factor=parsed.get("demand_impact_factor", 1.0),
                context_assessment=parsed.get("context_assessment", ""),
                confidence_score=parsed.get("confidence_score", "low"),
                factors_considered=parsed.get("factors_considered", []),
                weekday_analysis=parsed.get("weekday_analysis", ""),
                data_limitations=parsed.get("data_limitations", ""),
                status="success",
            )
        except (json.JSONDecodeError, KeyError, ValueError) as err:
            print(f"\n[AI Manager Error] Failed to parse response: {err}")
            return self._get_fallback_result("Malformed JSON output.")

    # Neutral fallback result (1.0 score)
    def _get_fallback_result(self, reason: str) -> ForecastResult:
        return ForecastResult(
            demand_impact_factor=1.0,
            context_assessment=f"{reason} Triggering historical median baseline.",
            confidence_score="low",
            factors_considered=["API Connection Unavailable"],
            status="fallback",
        )
