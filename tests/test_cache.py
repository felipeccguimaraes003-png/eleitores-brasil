import asyncio

import pytest

from backend.domain.errors import SourceUnavailableError
from backend.services.cache import TTLCache

pytestmark = pytest.mark.anyio


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _cache(
    clock: Clock, ttl: float = 10, max_stale: float = 100, cooldown: float = 5
) -> TTLCache[int]:
    return TTLCache(ttl=ttl, max_stale=max_stale, failure_cooldown=cooldown, clock=clock)


async def test_serves_from_cache_until_ttl() -> None:
    clock, calls = Clock(), 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        return calls

    cache = _cache(clock)
    assert (await cache.get_or_load("k", loader)).value == 1
    clock.now = 9.9
    assert (await cache.get_or_load("k", loader)).value == 1
    clock.now = 10.1
    assert (await cache.get_or_load("k", loader)).value == 2


async def test_single_flight_under_concurrency() -> None:
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return 42

    cache = _cache(Clock())
    results = await asyncio.gather(*(cache.get_or_load("k", loader) for _ in range(10)))
    assert calls == 1
    assert {r.value for r in results} == {42}


async def test_serves_stale_value_when_source_fails() -> None:
    clock = Clock()
    cache = _cache(clock)
    should_fail = False

    async def loader() -> int:
        if should_fail:
            raise SourceUnavailableError("fora do ar")
        return 7

    await cache.get_or_load("k", loader)
    should_fail, clock.now = True, 11
    result = await cache.get_or_load("k", loader)
    assert (result.value, result.stale) == (7, True)


async def test_stale_value_expires_after_max_stale() -> None:
    clock = Clock()
    cache = _cache(clock, max_stale=50)
    fail = False

    async def loader() -> int:
        if fail:
            raise SourceUnavailableError("fora do ar")
        return 7

    await cache.get_or_load("k", loader)
    fail, clock.now = True, 60
    with pytest.raises(SourceUnavailableError):
        await cache.get_or_load("k", loader)


async def test_failure_cooldown_protects_the_source() -> None:
    clock, calls = Clock(), 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        raise SourceUnavailableError("fora do ar")

    cache = _cache(clock, cooldown=5)
    for _ in range(3):
        with pytest.raises(SourceUnavailableError):
            await cache.get_or_load("k", loader)
    assert calls == 1
    clock.now = 5.1
    with pytest.raises(SourceUnavailableError):
        await cache.get_or_load("k", loader)
    assert calls == 2


async def test_ttl_can_depend_on_the_value() -> None:
    clock, calls = Clock(), 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        return calls

    cache = _cache(clock, ttl=100)
    short = lambda value: 1.0  # noqa: E731 - lambda de uma linha em teste
    await cache.get_or_load("k", loader, ttl_for=short)
    clock.now = 2
    assert (await cache.get_or_load("k", loader, ttl_for=short)).value == 2
