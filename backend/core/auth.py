from ninja.security import SessionAuth


class TrocaSenhaPendente(Exception):
    """Usuário logado que ainda não trocou a senha provisória."""


class Sessao(SessionAuth):
    """Sessão do Django (cookie + CSRF) que barra quem tem troca de senha pendente.

    Use `sessao` como padrão; `sessao_troca_pendente` só nas rotas que o usuário precisa
    para conseguir trocar a senha (me, logout, trocar-senha).
    """

    def __init__(self, permitir_troca_pendente: bool = False):
        super().__init__(csrf=True)
        self.permitir_troca_pendente = permitir_troca_pendente

    def authenticate(self, request, key):
        usuario = super().authenticate(request, key)
        if usuario is not None and usuario.deve_trocar_senha and not self.permitir_troca_pendente:
            raise TrocaSenhaPendente
        return usuario


sessao = Sessao()
sessao_troca_pendente = Sessao(permitir_troca_pendente=True)


def instalar_handlers(api):
    def troca_senha_pendente(request, exc):
        return api.create_response(
            request,
            {"detail": "Troque a senha antes de continuar.", "codigo": "troca_senha_pendente"},
            status=403,
        )

    api.add_exception_handler(TrocaSenhaPendente, troca_senha_pendente)
