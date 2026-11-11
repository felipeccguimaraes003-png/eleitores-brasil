import pytest

from backend.api.ratelimit import RateLimitMiddleware
from backend.config import parse_rate_limit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("120/minute", (120, 60)), ("5/second", (5, 1)), ("1000/hour", (1000, 3600))],
)
def test_parse_rate_limit(raw: str, expected: tuple[int, int]) -> None:
    assert parse_rate_limit(raw) == expected


@pytest.mark.parametrize("raw", ["", "0/minute", "10/day", "abc", "10 / minute", "-1/minute"])
def test_parse_rate_limit_rejects(raw: str) -> None:
    with pytest.raises(ValueError, match="N/second"):
        parse_rate_limit(raw)


def test_fixed_window_resets_and_reports_retry_after() -> None:
    now = 100.0
    limiter = RateLimitMiddleware(lambda *_: None, limit="2/minute", clock=lambda: now)  # type: ignore[arg-type]
    assert limiter._hit("a") is None
    assert limiter._hit("a") is None
    assert limiter._hit("a") == 60
    assert limiter._hit("b") is None  # outro cliente tem contador próprio
    now = 130.0
    assert limiter._hit("a") == 30
    now = 160.0
    assert limiter._hit("a") is None  # janela nova
