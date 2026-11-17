from abc import ABC, abstractmethod

class Record(ABC):
    """Common interface for objects that can be stored in databases/CSVs."""

    @abstractmethod
    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Record":
        raise NotImplementedError