from ninja.errors import HttpError


def exigir(request, *perms: str):
    """Levanta 403 se o usuário não tiver todas as permissões ("app.codename").

    Toda rota de escrita chama isto (ou um serviço que chama): esconder botão no
    frontend não é segurança.
    """
    if not request.user.has_perms(perms):
        raise HttpError(403, "Sem permissão para esta ação.")
