"""Coordinate one forecast using the logic manager and the estimators"""


from pathlib import Path
from uuid import uuid4

import activity_logger
from demand_estimator import DemandEstimator
from forecast_estimate import ForecastEstimate
from logic_manager_class import LogicManager

class ForecastAdapter:
    def __init__(self, logic: LogicManager, estimators: list[DemandEstimator], log_path: Path, model: str,):
        self._logic = logic
        self._estimators = estimators
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

        estimate = self._choose_estimate(evidence_payload)
        return self._build_response(request, historical_records, estimate)

    def _choose_estimate(self, payload: dict) -> ForecastEstimate:
        for estimator in self._estimators:
            estimate = estimator.estimate(payload)
            if estimate is not None:
                return estimate

        raise RuntimeError("No demand estimate is available.")

    def _build_response(self, request: dict, historical_records: list[dict], estimate: ForecastEstimate) -> dict:
        metrics = self._logic.calculate_evidence_metrics(historical_records, request["target_date"])
        sales = [record["portions_sold"] for record in historical_records]
        justification = None

        if request["future_context"].strip():
            justification = estimate.context_justification


        uses_future_context = justification is not None
        quantity = self._logic.calculate_quantity(estimate.factor, sales, metrics, uses_future_context)
        maximum_sold = int(metrics["historical_maximum_sold"])

        confidence = estimate.confidence
        warning = estimate.warning

        if self._logic.has_limited_history(len(sales)):
            confidence = "low"
            if warning is None:
                warning = ("Limited History is available; record more sales before relying on a higher-confidence forecast")

        response = {
            "forecast_method": estimate.method,
            "suggested_portions": quantity,
            "recorded_sales": sales,
            "confidence": confidence,
            "reasoning": estimate.reasoning,
            "business_advice": (f"Prepare {quantity} portions, then compare sales and leftovers after service {estimate.advice_ending}"),
            "factors_considered": estimate.factors,
            "evidence": [
                {
                    "metric": "record_count",
                    "value": metrics["record_count"],
                    "claim": f"The {estimate.evidence_name} uses {len(sales)} saved sales record.",
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
        if estimate.weekday_analysis is not None:
            response["weekday_analysis"] = estimate.weekday_analysis


        issues = self._logic.validate_ai_response(response, request, historical_records)
        if issues:
            raise RuntimeError(f"The {estimate.error_name} could not meet the safety rules: " + "; ".join(issues))
        return response

