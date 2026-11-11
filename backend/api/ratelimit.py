"""Limitador de taxa por IP, em memória (janela fixa).

Escrito aqui de propósito: o slowapi dependia de enxergar as rotas em `app.routes` e,
nas versões recentes do FastAPI, rotas incluídas via `include_router` ficam fora dessa
lista, então o limite simplesmente não era aplicado (sem erro nenhum). Um teste de
integração pegou isso; este middleware não depende de nenhum detalhe interno do framework.

Com vários workers/réplicas, cada processo conta separado: o limite "de verdade"
deve ficar também no proxy reverso.
"""

import math
import time
from collections.abc import Callable, Sequence

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from backend.config import parse_rate_limit


def client_ip(request: Request, trusted_hops: int) -> str:
    """IP do cliente. `X-Forwarded-For` só é considerado atrás de proxies confiáveis.

    Com N proxies confiáveis, o IP real é a N-ésima entrada contada do fim: o que vem
    antes disso pode ter sido forjado pelo cliente.
    """
    if trusted_hops > 0:
        forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",")]
        forwarded = [p for p in forwarded if p]
        if len(forwarded) >= trusted_hops:
            return forwarded[-trusted_hops]
    return request.client.host if request.client else "unknown"


_PRUNE_ABOVE = 10_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        limit: str,
        exempt_paths: Sequence[str] = ("/health",),
        trusted_hops: int = 0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(app)
        self._max, self._window = parse_rate_limit(limit)
        self._exempt = tuple(exempt_paths)
        self._hops = trusted_hops
        self._clock = clock
        self._counters: dict[str, tuple[float, int]] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exempt:
            return await call_next(request)
        retry_after = self._hit(client_ip(request, self._hops))
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas requisições. Aguarde um instante e tente de novo."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    def _hit(self, key: str) -> int | None:
        """Registra uma requisição. Devolve segundos de espera se estourou o limite."""
        now = self._clock()
        started, count = self._counters.get(key, (now, 0))
        if now - started >= self._window:
            started, count = now, 0
        if count >= self._max:
            return max(1, math.ceil(started + self._window - now))
        self._counters[key] = (started, count + 1)
        if len(self._counters) > _PRUNE_ABOVE:
            self._counters = {k: v for k, v in self._counters.items() if now - v[0] < self._window}
        return None
