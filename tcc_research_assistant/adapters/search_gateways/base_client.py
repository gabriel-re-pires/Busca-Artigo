from abc import ABC, abstractmethod
from typing import List
from core.entities import Paper
from infrastructure.network.http_client import HttpClient, RateLimiter

class BaseSearchClient(ABC):
    def __init__(self):
        # Default rate limit: 1 request per second
        # Subclasses can override this with stricter limits if needed
        self.http_client = HttpClient(RateLimiter(calls=1, period=1.0))

    @abstractmethod
    def search(self, query: str, max_results: int = 10, year_start: int = None, year_end: int = None) -> List[Paper]:
        pass
