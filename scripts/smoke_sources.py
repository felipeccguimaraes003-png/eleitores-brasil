"""Teste de fumaça das fontes oficiais. Rode na SUA máquina (precisa de internet):

    python scripts/smoke_sources.py                      # só verifica
    python scripts/smoke_sources.py --save-fixtures DIR  # e guarda as respostas reais

Serve para confirmar que os formatos reais batem com o que os adaptadores esperam
(as fixtures de `tests/fixtures.py` foram escritas à mão a partir da documentação).
Sai com código 1 se alguma verificação falhar.
"""

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
SENADO = "https://legis.senado.leg.br/dadosabertos"
IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades"
TSE_CKAN = "https://dadosabertos.tse.jus.br/api/3/action/package_show"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


class Saver:
    def __init__(self, directory: Path | None) -> None:
        self._dir = directory
        if directory:
            directory.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, payload: Any) -> None:
        if self._dir:
            (self._dir / f"{name}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )


def _get(client: httpx.Client, url: str, **params: str | int) -> Any:
    response = client.get(url, params=params or None, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def check_camara(client: httpx.Client, saver: Saver) -> list[Check]:
    listing = _get(client, f"{CAMARA}/deputados", siglaUf="GO", itens=5)
    saver.save("camara_deputados_list", listing)
    rows = listing["dados"]
    missing = {"id", "nome", "siglaPartido", "urlFoto"} - rows[0].keys()
    checks = [
        Check("Câmara: lista de deputados", bool(rows) and not missing,
              f"{len(rows)} itens; campos ausentes: {sorted(missing) or 'nenhum'}; "
              f"'email' na lista: {'email' in rows[0]}")
    ]  # fmt: skip
    detail = _get(client, f"{CAMARA}/deputados/{rows[0]['id']}")
    saver.save("camara_deputado_detail", detail)
    data = detail["dados"]
    office = (data.get("ultimoStatus") or {}).get("gabinete") or {}
    checks.append(
        Check("Câmara: detalhe do deputado", isinstance(office, dict) and bool(office),
              f"gabinete com chaves {sorted(office)}; 'redeSocial' é lista: "
              f"{isinstance(data.get('redeSocial'), list)}")
    )  # fmt: skip
    return checks


def check_senado(client: httpx.Client, saver: Saver) -> list[Check]:
    payload = _get(client, f"{SENADO}/senador/lista/atual.json")
    saver.save("senado_lista_atual", payload)
    rows = payload["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    ident = rows[0]["IdentificacaoParlamentar"]
    wanted = {"CodigoParlamentar", "NomeParlamentar", "UfParlamentar", "EmailParlamentar"}
    ufs = {r["IdentificacaoParlamentar"].get("UfParlamentar") for r in rows}
    ok = len(rows) > 0 and not (wanted - ident.keys())
    return [
        Check("Senado: lista atual", ok,
              f"{len(rows)} senadores; {len(ufs - {None})} UFs; campos ausentes: "
              f"{sorted(wanted - ident.keys()) or 'nenhum'}")
    ]  # fmt: skip


def check_ibge(client: httpx.Client, saver: Saver) -> list[Check]:
    states = _get(client, f"{IBGE}/estados")
    saver.save("ibge_estados", states)
    return [Check("IBGE: localidades/estados", len(states) == 27, f"{len(states)} estados")]


def check_tse(client: httpx.Client, saver: Saver) -> list[Check]:
    payload = _get(client, TSE_CKAN, id="candidatos-2026")
    saver.save("tse_candidatos_2026_catalogo", payload)
    resources = payload["result"]["resources"]
    names = [str(r.get("name", "")) for r in resources]
    social = [r for r in resources if "redes sociais" in str(r.get("name", "")).lower()]
    sample = social[0].get("url") if social else "nenhum"
    return [
        Check("TSE: catálogo candidatos-2026", bool(social),
              f"{len(resources)} recursos; recursos de redes sociais: {len(social)}; "
              f"exemplo: {sample}; nomes (início): {names[:3]}")
    ]  # fmt: skip


CHECKS: list[Callable[[httpx.Client, Saver], list[Check]]] = [
    check_camara,
    check_senado,
    check_ibge,
    check_tse,
]


def run_all(client: httpx.Client, save_dir: Path | None = None) -> list[Check]:
    saver = Saver(save_dir)
    results: list[Check] = []
    for check in CHECKS:
        try:
            results.extend(check(client, saver))
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
            results.append(Check(check.__name__, False, f"{type(exc).__name__}: {exc}"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save-fixtures", type=Path, metavar="DIR")
    args = parser.parse_args()
    with httpx.Client(timeout=30, headers={"User-Agent": "eleitores-brasil-smoke/0.1"}) as client:
        results = run_all(client, args.save_fixtures)
    for result in results:
        print(f"[{'OK' if result.ok else 'FALHOU'}] {result.name}: {result.detail}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
