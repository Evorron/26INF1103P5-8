import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.ai_factor_strategy import AIFactorStrategy
from ai.ai_manager import AIManager
from ai.ai_provider import GroqForecastProvider
from logic.forecast_result import ForecastResult


class StubProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate_forecast(self, payload, feedback=None):
        self.calls.append((payload, feedback))
        return self.result


class TestAIManager(unittest.TestCase):
    def test_manager_delegates_to_injected_provider_and_serializes_result(self):
        provider = StubProvider(
            ForecastResult(1.2, "Context assessed", "high", ["history"])
        )
        manager = AIManager(provider=provider)
        payload = {"item": "Laksa"}
        result = manager.generate_forecast(payload, feedback=["correction"])

        self.assertEqual(provider.calls, [(payload, ["correction"])])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["demand_impact_factor"], 1.2)
        self.assertEqual(result["factors_considered"], ["history"])


class TestGroqProviderOffline(unittest.TestCase):
    def setUp(self):
        self.provider = GroqForecastProvider()
        self.provider._api_key = "unit-test-key"

    @patch("ai.ai_provider.requests.post")
    def test_successful_http_response_is_parsed_and_request_has_expected_schema(self, mock_post):
        content = {
            "demand_impact_factor": 1.1,
            "context_assessment": "Based on recorded sales",
            "confidence_score": "medium",
            "factors_considered": ["sales history"],
            "weekday_analysis": "Limited weekday history",
            "data_limitations": "Few records",
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": json.dumps(content)}}]
        }

        result = self.provider.generate_forecast({"evidence": "sample"})

        self.assertEqual(result.status, "success")
        self.assertAlmostEqual(result.demand_impact_factor, 1.1)
        self.assertEqual(result.confidence_score, "medium")
        self.assertEqual(mock_post.call_count, 1)
        request = mock_post.call_args.kwargs["json"]
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertIn('"evidence": "sample"', request["messages"][1]["content"])

    def test_malformed_provider_content_returns_neutral_fallback(self):
        result = self.provider._parse_and_validate_response("not-json")

        self.assertEqual(result.status, "fallback")
        self.assertEqual(result.demand_impact_factor, 1.0)
        self.assertIn("Malformed JSON", result.context_assessment)

    @patch.dict("os.environ", {}, clear=True)
    @patch("ai.ai_provider.requests.post")
    def test_missing_api_key_falls_back_without_network_request(self, mock_post):
        self.provider._api_key = ""
        result = self.provider.generate_forecast({})

        self.assertEqual(result.status, "fallback")
        self.assertEqual(result.demand_impact_factor, 1.0)
        mock_post.assert_not_called()

    @patch("ai.ai_provider.time.sleep")
    @patch("ai.ai_provider.requests.post")
    def test_network_timeouts_are_retried_three_times_then_fall_back(self, mock_post, mock_sleep):
        from requests.exceptions import Timeout

        mock_post.side_effect = Timeout("offline")
        result = self.provider.generate_forecast({})

        self.assertEqual(result.status, "fallback")
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual([call.args[0] for call in mock_sleep.call_args_list], [1, 2])


class TestAIFactorStrategy(unittest.TestCase):
    @patch("ai.ai_factor_strategy.ai_manager.generate_forecast")
    def test_success_response_is_normalized_to_common_factor_result(self, generate):
        generate.return_value = {
            "status": "success",
            "demand_impact_factor": "1.25",
            "confidence_score": "HIGH",
            "factors_considered": [" history ", "context", "weekday", "extra"],
            "context_assessment": " Demand may rise. ",
            "weekday_analysis": " Weekday evidence is limited. ",
            "data_limitations": " Few records. ",
        }

        result = AIFactorStrategy().get_factor_result({"payload": True})

        self.assertEqual(result.factor, 1.25)
        self.assertEqual(result.confidence, "high")
        self.assertEqual(result.method, "gemini_ai")
        self.assertEqual(result.factors, ["history", "context", "weekday"])
        self.assertIn("Demand may rise.", result.reasoning)
        self.assertIn("Weekday evidence is limited.", result.reasoning)

    @patch("ai.ai_factor_strategy.ai_manager.generate_forecast")
    def test_failed_ai_status_returns_none_for_baseline_fallback(self, generate):
        generate.return_value = {"status": "fallback"}

        self.assertIsNone(AIFactorStrategy().get_factor_result({}))


class TestActivityLogger(unittest.TestCase):
    def test_request_log_is_jsonl_and_omits_full_payload_by_default(self):
        from ai import activity_logger

        payload = {
            "forecast_request": {
                "user_name": "Test User",
                "food_item": "Laksa",
                "target_date": "2030-01-02",
                "future_context": None,
            },
            "historical_records": [{"portions_sold": 8}],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nested" / "activity.jsonl"
            activity_logger.initialise_log(path)
            activity_logger.log_request(path, "activity-1", "test-model", payload)
            entry = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(entry["event"], "groq_request_started")
        self.assertEqual(entry["historical_record_count"], 1)
        self.assertFalse(entry["future_context_provided"])
        self.assertNotIn("full_evidence_payload", entry)
        self.assertNotIn("api_key", entry)


if __name__ == "__main__":
    unittest.main()
