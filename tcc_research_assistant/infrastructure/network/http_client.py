import time
import logging
import requests
from requests.exceptions import Timeout, ConnectionError as ConnError, RequestException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from core.exceptions import NetworkError, RateLimitError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter: allows `calls` requests within `period` seconds."""

    def __init__(self, calls: int, period: float) -> None:
        self.calls = calls
        self.period = period
        self._timestamps: list[float] = []

    def wait(self) -> None:
        now = time.time()
        self._timestamps = [t for t in self._timestamps if now - t < self.period]
        if len(self._timestamps) >= self.calls:
            sleep_for = self.period - (now - self._timestamps[0])
            if sleep_for > 0:
                logger.debug("Rate limited — aguardando %.2fs", sleep_for)
                time.sleep(sleep_for)
        self._timestamps.append(time.time())


@retry(
    retry=retry_if_exception_type((Timeout, ConnError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_with_retry(
    session: requests.Session,
    url: str,
    params: dict,
    headers: dict,
    timeout: int,
) -> requests.Response:
    return session.get(url, params=params, headers=headers, timeout=timeout)


class HttpClient:
    def __init__(self, rate_limiter: RateLimiter, timeout: int = 15) -> None:
        self.session = requests.Session()
        self.rate_limiter = rate_limiter
        self.timeout = timeout
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
        )

    def get(
        self,
        url: str,
        params: dict = None,
        custom_headers: dict = None,
    ) -> requests.Response:
        self.rate_limiter.wait()

        headers = dict(self.session.headers)
        if custom_headers:
            headers.update(custom_headers)

        try:
            response = _get_with_retry(
                self.session, url, params or {}, headers, self.timeout
            )
        except (Timeout, ConnError, RequestException) as exc:
            raise NetworkError(
                f"Falha na conexão com '{url}' após múltiplas tentativas."
            ) from exc

        if response.status_code == 429:
            raise RateLimitError(
                f"Servidor bloqueou as requisições (HTTP 429) em '{url}'. "
                "Aguarde alguns minutos antes de buscar novamente."
            )

        return response
