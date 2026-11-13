"""Create the forecast adaptor and expose the current entry points."""

import ai_manager
import data_manager
from forecast_adapter_class import ForecastAdapter
from groq_estimator import groq_estimator
from historical_baseline_estimator import historical_baseline_estimator
from logic_manager import default_logic

default_adapter = ForecastAdapter(logic=default_logic, estimators=[groq_estimator, historical_baseline_estimator], log_path=data_manager.DATA_FOLDER / "forecast_activity.jsonl", model=ai_manager.DEFAULT_MODEL)
generate_logged_forecast = default_adapter.generate_logged_forecast
build_validated_forecast = default_adapter.build_validated_forecast

