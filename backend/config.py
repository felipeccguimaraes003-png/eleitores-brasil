"""Configuração via variáveis de ambiente (12-factor)."""

import re
from functools import lru_cache
from typing import Annotated

from pydantic import AfterValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_RATE_RE = re.compile(r"^(\d{1,6})/(second|minute|hour)$")
_WINDOWS = {"second": 1, "minute": 60, "hour": 3600}


def parse_rate_limit(value: str) -> tuple[int, int]:
    """'120/minute' -> (120, 60). Levanta ValueError se o formato for inválido."""
    match = _RATE_RE.match(value.strip())
    if match is None or int(match.group(1)) < 1:
        raise ValueError("use o formato N/second, N/minute ou N/hour (ex.: 120/minute)")
    return int(match.group(1)), _WINDOWS[match.group(2)]


def _valid_rate(value: str) -> str:
    parse_rate_limit(value)
    return value


def _https_only(value: str) -> str:
    if not value.startswith("https://"):
        raise ValueError("a URL precisa começar com https://")
    return value.rstrip("/")


HttpsUrl = Annotated[str, AfterValidator(_https_only)]
RateLimit = Annotated[str, AfterValidator(_valid_rate)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Cache
    cache_ttl_seconds: int = Field(900, ge=0, le=86_400)
    cache_partial_ttl_seconds: int = Field(60, ge=0, le=3_600)
    cache_max_stale_seconds: int = Field(86_400, ge=0, le=604_800)
    cache_failure_cooldown_seconds: int = Field(15, ge=0, le=300)

    # Cliente HTTP das fontes oficiais
    http_timeout_seconds: float = Field(10.0, gt=0, le=60)
    http_max_retries: int = Field(2, ge=0, le=5)
    http_backoff_seconds: float = Field(0.5, ge=0, le=10)
    camara_concurrency: int = Field(8, ge=1, le=32)
    camara_base_url: HttpsUrl = "https://dadosabertos.camara.leg.br/api/v2"
    senado_base_url: HttpsUrl = "https://legis.senado.leg.br/dadosabertos"
    user_agent: str = "eleitores-brasil/0.1 (projeto de utilidade publica)"

    # API
    rate_limit: RateLimit = "120/minute"
    # Quantos proxies confiáveis (ex.: Caddy/Traefik) ficam na frente da API.
    trusted_proxy_hops: int = Field(0, ge=0, le=5)
    # JSON na variável de ambiente, ex.: CORS_ORIGINS='["https://meusite.com"]'
    cors_origins: list[str] = Field(default_factory=list)
    enable_docs: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
