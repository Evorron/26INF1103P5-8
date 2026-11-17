from abc import ABC, abstractmethod
from demand_factor_result import DemandFactorResult

"""
Overall responsibility: Defines the common agreement followed by every demand-factor strategy.

Main components:
- DemandFactorStrategy — the abstract base class/interface.
- get_factor_result(payload) — the required operation, returning DemandFactorResult or None.

It allows the coordinator to use different approaches through the same operation.
"""

class DemandFactorStrategy(ABC):
    @abstractmethod
    def get_factor_result(self, payload: dict) -> DemandFactorResult | None:
        """Return a demand-factor result or None when unavailable."""
        raise NotImplementedError
