"""Modelo de domínio. Só biblioteca padrão: nada de HTTP, Pydantic ou Pandas aqui."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Literal


class Sphere(StrEnum):
    FEDERAL = "federal"
    ESTADUAL = "estadual"
    MUNICIPAL = "municipal"


class Role(StrEnum):
    """Cargos eletivos cobertos, na ordem em que aparecem na tela."""

    PRESIDENTE = "presidente"
    GOVERNADOR = "governador"
    SENADOR = "senador"
    DEPUTADO_FEDERAL = "deputado_federal"
    DEPUTADO_ESTADUAL = "deputado_estadual"  # no DF, o cargo se chama deputado distrital
    PREFEITO = "prefeito"
    VEREADOR = "vereador"


ROLE_SPHERE: dict[Role, Sphere] = {
    Role.PRESIDENTE: Sphere.FEDERAL,
    Role.SENADOR: Sphere.FEDERAL,
    Role.DEPUTADO_FEDERAL: Sphere.FEDERAL,
    Role.GOVERNADOR: Sphere.ESTADUAL,
    Role.DEPUTADO_ESTADUAL: Sphere.ESTADUAL,
    Role.PREFEITO: Sphere.MUNICIPAL,
    Role.VEREADOR: Sphere.MUNICIPAL,
}
ROLE_ORDER: dict[Role, int] = {role: index for index, role in enumerate(Role)}
STATE_ROLES: tuple[Role, ...] = (
    Role.GOVERNADOR,
    Role.SENADOR,
    Role.DEPUTADO_FEDERAL,
    Role.DEPUTADO_ESTADUAL,
)
MUNICIPAL_ROLES: tuple[Role, ...] = (Role.PREFEITO, Role.VEREADOR)

Gender = Literal["F", "M"]


class MandateStatus(StrEnum):
    # Confirmado pela API da própria casa legislativa (Câmara ou Senado).
    EM_EXERCICIO = "em_exercicio"
    # Eleito para o mandato em curso, segundo o TSE. O TSE não informa renúncia, cassação
    # ou substituição: por isso não chamamos de "em exercício".
    ELEITO_MANDATO_VIGENTE = "eleito_mandato_vigente"
    # Eleito, ainda não tomou posse.
    ELEITO_AGUARDANDO_POSSE = "eleito_aguardando_posse"


class MandateView(StrEnum):
    ATUAL = "atual"  # quem ocupa o cargo hoje
    PROXIMO = "proximo"  # quem foi eleito e ainda vai tomar posse


class ContactKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


@dataclass(frozen=True, slots=True)
class ContactChannel:
    """Canal de contato com procedência obrigatória.

    Regra do projeto: sem `source` rastreável o canal não existe, e sem `official`
    verdadeiro ele não é apresentado como confirmado.
    """

    kind: ContactKind
    label: str
    value: str
    url: str
    source: str
    official: bool


@dataclass(frozen=True, slots=True)
class Term:
    """Mandato. `start`/`end` ficam vazios quando a data varia (ex.: deputados estaduais)."""

    election_year: int | None = None
    start: date | None = None
    end: date | None = None


@dataclass(frozen=True, slots=True)
class Municipality:
    code: str  # código do município no TSE (diferente do código do IBGE)
    name: str
    uf: str


@dataclass(frozen=True, slots=True)
class Representative:
    id: str  # "camara:204521", "senado:5672", "tse:2026:280002551544"
    role: Role
    role_label: str  # "Senadora", "Deputado distrital"...
    name: str  # nome público (parlamentar ou de urna)
    source: str  # "camara" | "senado" | "tse"
    status: MandateStatus
    term: Term = Term()
    civil_name: str | None = None  # nome completo (nome social, quando houver)
    gender: Gender | None = None  # só para concordância ("Senadora", "Reeleita"); não vai para a API
    uf: str | None = None  # None para o presidente
    municipality: Municipality | None = None
    party: str | None = None
    photo_url: str | None = None
    profile_url: str | None = None
    office: str | None = None
    ballot_number: str | None = None  # número de urna (TSE)
    vice: str | None = None  # nome do vice (cargos do Executivo)
    highlight: str | None = None  # ex.: "Reeleito", "Hoje é deputado federal"
    contacts: tuple[ContactChannel, ...] = ()
    fetched_at: datetime | None = None

    @property
    def sphere(self) -> Sphere:
        return ROLE_SPHERE[self.role]


class SourceState(StrEnum):
    OK = "ok"
    PARTIAL = "partial"  # resposta incompleta (ex.: falhou o detalhe de alguns deputados)
    STALE = "stale"  # fonte fora do ar; servindo o último valor bom do cache
    FAILED = "failed"
    MISSING = "missing"  # conjunto de dados ainda não carregado (ex.: ETL do TSE não rodou)


@dataclass(frozen=True, slots=True)
class SourceStatus:
    name: str  # "camara", "senado", "tse_2026"...
    state: SourceState
    fetched_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Scope:
    level: Literal["brasil", "uf", "municipio"]
    uf: str | None = None
    municipality: Municipality | None = None


@dataclass(frozen=True, slots=True)
class Directory:
    scope: Scope
    view: MandateView
    items: tuple[Representative, ...]
    sources: tuple[SourceStatus, ...]
    has_next: bool  # existe algum eleito aguardando posse neste escopo?


# ---------- Atuação ("o que vem fazendo") ----------


class BlockState(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ActivityItem:
    title: str
    text: str | None = None
    url: str | None = None
    meta: str | None = None
    value: float | None = None  # para barras (ex.: gasto em reais)


@dataclass(frozen=True, slots=True)
class ActivityBlock:
    key: str  # "proposicoes", "orgaos", "frentes", "despesas", "comissoes", "autorias"
    title: str
    state: BlockState
    items: tuple[ActivityItem, ...] = ()
    note: str | None = None
    total: float | None = None
    more_url: str | None = None


@dataclass(frozen=True, slots=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class Activity:
    rep_id: str
    blocks: tuple[ActivityBlock, ...]
    links: tuple[Link, ...]
    fetched_at: datetime | None = None


# ---------- Busca ----------


@dataclass(frozen=True, slots=True)
class SearchHit:
    kind: Literal["pessoa", "municipio"]
    label: str
    detail: str
    uf: str | None
    view: MandateView | None = None
    rep_id: str | None = None
    municipality: str | None = None
