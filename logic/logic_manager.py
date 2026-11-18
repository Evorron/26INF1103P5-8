from logic.forecast_rules import ForecastRules
from logic.logic_manager_class import LogicManager

"""
Overall Responsibility: Provides the entry points other modules can use to access the business logic

Main Components:
        'default_logic' - the dfeault LogicManager Object.
        Method aliases - expose object methods through calls, such as 'logic_manager.validate_sales_record()'
        Exported settings - make exsiting rule constants accessible through this module

This file connects callers to the implementation; the business logic is defined in 'logic_manager_class.py'.
"""

default_logic = LogicManager()

# These names also support the previous adapter during the migration.
validate_label = default_logic.validate_label
validate_historical_date = default_logic.validate_historical_date
validate_forecast_date = default_logic.validate_forecast_date
validate_portions = default_logic.validate_portions
validate_context = default_logic.validate_context
validate_sales_record = default_logic.validate_sales_record
validate_forecast_request = default_logic.validate_forecast_request
validate_search_filters = default_logic.validate_search_filters
normalise_text = default_logic.normalise_text
records_for_forecast = default_logic.records_for_forecast
records_for_search = default_logic.records_for_search
food_items_for_user = default_logic.food_items_for_user
build_ai_payload = default_logic.build_ai_payload
calculate_evidence_metrics = default_logic.calculate_evidence_metrics
validate_ai_response = default_logic.validate_ai_response

CONTEXT_WORD_LIMIT = LogicManager.CONTEXT_WORD_LIMIT
EVIDENCE_TOLERANCE = LogicManager.EVIDENCE_TOLERANCE
LOW_CONFIDENCE_RECORD_COUNT = ForecastRules.LOW_CONFIDENCE_RECORD_COUNT
MAXIMUM_MULTIPLIER = ForecastRules.MAXIMUM_MULTIPLIER
MINIMUM_DEMAND_FACTOR = ForecastRules.MINIMUM_DEMAND_FACTOR
MINIMUM_RECOMMENDATION_RATIO = ForecastRules.MINIMUM_RECOMMENDATION_RATIO
WEEKDAY_DEVIATION_LIMIT = ForecastRules.WEEKDAY_DEVIATION_LIMIT
REQUIRED_SAME_WEEKDAY_RECORDS = ForecastRules.REQUIRED_SAME_WEEKDAY_RECORDS
HISTORICAL_SHIFT_THRESHOLD = ForecastRules.HISTORICAL_SHIFT_THRESHOLD