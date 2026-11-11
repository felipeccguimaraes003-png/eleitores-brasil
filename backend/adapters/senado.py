"""Adaptador da API de Dados Abertos do Senado Federal."""

from typing import Any

from backend.adapters.http import HttpJsonClient
from backend.domain.errors import SourceUnavailableError
from backend.domain.models import Chamber, ContactChannel, ContactKind, Parliamentarian
from backend.domain.ports import Scope, SourceResult
from backend.domain.ufs import UF_NAMES
from backend.domain.validators import clean_text, mailto_url, safe_official_url, valid_email


class SenadoSource:
    name = "senado"
    scope = Scope.NATIONAL

    def __init__(self, http: HttpJsonClient, *, base_url: str) -> None:
        self._http = http
        self._base = base_url.rstrip("/")

    async def fetch(self, uf: str | None) -> SourceResult:
        payload = await self._http.get_json(f"{self._base}/senador/lista/atual.json")
        rows = _as_list(
            _dig(payload, "ListaParlamentarEmExercicio", "Parlamentares", "Parlamentar")
        )
        if rows is None:
            raise SourceUnavailableError("formato inesperado (Senado)")
        items = tuple(p for row in rows if (p := self._to_domain(row)) is not None)
        return SourceResult(items)

    def _to_domain(self, row: dict[str, Any]) -> Parliamentarian | None:
        ident = _as_dict(row.get("IdentificacaoParlamentar"))
        mandate = _as_dict(row.get("Mandato"))
        code = clean_text(ident.get("CodigoParlamentar"))
        name = clean_text(ident.get("NomeParlamentar"))
        # Em alguns endpoints a UF só vem dentro do mandato.
        uf = (
            clean_text(ident.get("UfParlamentar")) or clean_text(mandate.get("UfParlamentar")) or ""
        ).upper()
        if code is None or name is None or uf not in UF_NAMES:
            return None

        contacts: list[ContactChannel] = []
        email = valid_email(ident.get("EmailParlamentar"))
        if email:
            contacts.append(
                ContactChannel(
                    ContactKind.EMAIL,
                    "E-mail",
                    email,
                    mailto_url(email),
                    f"senado:senador/{code}#EmailParlamentar",
                    official=True,
                )
            )
        return Parliamentarian(
            id=f"senado:{code}",
            chamber=Chamber.SENADO,
            name=name,
            uf=uf,
            party=clean_text(ident.get("SiglaPartidoParlamentar")),
            photo_url=safe_official_url(ident.get("UrlFotoParlamentar")),
            profile_url=safe_official_url(ident.get("UrlPaginaParlamentar")),
            office=None,
            contacts=tuple(contacts),
        )


def _dig(payload: object, *keys: str) -> object:
    node = payload
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _as_list(value: object) -> list[dict[str, Any]] | None:
    """A conversão XML→JSON do Senado devolve dict quando há um único elemento."""
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        return [value]
    return None


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
