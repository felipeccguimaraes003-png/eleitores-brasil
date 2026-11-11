import httpx
import pytest

from backend.adapters.http import HttpJsonClient
from backend.domain.errors import SourceUnavailableError

pytestmark = pytest.mark.anyio


def _client(handler: httpx.MockTransport, sleeps: list[float], retries: int = 2) -> HttpJsonClient:
    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    return HttpJsonClient(
        httpx.AsyncClient(transport=handler), retries=retries, backoff=0.5, sleep=fake_sleep
    )


async def test_retries_on_5xx_then_succeeds() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503) if calls == 1 else httpx.Response(200, json={"ok": True})

    sleeps: list[float] = []
    result = await _client(httpx.MockTransport(handler), sleeps).get_json("https://x.test/a")
    assert result == {"ok": True}
    assert calls == 2
    assert len(sleeps) == 1


async def test_does_not_retry_client_errors() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    with pytest.raises(SourceUnavailableError, match="404"):
        await _client(httpx.MockTransport(handler), []).get_json("https://x.test/a")
    assert calls == 1


async def test_gives_up_after_retries_on_transport_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("lento", request=request)

    sleeps: list[float] = []
    with pytest.raises(SourceUnavailableError, match="ConnectTimeout"):
        await _client(httpx.MockTransport(handler), sleeps, retries=2).get_json("https://x.test/a")
    assert calls == 3
    assert len(sleeps) == 2


async def test_non_json_body_is_an_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>erro</html>")

    with pytest.raises(SourceUnavailableError, match="JSON"):
        await _client(httpx.MockTransport(handler), []).get_json("https://x.test/a")


async def test_respects_retry_after_with_cap() -> None:
    answers = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(429, headers={"Retry-After": "999"}),
            httpx.Response(200, json=[]),
        ]
    )
    sleeps: list[float] = []
    await _client(httpx.MockTransport(lambda _: next(answers)), sleeps).get_json("https://x.test/a")
    assert sleeps == [2.0, 10.0]
