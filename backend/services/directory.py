"""Serviço de aplicação: combina as fontes, usa cache e devolve o diretório de uma UF."""

import asyncio
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from backend.domain.errors import SourceUnavailableError
from backend.domain.models import (
    Chamber,
    Directory,
    Parliamentarian,
    SourceState,
    SourceStatus,
)
from backend.domain.ports import ParliamentarianSource, Scope, SourceResult
from backend.domain.validators import sort_key
from backend.services.cache import TTLCache
from backend.services.summary import summarize

_CHAMBER_ORDER = {Chamber.SENADO: 0, Chamber.CAMARA: 1}


@dataclass(frozen=True, slots=True)
class _Outcome:
    status: SourceStatus
    items: tuple[Parliamentarian, ...]
    available: bool


class DirectoryService:
    def __init__(
        self,
        sources: Sequence[ParliamentarianSource],
        *,
        ttl: float,
        partial_ttl: float,
        max_stale: float,
        failure_cooldown: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sources = tuple(sources)
        self._ttl = ttl
        self._partial_ttl = partial_ttl
        self._cache: TTLCache[SourceResult] = TTLCache(
            ttl=ttl, max_stale=max_stale, failure_cooldown=failure_cooldown, clock=clock
        )

    async def by_uf(self, uf: str) -> Directory:
        outcomes = await asyncio.gather(*(self._load(source, uf) for source in self._sources))
        available = [o for o in outcomes if o.available]
        if not available:
            raise SourceUnavailableError("todas as fontes oficiais estão indisponíveis")

        unique: dict[str, Parliamentarian] = {}
        for outcome in available:
            for person in outcome.items:
                unique.setdefault(person.id, person)
        items = tuple(
            sorted(
                unique.values(),
                key=lambda p: (_CHAMBER_ORDER[p.chamber], sort_key(p.name)),
            )
        )
        fetched = [o.status.fetched_at for o in available if o.status.fetched_at is not None]
        return Directory(
            uf=uf,
            items=items,
            sources=tuple(o.status for o in outcomes),
            summary=summarize(items),
            data_as_of=min(fetched) if fetched else datetime.now(UTC),
        )

    async def _load(self, source: ParliamentarianSource, uf: str) -> _Outcome:
        national = source.scope is Scope.NATIONAL
        key = f"{source.name}:all" if national else f"{source.name}:{uf}"
        try:
            cached = await self._cache.get_or_load(
                key,
                lambda: source.fetch(None if national else uf),
                ttl_for=lambda r: self._ttl if r.complete else self._partial_ttl,
            )
        except SourceUnavailableError:
            return _Outcome(SourceStatus(source.name, SourceState.FAILED, None), (), False)
        if cached.stale:
            state = SourceState.STALE
        elif cached.value.complete:
            state = SourceState.OK
        else:
            state = SourceState.PARTIAL
        items = tuple(
            replace(p, fetched_at=cached.fetched_at) for p in cached.value.items if p.uf == uf
        )
        return _Outcome(SourceStatus(source.name, state, cached.fetched_at), items, True)
