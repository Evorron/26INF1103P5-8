from abc import ABC, abstractmethod
from record import Record


class IStorage(ABC):
    """Interface for storage engines (CSV, Database, etc.)"""
    
    @abstractmethod
    def load(self) -> list[Record]:
        pass

    @abstractmethod
    def save(self, records: list[Record]) -> None:
        pass