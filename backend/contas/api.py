from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from ninja import Router, Schema, Status
from ninja.errors import HttpError
from ninja.utils import check_csrf

from core.auth import sessao_troca_pendente
from core.schemas import ErroOut

router = Router(tags=["auth"])


class TurmaOut(Schema):
    id: int
    nome: str


class MeOut(Schema):
    numerica: str
    nome: str
    email: str
    turma: TurmaOut | None
    grupos: list[str]
    permissoes: list[str]
    deve_trocar_senha: bool


class CsrfOut(Schema):
    csrftoken: str


class LoginIn(Schema):
    numerica: str
    senha: str


class TrocaSenhaIn(Schema):
    senha_atual: str
    nova_senha: str
    confirmacao: str


def dados_me(usuario):
    return {
        "numerica": usuario.numerica,
        "nome": usuario.nome,
        "email": usuario.email,
        "turma": usuario.turma,
        "grupos": sorted(usuario.groups.values_list("name", flat=True)),
        "permissoes": sorted(usuario.get_all_permissions()),
        "deve_trocar_senha": usuario.deve_trocar_senha,
    }


@router.get("/csrf", auth=None, response=CsrfOut)
def csrf(request):
    # get_token marca o cookie para ser enviado pelo CsrfViewMiddleware na resposta.
    return {"csrftoken": get_token(request)}


@router.post("/login", auth=None, response={200: MeOut, 401: ErroOut})
def entrar(request, dados: LoginIn):
    # Rotas do Ninja são csrf_exempt; sem auth de sessão, o CSRF precisa ser checado aqui.
    if check_csrf(request):
        raise HttpError(403, "Falha na verificação CSRF.")

    usuario = authenticate(request, numerica=dados.numerica, password=dados.senha)
    if usuario is None:
        # Mesma mensagem para numérica inexistente e senha errada.
        # Se o axes bloquear, o AxesMiddleware troca esta resposta pelo 429.
        return Status(401, {"detail": "Numérica ou senha incorreta."})

    login(request, usuario)  # gera nova sessão (evita session fixation)
    return Status(200, dados_me(usuario))


@router.post("/logout", auth=sessao_troca_pendente, response={204: None})
def sair(request):
    logout(request)
    return Status(204, None)


@router.get("/me", auth=sessao_troca_pendente, response=MeOut)
def me(request):
    return dados_me(request.user)


@router.post("/trocar-senha", auth=sessao_troca_pendente, response={200: MeOut, 400: ErroOut})
def trocar_senha(request, dados: TrocaSenhaIn):
    usuario = request.user

    if not usuario.check_password(dados.senha_atual):
        return Status(400, {"detail": "Senha atual incorreta."})
    if dados.nova_senha != dados.confirmacao:
        return Status(400, {"detail": "A confirmação não confere com a nova senha."})
    if dados.nova_senha == dados.senha_atual:
        return Status(400, {"detail": "A nova senha precisa ser diferente da atual."})
    try:
        validate_password(dados.nova_senha, usuario)
    except ValidationError as exc:
        return Status(400, {"detail": "A nova senha não atende às regras.", "erros": exc.messages})

    usuario.set_password(dados.nova_senha)
    usuario.deve_trocar_senha = False
    usuario.save(update_fields=["password", "deve_trocar_senha"])
    update_session_auth_hash(request, usuario)  # sem isto, a troca desloga o usuário
    return Status(200, dados_me(usuario))
