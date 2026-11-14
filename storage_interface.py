from abc import ABC, abstractmethod
from typing import TypeVar
from record import Record

T = TypeVar("T", bound=Record)

class IStorage(ABC):
    """Interface for storage engines (CSV, Database, etc.)"""
    
    @abstractmethod
    def load(self) -> list[Record]:
        pass

    @abstractmethod
    def save(self, records: list[Record]) -> None:
        pass