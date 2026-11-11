"""Cliente JSON com timeout, retry com backoff e erros de domínio."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from backend.domain.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_DELAY_SECONDS = 10.0

type Sleep = Callable[[float], Awaitable[None]]
type Params = Mapping[str, str | int]


class HttpJsonClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        retries: int,
        backoff: float,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._client = client
        self._retries = retries
        self._backoff = backoff
        self._sleep = sleep

    async def get_json(self, url: str, params: Params | None = None) -> Any:
        reason = "erro desconhecido"
        for attempt in range(self._retries + 1):
            retry_after: float | None = None
            try:
                response = await self._client.get(url, params=params)
            except httpx.TransportError as exc:
                reason = type(exc).__name__
            else:
                if response.status_code < 400:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise SourceUnavailableError("resposta não é JSON") from exc
                if response.status_code not in _RETRYABLE_STATUS:
                    raise SourceUnavailableError(f"HTTP {response.status_code}")
                reason = f"HTTP {response.status_code}"
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            if attempt < self._retries:
                await self._sleep(self._delay(attempt, retry_after))
        logger.warning("fonte indisponível após %d tentativas: %s", self._retries + 1, reason)
        raise SourceUnavailableError(reason)

    def _delay(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(retry_after, _MAX_DELAY_SECONDS)
        jitter = random.uniform(0, self._backoff / 2)  # nosec B311 # noqa: S311
        return min(self._backoff * (2.0**attempt) + jitter, _MAX_DELAY_SECONDS)


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
