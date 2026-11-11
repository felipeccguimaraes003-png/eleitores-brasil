import asyncio
from typing import Any

import httpx
import pytest

from backend.adapters.camara import CamaraSource
from backend.adapters.http import HttpJsonClient
from backend.domain.errors import SourceUnavailableError
from backend.domain.models import ContactKind
from tests import fixtures as fx

pytestmark = pytest.mark.anyio
BASE = "https://camara.test/api/v2"


def _source(handler: Any, concurrency: int = 4) -> CamaraSource:
    async def no_sleep(_: float) -> None:
        return None

    http = HttpJsonClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        retries=0,
        backoff=0,
        sleep=no_sleep,
    )
    return CamaraSource(http, base_url=BASE, concurrency=concurrency)


def _json(data: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


async def test_merges_list_and_detail_with_provenance() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/deputados"):
            assert request.url.params["siglaUf"] == "GO"
            return _json(
                fx.camara_list([fx.camara_row(1, "Ana Lima"), fx.camara_row(2, "Bia Souza")])
            )
        if request.url.path.endswith("/deputados/1"):
            return _json(
                fx.camara_detail(
                    1, networks=["https://twitter.com/ana", "https://www.instagram.com/AnaLima/"]
                )
            )
        return _json(fx.camara_detail(2))

    result = await _source(handler).fetch("GO")
    assert result.complete
    ana, bia = result.items
    assert ana.id == "camara:1"
    assert ana.uf == "GO"
    assert ana.photo_url == "https://www.camara.leg.br/internet/deputado/bandep/1.jpg"
    assert ana.profile_url == "https://www.camara.leg.br/deputados/1"
    assert ana.office == "prédio 4, sala 325, 3º andar"
    kinds = {c.kind: c for c in ana.contacts}
    assert kinds[ContactKind.EMAIL].url == "mailto:dep.exemplo@camara.leg.br"
    assert kinds[ContactKind.PHONE].url == "tel:+556132155325"
    assert kinds[ContactKind.INSTAGRAM].value == "@analima"
    assert kinds[ContactKind.INSTAGRAM].source == "camara:deputados/1#redeSocial"
    assert all(c.source for c in ana.contacts)
    assert ContactKind.INSTAGRAM not in {c.kind for c in bia.contacts}


async def test_no_instagram_when_only_other_networks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/deputados"):
            return _json(fx.camara_list([fx.camara_row(1, "Ana")]))
        return _json(
            fx.camara_detail(1, networks=["https://facebook.com/ana", "javascript:alert(1)"])
        )

    (ana,) = (await _source(handler).fetch("GO")).items
    assert ContactKind.INSTAGRAM not in {c.kind for c in ana.contacts}


async def test_detail_failure_degrades_gracefully() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/deputados"):
            row = fx.camara_row(1, "Ana")
            row["email"] = "dep.ana@camara.leg.br"
            return _json(fx.camara_list([row, fx.camara_row(2, "Bia")]))
        if request.url.path.endswith("/deputados/1"):
            return httpx.Response(504)
        return _json(fx.camara_detail(2))

    result = await _source(handler).fetch("GO")
    assert not result.complete
    ana, bia = result.items
    assert [c.kind for c in ana.contacts] == [ContactKind.EMAIL]  # veio da listagem
    assert ContactKind.PHONE in {c.kind for c in bia.contacts}


async def test_follows_pagination_only_inside_official_api() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path.endswith("/deputados") and "pagina" not in request.url.params:
            return _json(
                fx.camara_list([fx.camara_row(1, "Ana")], next_href=f"{BASE}/deputados?pagina=2")
            )
        if request.url.path.endswith("/deputados"):
            return _json(
                fx.camara_list(
                    [fx.camara_row(2, "Bia")], next_href="https://evil.test/deputados?pagina=3"
                )
            )
        return _json(fx.camara_detail(1))

    result = await _source(handler).fetch("GO")
    assert [p.name for p in result.items] == ["Ana", "Bia"]
    assert not any("evil.test" in url for url in seen)


async def test_malformed_list_is_source_error() -> None:
    with pytest.raises(SourceUnavailableError, match="formato"):
        await _source(lambda _: _json({"dados": "nope"})).fetch("GO")


async def test_drops_rows_without_valid_id_or_name() -> None:
    rows = [fx.camara_row(1, "Ana"), {"id": "x", "nome": "Sem id"}, {"id": 3, "nome": "  "}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/deputados"):
            return _json(fx.camara_list(rows))
        return _json(fx.camara_detail(1))

    result = await _source(handler).fetch("GO")
    assert [p.name for p in result.items] == ["Ana"]


async def test_detail_requests_respect_concurrency_limit() -> None:
    in_flight = 0
    peak = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak
        if request.url.path.endswith("/deputados"):
            return _json(fx.camara_list([fx.camara_row(i, f"Dep {i}") for i in range(1, 9)]))
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return _json(fx.camara_detail(1))

    await _source(handler, concurrency=2).fetch("GO")
    assert peak == 2


async def test_requires_uf() -> None:
    with pytest.raises(ValueError, match="UF"):
        await _source(lambda _: _json({})).fetch(None)
