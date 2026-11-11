from typing import Any

import httpx
import pytest

from backend.adapters.http import HttpJsonClient
from backend.adapters.senado import SenadoSource
from backend.domain.errors import SourceUnavailableError
from backend.domain.models import ContactKind
from tests import fixtures as fx

pytestmark = pytest.mark.anyio


def _source(payload: Any, status: int = 200) -> SenadoSource:
    async def no_sleep(_: float) -> None:
        return None

    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=payload))
    http = HttpJsonClient(
        httpx.AsyncClient(transport=transport), retries=0, backoff=0, sleep=no_sleep
    )
    return SenadoSource(http, base_url="https://senado.test/dadosabertos")


async def test_parses_senators_and_upgrades_photo_to_https() -> None:
    result = await _source(
        fx.senado_list([fx.senado_row(10, "Zé Senador"), fx.senado_row(11, "Ana", "SP")])
    ).fetch(None)
    ze, ana = result.items
    assert ze.id == "senado:10"
    assert ze.chamber.value == "senado"
    assert ze.photo_url == "https://www.senado.leg.br/senadores/img/fotos-oficiais/senador10.jpg"
    assert ze.profile_url == "https://www25.senado.leg.br/web/senadores/senador/-/perfil/10"
    (email,) = ze.contacts
    assert email.kind is ContactKind.EMAIL
    assert email.source == "senado:senador/10#EmailParlamentar"
    assert ana.uf == "SP"


async def test_single_element_comes_as_dict() -> None:
    result = await _source(fx.senado_list(fx.senado_row(10, "Único"))).fetch(None)
    assert [p.name for p in result.items] == ["Único"]


async def test_uf_falls_back_to_mandate() -> None:
    row = fx.senado_row(10, "Sem UF na identificação", uf="MT")
    del row["IdentificacaoParlamentar"]["UfParlamentar"]
    (person,) = (await _source(fx.senado_list([row])).fetch(None)).items
    assert person.uf == "MT"


async def test_drops_invalid_rows_and_bad_email() -> None:
    bad_uf = fx.senado_row(1, "UF inválida", uf="ZZ")
    no_name = fx.senado_row(2, "x")
    del no_name["IdentificacaoParlamentar"]["NomeParlamentar"]
    bad_email = fx.senado_row(3, "Email ruim")
    bad_email["IdentificacaoParlamentar"]["EmailParlamentar"] = "não é email"
    result = await _source(fx.senado_list([bad_uf, no_name, bad_email])).fetch(None)
    (person,) = result.items
    assert person.name == "Email ruim"
    assert person.contacts == ()


@pytest.mark.parametrize("payload", [{}, {"ListaParlamentarEmExercicio": {}}, [], "texto"])
async def test_unexpected_shape_is_source_error(payload: Any) -> None:
    with pytest.raises(SourceUnavailableError):
        await _source(payload).fetch(None)
