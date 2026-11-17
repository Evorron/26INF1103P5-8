from pathlib import Path
from uuid import uuid4

import activity_logger
from demand_factor_result import DemandFactorResult
from demand_factor_strategy import DemandFactorStrategy
from logic_manager_class import LogicManager

"""
Overall responsibility: Coordinates the steps required to produce a completed forecast.

Main components:
- ForecastCoordinator — controls the workflow.
- _logic — delegates domain operations to LogicManager.
- _factor_strategies — stores the ordered estimation approaches.
- _log_path / _model — retain audit configuration and metadata.
- generate_logged_forecast() — runs forecasting with request/result/error logging.
- _choose_factor_result() — accepts the first available strategy result.
- _build_response() — combines the result, quantity, confidence, advice, and evidence, then requests validation.
"""

class ForecastCoordinator:

    def __init__(self, logic: LogicManager, factor_strategies: list[DemandFactorStrategy], log_path: Path, model: str,):
        self._logic = logic
        self._factor_strategies = factor_strategies
        self._log_path = log_path
        self._model = model

    def generate_logged_forecast(self, request: dict, all_records: list[dict], log_path: Path | None = None) -> dict:
        history = self._logic.records_for_forecast(request, all_records)
        payload = self._logic.build_ai_payload(request, history)
        activity_id = str(uuid4())

        if log_path is None:
            log_path = self._log_path

        activity_logger.initialise_log(log_path)
        activity_logger.log_request(log_path, activity_id, self._model, payload)

        try:
            response = self.build_validated_forecast(request, history, payload)
        except (RuntimeError, ValueError, KeyError, TypeError) as error:
            activity_logger.log_error(log_path, activity_id, self._model, str(error), status = None, failure_type = "forecast_validation")
            raise

        activity_logger.log_response(log_path, activity_id, self._model, response)
        return response


    def build_validated_forecast(self, request: dict, historical_records: list[dict], evidence_payload: dict | None = None) -> dict:
        if evidence_payload is None:
            evidence_payload = self._logic.build_ai_payload(request, historical_records)

        factor_result = self._choose_factor_result(evidence_payload)
        return self._build_response(request, historical_records, factor_result)

    def _choose_factor_result(self, payload: dict) -> DemandFactorResult:
        for factor_strategy in self._factor_strategies:
            factor_result = factor_strategy.get_factor_result(payload)
            if factor_result is not None:
                return factor_result

        raise RuntimeError("No demand-factor result is available.")

    def _build_response(self, request: dict, historical_records: list[dict], factor_result: DemandFactorResult) -> dict:
        metrics = self._logic.calculate_evidence_metrics(historical_records, request["target_date"])
        sales = [record["portions_sold"] for record in historical_records]
        justification = None

        if request["future_context"].strip():
            justification = factor_result.context_justification


        uses_future_context = justification is not None
        quantity = self._logic.calculate_quantity(factor_result.factor, sales, metrics, uses_future_context)
        maximum_sold = int(metrics["historical_maximum_sold"])

        confidence = factor_result.confidence
        warning = factor_result.warning

        if self._logic.has_limited_history(len(sales)):
            confidence = "low"
            if warning is None:
                warning = ("Limited History is available; record more sales before relying on a higher-confidence forecast")

        response = {
            "forecast_method": factor_result.method,
            "suggested_portions": quantity,
            "recorded_sales": sales,
            "confidence": confidence,
            "reasoning": factor_result.reasoning,
            "business_advice": (f"Prepare {quantity} portions, then compare sales and leftovers after service {factor_result.advice_ending}"),
            "factors_considered": factor_result.factors,
            "evidence": [
                {
                    "metric": "record_count",
                    "value": metrics["record_count"],
                    "claim": f"The {factor_result.evidence_name} uses {len(sales)} saved sales record.",
                },
                {
                    "metric": "historical_maximum_sold",
                    "value": metrics["historical_maximum_sold"],
                    "claim": f"The highest recorded sales value is {maximum_sold} portions"
                },
            ],
            "warning": warning,
            "uses_future_context": uses_future_context,
            "exception_justification": justification,
            "uses_historical_shift": False,
            "historical_shift_justification": None,
        }
        if factor_result.weekday_analysis is not None:
            response["weekday_analysis"] = factor_result.weekday_analysis


        issues = self._logic.validate_ai_response(response, request, historical_records)
        if issues:
            raise RuntimeError(f"The {factor_result.error_name} could not meet the safety rules: " + "; ".join(issues))
        return response

