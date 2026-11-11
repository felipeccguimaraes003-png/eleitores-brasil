from dataclasses import dataclass, field

import pytest

from backend.domain.errors import SourceUnavailableError
from backend.domain.models import Chamber, Parliamentarian, SourceState
from backend.domain.ports import Scope, SourceResult
from backend.services.directory import DirectoryService

pytestmark = pytest.mark.anyio


def person(
    pid: str, name: str, chamber: Chamber, uf: str = "GO", party: str | None = "PT"
) -> Parliamentarian:
    return Parliamentarian(
        id=pid, chamber=chamber, name=name, uf=uf, party=party,
        photo_url=None, profile_url=None, office=None, contacts=(),
    )  # fmt: skip


@dataclass
class FakeSource:
    name: str
    scope: Scope
    result: SourceResult | None = None
    calls: list[str | None] = field(default_factory=list)

    async def fetch(self, uf: str | None) -> SourceResult:
        self.calls.append(uf)
        if self.result is None:
            raise SourceUnavailableError("fora do ar")
        return self.result


def _service(*sources: FakeSource) -> DirectoryService:
    return DirectoryService(sources, ttl=900, partial_ttl=60, max_stale=3600, failure_cooldown=15)


async def test_merges_sorts_and_summarizes() -> None:
    camara = FakeSource(
        "camara",
        Scope.UF,
        SourceResult(
            (
                person("camara:2", "Zélia", Chamber.CAMARA, party="PL"),
                person("camara:1", "Álvaro", Chamber.CAMARA),
                person("camara:3", "Bia", Chamber.CAMARA, party=None),
            )
        ),
    )
    senado = FakeSource(
        "senado",
        Scope.NATIONAL,
        SourceResult(
            (
                person("senado:9", "Xavier", Chamber.SENADO),
                person("senado:8", "SP", Chamber.SENADO, uf="SP"),
            )
        ),
    )
    directory = await _service(camara, senado).by_uf("GO")
    assert [p.name for p in directory.items] == [
        "Xavier",
        "Álvaro",
        "Bia",
        "Zélia",
    ]  # senado primeiro
    assert directory.summary.total == 4
    assert directory.summary.by_chamber == {"camara": 3, "senado": 1}
    assert directory.summary.by_party == {"PT": 2, "PL": 1, "Sem partido": 1}
    assert [s.state for s in directory.sources] == [SourceState.OK, SourceState.OK]


async def test_national_source_is_fetched_once_for_all_ufs() -> None:
    senado = FakeSource(
        "senado",
        Scope.NATIONAL,
        SourceResult(
            (
                person("senado:1", "A", Chamber.SENADO, "GO"),
                person("senado:2", "B", Chamber.SENADO, "SP"),
            )
        ),
    )
    camara = FakeSource("camara", Scope.UF, SourceResult(()))
    service = _service(camara, senado)
    go = await service.by_uf("GO")
    sp = await service.by_uf("SP")
    assert senado.calls == [None]
    assert [p.name for p in go.items] == ["A"]
    assert [p.name for p in sp.items] == ["B"]
    assert camara.calls == ["GO", "SP"]


async def test_one_source_down_still_answers() -> None:
    camara = FakeSource("camara", Scope.UF, None)
    senado = FakeSource(
        "senado", Scope.NATIONAL, SourceResult((person("senado:1", "A", Chamber.SENADO),))
    )
    directory = await _service(camara, senado).by_uf("GO")
    assert [p.name for p in directory.items] == ["A"]
    states = {s.name: s.state for s in directory.sources}
    assert states == {"camara": SourceState.FAILED, "senado": SourceState.OK}


async def test_all_sources_down_raises() -> None:
    with pytest.raises(SourceUnavailableError):
        await _service(
            FakeSource("camara", Scope.UF, None), FakeSource("senado", Scope.NATIONAL, None)
        ).by_uf("GO")


async def test_incomplete_source_is_marked_partial() -> None:
    camara = FakeSource(
        "camara", Scope.UF, SourceResult((person("camara:1", "A", Chamber.CAMARA),), complete=False)
    )
    directory = await _service(camara).by_uf("GO")
    assert directory.sources[0].state is SourceState.PARTIAL


async def test_duplicate_ids_are_collapsed() -> None:
    dup = person("camara:1", "A", Chamber.CAMARA)
    camara = FakeSource("camara", Scope.UF, SourceResult((dup, dup)))
    assert len((await _service(camara).by_uf("GO")).items) == 1


async def test_stale_state_when_source_fails_after_expiry() -> None:
    now = 0.0
    camara = FakeSource(
        "camara", Scope.UF, SourceResult((person("camara:1", "A", Chamber.CAMARA),))
    )
    service = DirectoryService(
        [camara], ttl=10, partial_ttl=1, max_stale=1000, failure_cooldown=0, clock=lambda: now
    )
    await service.by_uf("GO")
    now = 11.0
    camara.result = None
    directory = await service.by_uf("GO")
    assert directory.sources[0].state is SourceState.STALE
    assert [p.name for p in directory.items] == ["A"]


async def test_items_carry_the_source_fetch_time() -> None:
    camara = FakeSource(
        "camara", Scope.UF, SourceResult((person("camara:1", "A", Chamber.CAMARA),))
    )
    (item,) = (await _service(camara).by_uf("GO")).items
    assert item.fetched_at is not None
