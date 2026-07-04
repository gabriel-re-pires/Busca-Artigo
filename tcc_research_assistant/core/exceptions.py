class BuscadorError(Exception):
    """Base exception for the Busca-Artigo application."""


class NetworkError(BuscadorError):
    """Raised when a network request fails after all retries are exhausted."""


class RateLimitError(BuscadorError):
    """Raised when the remote server returns HTTP 429 (Too Many Requests)."""


class EmptyResultsError(BuscadorError):
    """Raised when a search returns no papers, carrying a per-source explanation."""

    def __init__(self, message: str, source_report: dict | None = None) -> None:
        super().__init__(message)
        self.source_report = source_report or {}
