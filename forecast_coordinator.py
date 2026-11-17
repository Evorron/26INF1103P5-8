from pathlib import Path

import ai_manager
from ai_factor_strategy import ai_factor_strategy
from baseline_factor_strategy import baseline_factor_strategy
from forecast_coordinator_class import ForecastCoordinator
from logic_manager import default_logic

"""
Overall responsibility: Creates and connects the default forecasting setup.

Main components:
- default_coordinator — the configured ForecastCoordinator object.
- Default collaborators — the logic manager and ordered AI/baseline strategies.
- Logging configuration — the log destination and model metadata.
- Public method aliases — expose generate_logged_forecast() and build_validated_forecast().

This is the setup and entry-point file; the workflow implementation is in forecast_coordinator_class.py.
"""

DATA_FOLDER = Path(__file__).resolve().parent / "data"

default_coordinator = ForecastCoordinator(logic=default_logic, factor_strategies=[ai_factor_strategy, baseline_factor_strategy], log_path=DATA_FOLDER / "forecast_activity.jsonl", model=ai_manager.DEFAULT_MODEL)
generate_logged_forecast = default_coordinator.generate_logged_forecast
build_validated_forecast = default_coordinator.build_validated_forecast

