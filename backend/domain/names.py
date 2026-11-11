"""Nomes: forma de exibição e chave de comparação.

O TSE publica tudo em maiúsculas ("LUIZ INÁCIO LULA DA SILVA", "ALTA FLORESTA D'OESTE").
`smart_title` devolve uma forma legível; `name_key` devolve a chave usada para comparar
nomes entre fontes (sem acento, sem pontuação, maiúscula).
"""

import re
import unicodedata

_PARTICLES = frozenset(
    {"da", "de", "do", "das", "dos", "e", "di", "du", "del", "della", "la", "van", "von"}
)
_TITLES = {
    "DR": "Dr.",
    "DRA": "Dra.",
    "SR": "Sr.",
    "SRA": "Sra.",
    "JR": "Jr.",
    "PROF": "Prof.",
    "PROFA": "Profa.",
}
_ROMAN = frozenset({"II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "XIII"})
_VOWELS = frozenset("AEIOUÁÉÍÓÚÂÊÔÃÕÀÜY")
_SPLIT = re.compile(r"([-'’])")


def _cap(part: str) -> str:
    return part[:1].upper() + part[1:].lower()


def _title_token(token: str, *, first: bool) -> str:
    bare = token.rstrip(".").upper()
    if bare in _TITLES:
        return _TITLES[bare]
    if not first and token.lower() in _PARTICLES:
        return token.lower()
    if bare in _ROMAN or any(ch.isdigit() for ch in token):
        return token.upper()
    letters = [ch for ch in bare if ch.isalpha()]
    if 2 <= len(letters) <= 4 and not any(ch in _VOWELS for ch in letters):
        return token.upper()  # siglas como PM, PRF, SGT, DJ
    # Hífen e apóstrofo: "GUAJARÁ-MIRIM" -> "Guajará-Mirim", "D'OESTE" -> "D'Oeste".
    return "".join(p if p in "-'’" else _cap(p) for p in _SPLIT.split(token))


def smart_title(text: str) -> str:
    """Converte NOME EM MAIÚSCULAS em "Nome em Maiúsculas", respeitando partículas."""
    tokens = text.split()
    return " ".join(_title_token(tok, first=index == 0) for index, tok in enumerate(tokens))


def name_key(text: str) -> str:
    """Chave de comparação: sem acentos, só letras e espaços simples, em maiúsculas."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^A-Za-z ]+", " ", plain).upper().split())
