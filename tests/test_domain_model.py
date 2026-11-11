from backend.domain.models import (
    Chamber,
    ContactChannel,
    ContactKind,
    Parliamentarian,
    Role,
    Sphere,
)


def _person(chamber: Chamber) -> Parliamentarian:
    return Parliamentarian(
        id="x:1",
        chamber=chamber,
        name="Fulano",
        uf="GO",
        party=None,
        photo_url=None,
        profile_url=None,
        office=None,
        contacts=(),
    )


def test_role_and_sphere_follow_the_chamber() -> None:
    assert _person(Chamber.SENADO).role is Role.SENADOR
    assert _person(Chamber.CAMARA).role is Role.DEPUTADO_FEDERAL
    assert _person(Chamber.CAMARA).sphere is Sphere.FEDERAL


def test_contact_channel_keeps_its_provenance() -> None:
    channel = ContactChannel(
        kind=ContactKind.EMAIL,
        label="E-mail",
        value="a@camara.leg.br",
        url="mailto:a@camara.leg.br",
        source="camara:deputados/1#email",
        official=True,
    )
    assert channel.official
    assert channel.source.startswith("camara:")
