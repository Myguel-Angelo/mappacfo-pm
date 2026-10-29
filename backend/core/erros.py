"""Exceções de domínio e como a API as converte em resposta.

Serviços levantam estas exceções em vez de HttpError: as regras não dependem do HTTP e
podem ser testadas sem ele.
"""

from core.auth import TrocaSenhaPendente


class RegraViolada(Exception):
    """Ação proibida por uma regra de negócio (vira 400 com a mensagem)."""

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class SemPermissao(Exception):
    """Usuário sem a permissão exigida (vira 403)."""


def instalar_handlers(api):
    def resposta(request, status, detail, codigo=None):
        return api.create_response(request, {"detail": detail, "codigo": codigo}, status=status)

    api.add_exception_handler(
        RegraViolada, lambda request, exc: resposta(request, 400, exc.mensagem, "regra_violada")
    )
    api.add_exception_handler(
        SemPermissao,
        lambda request, exc: resposta(
            request, 403, "Sem permissão para esta ação.", "sem_permissao"
        ),
    )
    api.add_exception_handler(
        TrocaSenhaPendente,
        lambda request, exc: resposta(
            request, 403, "Troque a senha antes de continuar.", "troca_senha_pendente"
        ),
    )
