from pathlib import Path

import httpx

from scripts.smoke_sources import run_all
from tests import fixtures as fx


def _transport(*, broken: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if broken:
            return httpx.Response(500)
        host, path = request.url.host, request.url.path
        if host == "dadosabertos.camara.leg.br":
            if path.endswith("/deputados"):
                return httpx.Response(200, json=fx.camara_list([fx.camara_row(1, "Ana")]))
            return httpx.Response(200, json=fx.camara_detail(1))
        if host == "legis.senado.leg.br":
            return httpx.Response(200, json=fx.senado_list([fx.senado_row(1, "Zé")]))
        if host == "servicodados.ibge.gov.br":
            return httpx.Response(200, json=[{"sigla": f"U{i}"} for i in range(27)])
        if host == "dadosabertos.tse.jus.br":
            body = {
                "result": {
                    "resources": [
                        {
                            "name": "Candidatos - 2026 - Redes sociais de candidatos",
                            "url": "https://x",
                        }
                    ]
                }
            }
            return httpx.Response(200, json=body)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_smoke_script_passes_against_expected_shapes(tmp_path: Path) -> None:
    results = run_all(httpx.Client(transport=_transport()), tmp_path)
    assert all(r.ok for r in results), results
    assert {p.name for p in tmp_path.iterdir()} >= {
        "camara_deputados_list.json",
        "senado_lista_atual.json",
    }


def test_smoke_script_reports_failures_instead_of_crashing() -> None:
    results = run_all(httpx.Client(transport=_transport(broken=True)))
    assert results
    assert not any(r.ok for r in results)
