"""Adaptador da API de Dados Abertos da Câmara dos Deputados."""

import asyncio
import logging
from typing import Any

from backend.adapters.http import HttpJsonClient
from backend.domain.errors import SourceUnavailableError
from backend.domain.models import (
    Chamber,
    ContactChannel,
    ContactKind,
    Parliamentarian,
)
from backend.domain.ports import Scope, SourceResult
from backend.domain.validators import (
    clean_text,
    instagram_handle_from_url,
    instagram_url,
    mailto_url,
    normalize_phone_br,
    safe_official_url,
    valid_email,
)

logger = logging.getLogger(__name__)

_PAGE_SIZE = 100
_MAX_PAGES = 5


class CamaraSource:
    name = "camara"
    scope = Scope.UF

    def __init__(self, http: HttpJsonClient, *, base_url: str, concurrency: int) -> None:
        self._http = http
        self._base = base_url.rstrip("/")
        self._concurrency = concurrency

    async def fetch(self, uf: str | None) -> SourceResult:
        if uf is None:
            raise ValueError("a Câmara é consultada por UF")
        rows = [r for r in await self._list(uf) if isinstance(r.get("id"), int)]
        semaphore = asyncio.Semaphore(self._concurrency)
        details = await asyncio.gather(*(self._detail(semaphore, r["id"]) for r in rows))
        items = tuple(
            p
            for row, detail in zip(rows, details, strict=True)
            if (p := self._to_domain(row, detail, uf)) is not None
        )
        # Se algum detalhe falhou, o e-mail/telefone/Instagram desse deputado pode
        # estar faltando por falha nossa, não por ausência na fonte.
        return SourceResult(items, complete=all(d is not None for d in details))

    async def _list(self, uf: str) -> list[dict[str, Any]]:
        url: str = f"{self._base}/deputados"
        params: dict[str, str | int] | None = {
            "siglaUf": uf,
            "itens": _PAGE_SIZE,
            "ordem": "ASC",
            "ordenarPor": "nome",
        }
        rows: list[dict[str, Any]] = []
        for _ in range(_MAX_PAGES):
            payload = await self._http.get_json(url, params)
            data = payload.get("dados") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                raise SourceUnavailableError("formato inesperado (Câmara)")
            rows.extend(r for r in data if isinstance(r, dict))
            next_url = self._next_link(payload)
            if next_url is None:
                break
            url, params = next_url, None
        return rows

    def _next_link(self, payload: dict[str, Any]) -> str | None:
        links = payload.get("links")
        if not isinstance(links, list):
            return None
        for link in links:
            if isinstance(link, dict) and link.get("rel") == "next":
                href = link.get("href")
                # Só seguimos paginação que continue dentro da API oficial.
                if isinstance(href, str) and href.startswith(f"{self._base}/"):
                    return href
        return None

    async def _detail(self, semaphore: asyncio.Semaphore, deputy_id: int) -> dict[str, Any] | None:
        async with semaphore:
            try:
                payload = await self._http.get_json(f"{self._base}/deputados/{deputy_id}")
            except SourceUnavailableError:
                logger.warning("detalhe do deputado %s indisponível", deputy_id)
                return None
        data = payload.get("dados") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else None

    def _to_domain(
        self, row: dict[str, Any], detail: dict[str, Any] | None, uf: str
    ) -> Parliamentarian | None:
        deputy_id = row["id"]
        name = clean_text(row.get("nome"))
        if name is None:
            return None
        detail = detail or {}
        status = _as_dict(detail.get("ultimoStatus"))
        office = _as_dict(status.get("gabinete"))
        source = f"camara:deputados/{deputy_id}"

        contacts: list[ContactChannel] = []
        email = (
            valid_email(office.get("email"))
            or valid_email(status.get("email"))
            or valid_email(row.get("email"))
        )
        if email:
            contacts.append(
                ContactChannel(
                    ContactKind.EMAIL,
                    "E-mail",
                    email,
                    mailto_url(email),
                    f"{source}#email",
                    official=True,
                )
            )
        phone = normalize_phone_br(office.get("telefone"))
        if phone:
            display, e164 = phone
            contacts.append(
                ContactChannel(
                    ContactKind.PHONE,
                    "Telefone do gabinete",
                    display,
                    f"tel:{e164}",
                    f"{source}#gabinete.telefone",
                    official=True,
                )
            )
        handle = _instagram_from(detail.get("redeSocial"))
        if handle:
            contacts.append(
                ContactChannel(
                    ContactKind.INSTAGRAM,
                    "Instagram",
                    f"@{handle}",
                    instagram_url(handle),
                    f"{source}#redeSocial",
                    official=True,
                )
            )

        return Parliamentarian(
            id=f"camara:{deputy_id}",
            chamber=Chamber.CAMARA,
            name=name,
            uf=uf,
            party=clean_text(row.get("siglaPartido")) or clean_text(status.get("siglaPartido")),
            photo_url=safe_official_url(row.get("urlFoto"))
            or safe_official_url(status.get("urlFoto")),
            profile_url=f"https://www.camara.leg.br/deputados/{deputy_id}",
            office=_office_text(office),
            contacts=tuple(contacts),
        )


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: object) -> str | None:
    return clean_text(str(value)) if isinstance(value, str | int) else None


def _instagram_from(networks: object) -> str | None:
    if not isinstance(networks, list):
        return None
    for url in networks:
        handle = instagram_handle_from_url(url)
        if handle:
            return handle
    return None


def _office_text(office: dict[str, Any]) -> str | None:
    building = _text(office.get("predio"))
    room = _text(office.get("sala"))
    floor = _text(office.get("andar"))
    if building and building.isdigit():
        building = f"prédio {building}"
    parts = [building, f"sala {room}" if room else None, f"{floor}º andar" if floor else None]
    return ", ".join(p for p in parts if p) or None
