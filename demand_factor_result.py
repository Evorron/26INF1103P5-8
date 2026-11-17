from dataclasses import dataclass

"""
Overall responsibility: Defines the common information structure returned by either strategy.

Main components:
- DemandFactorResult — the dataclass representing one strategy result.
- Core fields — factor, confidence, method, reasoning, factors, and advice ending.
- Optional fields — warning, weekday analysis, and context justification.
- Message labels — evidence and error names used during response construction.

It carries the information needed to construct the forecast; the final quantity is calculated later.
"""

@dataclass
class DemandFactorResult:
    factor: float
    confidence: str
    method: str
    reasoning: str
    factors: list[str]
    advice_ending: str
    warning: str | None = None
    weekday_analysis: str | None = None
    context_justification: str | None = None
    evidence_name: str = "recommendation"
    error_name: str = "forecast"
