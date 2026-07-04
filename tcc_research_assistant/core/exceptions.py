class BuscadorError(Exception):
    """Base exception for the Buscador TCC application."""


class NetworkError(BuscadorError):
    """Raised when a network request fails after all retries are exhausted."""


class RateLimitError(BuscadorError):
    """Raised when the remote server returns HTTP 429 (Too Many Requests)."""
