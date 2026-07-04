from abc import ABC, abstractmethod
from typing import List
from core.entities import Paper

class BaseExporter(ABC):
    @abstractmethod
    def export(self, papers: List[Paper], filepath: str) -> str:
        pass
