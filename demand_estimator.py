"""Define what every forecast estimator must provide."""

from abc import ABC, abstractmethod

from forecast_estimate import ForecastEstimate

class DemandEstimator(ABC):
    @abstractmethod
    def estimate(self, payload: dict) -> ForecastEstimate | None:
        """Return an estimate or None if this method cannot supply one. """
        raise NotImplementedError