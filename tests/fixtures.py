"""Respostas simuladas das fontes oficiais.

ATENÇÃO: estas fixtures foram escritas à mão a partir da documentação e de relatos
públicos sobre o formato das APIs. Para substituí-las por respostas reais, rode
`python scripts/smoke_sources.py --save-fixtures` numa máquina com acesso à internet.
"""

from typing import Any


def camara_row(deputy_id: int, name: str, party: str = "PT", uf: str = "GO") -> dict[str, Any]:
    return {
        "id": deputy_id,
        "uri": f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputy_id}",
        "nome": name,
        "siglaPartido": party,
        "siglaUf": uf,
        "idLegislatura": 57,
        "urlFoto": f"https://www.camara.leg.br/internet/deputado/bandep/{deputy_id}.jpg",
        "email": None,
    }


def camara_list(rows: list[dict[str, Any]], next_href: str | None = None) -> dict[str, Any]:
    links = [{"rel": "self", "href": "https://dadosabertos.camara.leg.br/api/v2/deputados"}]
    if next_href:
        links.append({"rel": "next", "href": next_href})
    return {"dados": rows, "links": links}


def camara_detail(
    deputy_id: int,
    *,
    email: str | None = "dep.exemplo@camara.leg.br",
    phone: str | None = "3215-5325",
    networks: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "dados": {
            "id": deputy_id,
            "ultimoStatus": {
                "siglaPartido": "PT",
                "siglaUf": "GO",
                "email": email,
                "gabinete": {
                    "predio": "4",
                    "sala": "325",
                    "andar": "3",
                    "telefone": phone,
                    "email": email,
                },
            },
            "redeSocial": networks if networks is not None else [],
        }
    }


def senado_row(code: int, name: str, uf: str = "GO", party: str = "PSD") -> dict[str, Any]:
    return {
        "IdentificacaoParlamentar": {
            "CodigoParlamentar": str(code),
            "NomeParlamentar": name,
            "SiglaPartidoParlamentar": party,
            "UfParlamentar": uf,
            "UrlFotoParlamentar": f"http://www.senado.leg.br/senadores/img/fotos-oficiais/senador{code}.jpg",
            "UrlPaginaParlamentar": f"http://www25.senado.leg.br/web/senadores/senador/-/perfil/{code}",
            "EmailParlamentar": f"sen.{code}@senado.leg.br",
        },
        "Mandato": {"UfParlamentar": uf},
    }


def senado_list(rows: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
    return {"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": rows}}}
