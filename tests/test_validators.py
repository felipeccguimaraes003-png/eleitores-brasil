import pytest

from backend.domain.errors import UnknownUFError
from backend.domain.ufs import UF_NAMES, parse_uf
from backend.domain.validators import (
    instagram_handle_from_url,
    mailto_url,
    normalize_phone_br,
    safe_official_url,
    sort_key,
    valid_email,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.instagram.com/Abouanni/?hl=pt", "abouanni"),
        ("https://instagram.com/foo.bar_1/", "foo.bar_1"),
        ("instagram.com/foo", "foo"),
        ("https://www.instagram.com/@foo", "foo"),
        ("https://www.instagram.com/foo/reels/", "foo"),
        ("https://www.instagram.com/p/Cxyz123/", None),
        ("https://www.instagram.com/", None),
        ("https://evil.com/instagram.com/foo", None),
        ("https://instagram.com.evil.com/foo", None),
        ("https://www.instagram.com/foo bar", None),
        ("https://www.instagram.com/" + "a" * 31, None),
        ("javascript:alert(1)", None),
        ("https://twitter.com/foo", None),
        (None, None),
        (42, None),
    ],
)
def test_instagram_handle_from_url(url: object, expected: str | None) -> None:
    assert instagram_handle_from_url(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "http://www.senado.leg.br/senadores/img/a.jpg",
            "https://www.senado.leg.br/senadores/img/a.jpg",
        ),
        (
            "https://www.camara.leg.br/internet/deputado/bandep/1.jpg",
            "https://www.camara.leg.br/internet/deputado/bandep/1.jpg",
        ),
        ("https://evil.example/x.jpg", None),
        ("https://www.camara.leg.br.evil.com/x.jpg", None),
        ("https://www.camara.leg.br@evil.com/x.jpg", None),
        ("https://user:pw@www.camara.leg.br/x.jpg", None),
        ("https://www.camara.leg.br:8443/x.jpg", None),
        ("ftp://www.camara.leg.br/x.jpg", None),
        ("javascript:alert(1)", None),
        ("", None),
        (None, None),
    ],
)
def test_safe_official_url(url: object, expected: str | None) -> None:
    assert safe_official_url(url) == expected


def test_valid_email_normalizes_and_rejects() -> None:
    assert valid_email("  Dep.Fulano@Camara.leg.br ") == "dep.fulano@camara.leg.br"
    for bad in ["x@y", "a b@c.com", "@c.com", "a@@c.com", "", None, 7, "a@b.c" + "d" * 260]:
        assert valid_email(bad) is None


def test_mailto_url_quotes_unsafe_chars() -> None:
    assert mailto_url("a+b@c.com") == "mailto:a%2Bb@c.com"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3215-5325", ("(61) 3215-5325", "+556132155325")),
        ("(62) 99999-0000", ("(62) 99999-0000", "+5562999990000")),
        ("+55 61 3215 5325", ("(61) 3215-5325", "+556132155325")),
        ("123", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_phone_br(raw: object, expected: tuple[str, str] | None) -> None:
    assert normalize_phone_br(raw) == expected


def test_sort_key_ignores_accents_and_case() -> None:
    assert sort_key("Álvaro") == sort_key("alvaro")
    assert sorted(["Zé", "Álvaro", "bia"], key=sort_key) == ["Álvaro", "bia", "Zé"]


def test_parse_uf() -> None:
    assert len(UF_NAMES) == 27
    assert parse_uf(" go ") == "GO"
    with pytest.raises(UnknownUFError):
        parse_uf("XX")
