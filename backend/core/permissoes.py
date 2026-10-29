from core.erros import SemPermissao


def exigir(usuario, *perms: str):
    """Levanta SemPermissao (403) se o usuário não tiver todas as permissões ("app.codename").

    Toda ação de escrita passa por um serviço que chama isto: esconder botão no frontend
    não é segurança.
    """
    if not usuario.has_perms(perms):
        raise SemPermissao
