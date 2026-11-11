"""Raiz de composição: é aqui (e só aqui) que adaptadores e serviços se encontram."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.adapters.camara import CamaraSource
from backend.adapters.http import HttpJsonClient
from backend.adapters.senado import SenadoSource
from backend.api.middleware import SecurityHeadersMiddleware
from backend.api.ratelimit import RateLimitMiddleware
from backend.api.routes import router
from backend.config import Settings, get_settings
from backend.domain.errors import SourceUnavailableError
from backend.services.directory import DirectoryService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Fábrica da aplicação. `transport` permite simular as fontes nos testes."""
    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(
            timeout=cfg.http_timeout_seconds,
            headers={"User-Agent": cfg.user_agent, "Accept": "application/json"},
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            transport=transport,
        ) as client:
            http = HttpJsonClient(
                client, retries=cfg.http_max_retries, backoff=cfg.http_backoff_seconds
            )
            app.state.directory = DirectoryService(
                [
                    CamaraSource(
                        http, base_url=cfg.camara_base_url, concurrency=cfg.camara_concurrency
                    ),
                    SenadoSource(http, base_url=cfg.senado_base_url),
                ],
                ttl=cfg.cache_ttl_seconds,
                partial_ttl=cfg.cache_partial_ttl_seconds,
                max_stale=cfg.cache_max_stale_seconds,
                failure_cooldown=cfg.cache_failure_cooldown_seconds,
            )
            yield

    app = FastAPI(
        title="Eleitores Brasil API",
        version="0.3.0",
        description="Parlamentares federais por UF, com contatos e procedência de cada dado.",
        lifespan=lifespan,
        docs_url="/docs" if cfg.enable_docs else None,
        redoc_url="/redoc" if cfg.enable_docs else None,
        openapi_url="/openapi.json" if cfg.enable_docs else None,
    )

    # Ordem: o último adicionado é o mais externo. Cabeçalhos de segurança valem até
    # para respostas 429 do limitador.
    app.add_middleware(
        RateLimitMiddleware, limit=cfg.rate_limit, trusted_hops=cfg.trusted_proxy_hops
    )
    app.add_middleware(SecurityHeadersMiddleware)
    if cfg.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors_origins,
            allow_methods=["GET"],
            allow_headers=[],
        )

    @app.exception_handler(SourceUnavailableError)
    async def _source_unavailable(_: Request, exc: SourceUnavailableError) -> JSONResponse:
        logger.warning("503 servido: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Fontes oficiais temporariamente indisponíveis. Tente em instantes."
            },
            headers={"Retry-After": "30"},
        )

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
