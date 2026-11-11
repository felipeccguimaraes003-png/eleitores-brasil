from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from tests import fixtures as fx


def _upstream(*, camara_ok: bool = True, senado_ok: bool = True) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        if host == "dadosabertos.camara.leg.br":
            if not camara_ok:
                return httpx.Response(500)
            if path.endswith("/deputados"):
                return httpx.Response(
                    200,
                    json=fx.camara_list(
                        [fx.camara_row(1, "Ana Lima"), fx.camara_row(2, "Bia Souza")]
                    ),
                )
            deputy = int(path.rsplit("/", 1)[1])
            networks = ["https://www.instagram.com/analima/"] if deputy == 1 else []
            return httpx.Response(200, json=fx.camara_detail(deputy, networks=networks))
        if host == "legis.senado.leg.br":
            if not senado_ok:
                return httpx.Response(503)
            return httpx.Response(
                200,
                json=fx.senado_list(
                    [fx.senado_row(10, "Zé Senador"), fx.senado_row(11, "Outro UF", "SP")]
                ),
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _client(transport: httpx.MockTransport | None = None, **overrides: Any) -> TestClient:
    base: dict[str, Any] = {
        "http_max_retries": 0,
        "http_backoff_seconds": 0,
        "rate_limit": "1000/minute",
    }
    settings = Settings(_env_file=None, **{**base, **overrides})
    return TestClient(create_app(settings, transport=transport or _upstream()))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with _client() as test_client:
        yield test_client


def test_happy_path(client: TestClient) -> None:
    response = client.get("/api/v1/parlamentares/go")
    assert response.status_code == 200
    body = response.json()
    assert body["uf"] == "GO"
    assert body["uf_name"] == "Goiás"
    assert [p["name"] for p in body["items"]] == ["Zé Senador", "Ana Lima", "Bia Souza"]
    assert body["summary"]["by_chamber"] == {"camara": 2, "senado": 1}
    assert {s["name"]: s["state"] for s in body["sources"]} == {"camara": "ok", "senado": "ok"}
    ana = next(p for p in body["items"] if p["name"] == "Ana Lima")
    instagram = next(c for c in ana["contacts"] if c["kind"] == "instagram")
    assert instagram["url"] == "https://www.instagram.com/analima/"
    assert instagram["source"] == "camara:deputados/1#redeSocial"
    assert all(c["source"] for p in body["items"] for c in p["contacts"])  # sem fonte, sem contato


def test_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/parlamentares/GO")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    # O Swagger precisa carregar scripts: sem a CSP restrita da API.
    assert "content-security-policy" not in client.get("/docs").headers


@pytest.mark.parametrize(("uf", "status"), [("XX", 404), ("G", 422), ("GOO", 422), ("12", 422)])
def test_invalid_uf(client: TestClient, uf: str, status: int) -> None:
    assert client.get(f"/api/v1/parlamentares/{uf}").status_code == status


def test_one_source_down_is_reported_not_fatal() -> None:
    with _client(_upstream(camara_ok=False)) as client:
        body = client.get("/api/v1/parlamentares/GO").json()
    assert [p["name"] for p in body["items"]] == ["Zé Senador"]
    assert {s["name"]: s["state"] for s in body["sources"]} == {"camara": "failed", "senado": "ok"}


def test_all_sources_down_returns_503_without_leaking_internals() -> None:
    with _client(_upstream(camara_ok=False, senado_ok=False)) as client:
        response = client.get("/api/v1/parlamentares/GO")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"
    text = response.text.lower()
    assert "camara.leg.br" not in text
    assert "http 500" not in text


def test_rate_limit() -> None:
    with _client(rate_limit="2/minute") as client:
        codes = [client.get("/api/v1/parlamentares/GO").status_code for _ in range(3)]
        assert codes == [200, 200, 429]
        assert client.get("/health").status_code == 200  # healthcheck não conta


def test_docs_can_be_disabled() -> None:
    with _client(enable_docs=False) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_cors_is_closed_by_default_and_allowlist_only() -> None:
    headers = {"Origin": "https://meusite.example"}
    with _client() as client:
        assert "access-control-allow-origin" not in client.get("/health", headers=headers).headers
    with _client(cors_origins=["https://meusite.example"]) as client:
        allowed = client.get("/health", headers=headers)
        assert allowed.headers["access-control-allow-origin"] == "https://meusite.example"
        other = client.get("/health", headers={"Origin": "https://outro.example"})
        assert "access-control-allow-origin" not in other.headers


def test_settings_reject_non_https_upstream() -> None:
    with pytest.raises(ValueError, match="https"):
        Settings(_env_file=None, camara_base_url="http://inseguro.example")


def test_rate_limit_uses_forwarded_for_only_behind_trusted_proxy() -> None:
    def hit(client: TestClient, ip: str) -> int:
        return int(
            client.get("/api/v1/parlamentares/GO", headers={"X-Forwarded-For": ip}).status_code
        )

    # Sem proxy confiável, o cabeçalho é ignorado: forjar IPs não burla o limite.
    with _client(rate_limit="2/minute") as client:
        assert [hit(client, f"1.1.1.{i}") for i in range(3)] == [200, 200, 429]
    # Com 1 proxy confiável, vale a última entrada (a que o proxy viu).
    with _client(rate_limit="2/minute", trusted_proxy_hops=1) as client:
        assert [hit(client, f"9.9.9.9, 10.0.0.{i}") for i in range(3)] == [200, 200, 200]
        assert [hit(client, "9.9.9.9, 10.0.0.1") for _ in range(2)] == [200, 429]


def test_rate_limit_rejects_bad_format() -> None:
    with pytest.raises(ValueError, match="N/second"):
        Settings(_env_file=None, rate_limit="muito")


def test_items_expose_sphere_role_and_update_time(client: TestClient) -> None:
    body = client.get("/api/v1/parlamentares/GO").json()
    by_name = {p["name"]: p for p in body["items"]}
    assert by_name["Ana Lima"]["sphere"] == "federal"
    assert by_name["Ana Lima"]["role"] == "deputado_federal"
    assert by_name["Zé Senador"]["role"] == "senador"
    assert all(p["updated_at"] is not None for p in body["items"])
    assert all(c["official"] is True for p in body["items"] for c in p["contacts"])
