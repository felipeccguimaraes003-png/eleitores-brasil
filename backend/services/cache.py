"""Cache TTL assíncrono com três proteções para as APIs do governo:

* single-flight: requisições simultâneas à mesma chave disparam uma única coleta;
* stale-if-error: se a fonte cair, serve o último valor bom por até `max_stale`;
* cooldown de falha: depois de uma falha, não martela a fonte durante alguns segundos.

O cache vive na memória do processo. Com vários workers, cada um tem o seu.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.domain.errors import SourceUnavailableError


@dataclass(frozen=True, slots=True)
class Cached[T]:
    value: T
    fetched_at: datetime
    stale: bool


@dataclass(frozen=True, slots=True)
class _Entry[T]:
    value: T
    fetched_at: datetime
    stored_at: float
    expires_at: float


@dataclass(frozen=True, slots=True)
class _Failure:
    until: float
    error: SourceUnavailableError


class TTLCache[T]:
    def __init__(
        self,
        *,
        ttl: float,
        max_stale: float,
        failure_cooldown: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl
        self._max_stale = max_stale
        self._cooldown = failure_cooldown
        self._clock = clock
        self._entries: dict[str, _Entry[T]] = {}
        self._failures: dict[str, _Failure] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_load(
        self,
        key: str,
        loader: Callable[[], Awaitable[T]],
        *,
        ttl_for: Callable[[T], float] | None = None,
    ) -> Cached[T]:
        fresh = self._fresh(key)
        if fresh is not None:
            return fresh
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            fresh = self._fresh(key)  # outro request pode ter recarregado enquanto esperávamos
            if fresh is not None:
                return fresh
            now = self._clock()
            failure = self._failures.get(key)
            if failure is not None and now < failure.until:
                return self._stale_or_raise(key, failure.error)
            try:
                value = await loader()
            except SourceUnavailableError as exc:
                self._failures[key] = _Failure(now + self._cooldown, exc)
                return self._stale_or_raise(key, exc)
            self._failures.pop(key, None)
            stored_at = self._clock()
            ttl = ttl_for(value) if ttl_for is not None else self._ttl
            entry = _Entry(value, datetime.now(UTC), stored_at, stored_at + ttl)
            self._entries[key] = entry
            return Cached(value, entry.fetched_at, stale=False)

    def _fresh(self, key: str) -> Cached[T] | None:
        entry = self._entries.get(key)
        if entry is not None and self._clock() < entry.expires_at:
            return Cached(entry.value, entry.fetched_at, stale=False)
        return None

    def _stale_or_raise(self, key: str, error: SourceUnavailableError) -> Cached[T]:
        entry = self._entries.get(key)
        if entry is not None and self._clock() - entry.stored_at <= self._max_stale:
            return Cached(entry.value, entry.fetched_at, stale=True)
        raise error
