"""Cabeçalhos de segurança para todas as respostas."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_API_CSP = "default-src 'none'; frame-ancestors 'none'"
_API_PREFIXES = ("/api/", "/health")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), camera=(), microphone=()"
        )
        if request.url.path.startswith(_API_PREFIXES):
            # A CSP restrita só vale para a API; o Swagger (/docs) precisa carregar scripts.
            response.headers.setdefault("Content-Security-Policy", _API_CSP)
        return response
