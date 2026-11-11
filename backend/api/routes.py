"""Rotas HTTP. Nada de regra de negócio aqui: só validar entrada e traduzir erros."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request

from backend.api.schemas import DirectoryOut, ErrorOut
from backend.domain.errors import UnknownUFError
from backend.domain.ufs import parse_uf
from backend.services.directory import DirectoryService

router = APIRouter(prefix="/api/v1", tags=["parlamentares"])

UFPath = Annotated[
    str,
    Path(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
        description="Sigla da UF, ex.: GO",
        examples=["GO"],
    ),
]


@router.get(
    "/parlamentares/{uf}",
    response_model=DirectoryOut,
    summary="Deputados federais e senadores em exercício de uma UF",
    responses={
        404: {"model": ErrorOut, "description": "UF inexistente"},
        503: {"model": ErrorOut, "description": "Todas as fontes oficiais indisponíveis"},
    },
)
async def list_by_uf(uf: UFPath, request: Request) -> DirectoryOut:
    try:
        code = parse_uf(uf)
    except UnknownUFError:
        raise HTTPException(status_code=404, detail="UF não encontrada") from None
    service: DirectoryService = request.app.state.directory
    return DirectoryOut.from_domain(await service.by_uf(code))
