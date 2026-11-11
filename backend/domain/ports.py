"""Portas: contratos que os adaptadores implementam e os serviços consomem."""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from backend.domain.models import (
    Activity,
    ContactChannel,
    Municipality,
    Representative,
    Role,
)


class FetchScope(StrEnum):
    UF = "uf"  # a fonte consulta uma UF por vez (ex.: Câmara)
    NATIONAL = "national"  # a fonte devolve tudo de uma vez (ex.: Senado)


@dataclass(frozen=True, slots=True)
class SourceResult:
    items: tuple[Representative, ...]
    complete: bool = True


class LegislatorSource(Protocol):
    """Quem está em exercício numa casa legislativa (Câmara, Senado)."""

    name: str
    scope: FetchScope

    async def fetch(self, uf: str | None) -> SourceResult:
        """Busca parlamentares. `uf` é None quando `scope` é NATIONAL."""
        ...

    async def fetch_index(self) -> SourceResult:
        """Lista nacional só com dados básicos (para a busca por nome)."""
        ...


class ActivitySource(Protocol):
    """O que um parlamentar vem fazendo (projetos, comissões, gastos)."""

    name: str

    async def activity(self, native_id: str) -> Activity: ...


class ElectedRepository(Protocol):
    """Eleitos segundo o TSE, já tratados pelo ETL (arquivos locais, sem rede)."""

    def years(self) -> frozenset[int]: ...

    def generated_at(self, year: int) -> datetime | None: ...

    def elected(
        self,
        year: int,
        roles: Collection[Role],
        *,
        uf: str | None = None,
        municipality: str | None = None,
    ) -> tuple[Representative, ...]: ...

    def municipalities(self, year: int, uf: str) -> tuple[Municipality, ...]: ...

    def social_for(self, civil_name: str, uf: str | None) -> tuple[ContactChannel, ...]:
        """Redes declaradas ao TSE por um candidato, achado pelo nome completo e pela UF."""
        ...
