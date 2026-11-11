"""Validação e normalização de dados vindos de fontes externas.

Tudo que chega de fora é tratado como não confiável: URLs passam por lista de hosts,
e-mails e handles por regex estrita, telefones por normalização.
"""

import re
import unicodedata
from urllib.parse import quote, urlsplit

# Hosts de onde aceitamos imagens e páginas oficiais.
OFFICIAL_HOSTS: frozenset[str] = frozenset(
    {
        "www.camara.leg.br",
        "www2.camara.leg.br",
        "www.senado.leg.br",
        "www12.senado.leg.br",
        "www25.senado.leg.br",
        "cdn.tse.jus.br",
    }
)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)+$")
_HANDLE_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
_INSTAGRAM_HOSTS = frozenset({"instagram.com", "www.instagram.com"})
_INSTAGRAM_NON_PROFILE = frozenset(
    {"p", "reel", "reels", "explore", "stories", "accounts", "tv", "about", "direct"}
)


def clean_text(value: object) -> str | None:
    """Texto aparado, sem caracteres de controle; None se vazio ou não-string."""
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if ch.isprintable()).strip()
    return cleaned or None


def sort_key(text: str) -> str:
    """Chave de ordenação sem acento e sem distinção de caixa."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def safe_official_url(url: object, allowed_hosts: frozenset[str] = OFFICIAL_HOSTS) -> str | None:
    """Devolve a URL em https se o host estiver na lista; senão None.

    As fontes do Senado ainda devolvem `http://` para fotos; promovemos para https.
    """
    text = clean_text(url)
    if text is None:
        return None
    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"} or parts.hostname not in allowed_hosts:
        return None
    if parts.username or parts.password or parts.port not in {None, 80, 443}:
        return None
    path = parts.path or "/"
    query = f"?{parts.query}" if parts.query else ""
    return f"https://{parts.hostname}{path}{query}"


def valid_email(value: object) -> str | None:
    text = clean_text(value)
    if text is None or len(text) > 254 or not _EMAIL_RE.match(text):
        return None
    return text.lower()


def mailto_url(email: str) -> str:
    return f"mailto:{quote(email, safe='@')}"


def instagram_handle_from_url(url: object) -> str | None:
    """Extrai o @ de uma URL de perfil do Instagram; None para qualquer outra coisa."""
    text = clean_text(url)
    if text is None:
        return None
    parts = urlsplit(text if "://" in text else f"https://{text}")
    if parts.scheme not in {"http", "https"} or parts.hostname not in _INSTAGRAM_HOSTS:
        return None
    segments = [s for s in parts.path.split("/") if s]
    if not segments:
        return None
    handle = segments[0].lstrip("@")
    if handle.lower() in _INSTAGRAM_NON_PROFILE or not _HANDLE_RE.match(handle):
        return None
    return handle.lower()


def instagram_url(handle: str) -> str:
    return f"https://www.instagram.com/{handle}/"


def normalize_phone_br(raw: object, default_area: str = "61") -> tuple[str, str] | None:
    """Devolve (texto para exibir, número E.164) ou None.

    Números de 8 ou 9 dígitos sem DDD recebem `default_area`: os gabinetes do
    Congresso ficam em Brasília (DDD 61).
    """
    text = clean_text(raw)
    if text is None:
        return None
    digits = re.sub(r"\D", "", text)
    if digits.startswith("55") and len(digits) in {12, 13}:
        digits = digits[2:]
    if len(digits) in {8, 9}:
        digits = default_area + digits
    if len(digits) not in {10, 11}:
        return None
    area, number = digits[:2], digits[2:]
    return f"({area}) {number[:-4]}-{number[-4:]}", f"+55{digits}"
