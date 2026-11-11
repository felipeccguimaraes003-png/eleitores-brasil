"""Mandatos: quando começa e termina cada cargo, conforme o ano da eleição.

Datas de posse (Constituição Federal, com a Emenda 111/2021):
* Presidente: 5 de janeiro (a partir dos eleitos em 2026; antes, 1º de janeiro).
* Governadores: 6 de janeiro (a partir dos eleitos em 2026; antes, 1º de janeiro).
* Senadores e deputados federais: 1º de fevereiro (art. 57, § 4º).
* Prefeitos e vereadores: 1º de janeiro.
* Deputados estaduais e distritais: a data varia conforme a Constituição de cada estado,
  por isso o mandato deles fica sem dia exato.
"""

from collections.abc import Iterable
from datetime import date

from backend.domain.models import MUNICIPAL_ROLES, Role, Term

FIRST_YEAR_WITH_NEW_DATES = 2026  # Emenda Constitucional 111/2021


def is_municipal(role: Role) -> bool:
    return role in MUNICIPAL_ROLES


def is_municipal_year(year: int) -> bool:
    """Eleições municipais: 2020, 2024, 2028... Gerais: 2022, 2026, 2030..."""
    return year % 4 == 0


def term_for(election_year: int, role: Role) -> Term:
    y = election_year
    new_dates = y >= FIRST_YEAR_WITH_NEW_DATES
    if role is Role.PRESIDENTE:
        start = date(y + 1, 1, 5) if new_dates else date(y + 1, 1, 1)
        return Term(y, start, date(y + 5, 1, 5))
    if role is Role.GOVERNADOR:
        start = date(y + 1, 1, 6) if new_dates else date(y + 1, 1, 1)
        return Term(y, start, date(y + 5, 1, 6))
    if role is Role.SENADOR:
        return Term(y, date(y + 1, 2, 1), date(y + 9, 1, 31))
    if role is Role.DEPUTADO_FEDERAL:
        return Term(y, date(y + 1, 2, 1), date(y + 5, 1, 31))
    if role is Role.DEPUTADO_ESTADUAL:
        return Term(y, None, None)
    return Term(y, date(y + 1, 1, 1), date(y + 4, 12, 31))


def effective_start(election_year: int, role: Role) -> date:
    """Data usada para decidir se um mandato já começou (1º/fev quando o dia varia)."""
    return term_for(election_year, role).start or date(election_year + 1, 2, 1)


def pick_years(available: Iterable[int], role: Role, today: date) -> tuple[int | None, int | None]:
    """Entre os anos de eleição carregados, devolve (mandato em curso, próximo mandato)."""
    years = sorted(y for y in available if is_municipal_year(y) == is_municipal(role))
    started = [y for y in years if effective_start(y, role) <= today]
    pending = [y for y in years if effective_start(y, role) > today]
    return (started[-1] if started else None, pending[0] if pending else None)
