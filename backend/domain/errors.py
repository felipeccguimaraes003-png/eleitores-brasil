"""Erros de domínio. Nenhum detalhe de transporte (HTTP, URLs) vaza daqui."""


class SourceUnavailableError(Exception):
    """Uma fonte oficial não respondeu ou devolveu um formato inesperado."""


class UnknownUFError(ValueError):
    """Sigla de UF inexistente."""


class NotFoundError(LookupError):
    """O que foi pedido não existe (município, representante...)."""
