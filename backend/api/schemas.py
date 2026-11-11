"""Contrato público da API (Pydantic). Separado do domínio de propósito."""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.domain.models import Directory, Parliamentarian
from backend.domain.ufs import UF_NAMES


class ContactOut(BaseModel):
    kind: str = Field(examples=["email"])
    label: str
    value: str
    url: str
    source: str = Field(description="De onde veio este contato (procedência).")
    official: bool = Field(description="True quando veio de fonte oficial.")


class ParliamentarianOut(BaseModel):
    id: str = Field(examples=["camara:204521"])
    chamber: str = Field(examples=["camara"])
    sphere: str = Field(examples=["federal"])
    role: str = Field(examples=["deputado_federal"])
    name: str
    uf: str
    party: str | None
    photo_url: str | None
    profile_url: str | None
    office: str | None
    status: str = Field(examples=["em_exercicio"])
    updated_at: datetime | None = Field(description="Quando a fonte foi consultada.")
    contacts: list[ContactOut]

    @classmethod
    def from_domain(cls, person: Parliamentarian) -> "ParliamentarianOut":
        return cls(
            id=person.id,
            chamber=person.chamber.value,
            sphere=person.sphere.value,
            role=person.role.value,
            name=person.name,
            uf=person.uf,
            party=person.party,
            photo_url=person.photo_url,
            profile_url=person.profile_url,
            office=person.office,
            status=person.status.value,
            updated_at=person.fetched_at,
            contacts=[
                ContactOut(
                    kind=c.kind.value,
                    label=c.label,
                    value=c.value,
                    url=c.url,
                    source=c.source,
                    official=c.official,
                )
                for c in person.contacts
            ],
        )


class SourceStatusOut(BaseModel):
    name: str
    state: str = Field(description="ok | partial | stale | failed")
    fetched_at: datetime | None


class SummaryOut(BaseModel):
    total: int
    by_chamber: dict[str, int]
    by_party: dict[str, int]


class DirectoryOut(BaseModel):
    uf: str
    uf_name: str
    data_as_of: datetime
    summary: SummaryOut
    sources: list[SourceStatusOut]
    items: list[ParliamentarianOut]

    @classmethod
    def from_domain(cls, directory: Directory) -> "DirectoryOut":
        return cls(
            uf=directory.uf,
            uf_name=UF_NAMES[directory.uf],
            data_as_of=directory.data_as_of,
            summary=SummaryOut(
                total=directory.summary.total,
                by_chamber=directory.summary.by_chamber,
                by_party=directory.summary.by_party,
            ),
            sources=[
                SourceStatusOut(name=s.name, state=s.state.value, fetched_at=s.fetched_at)
                for s in directory.sources
            ],
            items=[ParliamentarianOut.from_domain(p) for p in directory.items],
        )


class ErrorOut(BaseModel):
    detail: str
