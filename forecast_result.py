class ForecastResult:
    
    def __init__(
        self,
        demand_impact_factor: float,
        context_assessment: str,
        confidence_score: str,
        factors_considered: list[str],
        weekday_analysis: str = "",
        data_limitations: str = "",
        status: str = "success"

    ):
        self._demand_impact_factor: float = float(demand_impact_factor)
        self._context_assessment: str = context_assessment
        self._confidence_score: str = confidence_score
        self._factors_considered: list[str] = factors_considered
        self._weekday_analysis: str = weekday_analysis
        self._data_limitations: str = data_limitations
        self._status: str = status


    @property
    def status(self) -> str:
        return self._status

    @property
    def demand_impact_factor(self) -> float:
        return self._demand_impact_factor

    @property
    def context_assessment(self) -> str:
        return self._context_assessment

    @property
    def confidence_score(self) -> str:
        return self._confidence_score

    @property
    def factors_considered(self) -> list[str]:
        return self._factors_considered

    def to_dict(self) -> dict:
        return {
            "status": self._status,
            "demand_impact_factor": self._demand_impact_factor,
            "context_assessment": self._context_assessment,
            "confidence_score": self._confidence_score,
            "factors_considered": self._factors_considered,
            "weekday_analysis": self._weekday_analysis,
            "data_limitations": self._data_limitations,
        }