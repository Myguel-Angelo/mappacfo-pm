"""Login pelo nome de guerra: cadetes com "CAD " na frente, os demais só com o nome.

O texto digitado vira uma conta (resolver) antes de qualquer senha ser conferida, e o
bloqueio do axes conta as falhas por essa conta, não pelo texto: "CAD BRUNA", "CAD BRUNI"...
somam todas contra BRUNO, então variar a grafia não ganha tentativas a mais.
"""

from django.contrib.auth.backends import ModelBackend

from contas import nome_guerra as ng
from contas.models import GRUPO_CADETE, Usuario

# Abaixo disso, um erro de digitação já cai em outro nome com facilidade ("ANA" e "ANE").
TAMANHO_MINIMO_PARA_TOLERAR = 4


def resolver(texto: str) -> Usuario | None:
    """A conta que o texto de login aponta, ou None. A senha não entra aqui."""
    cadete, resto = ng.separar_prefixo(texto)
    alvo = ng.chave(resto)
    if not alvo:
        return None

    # O nome existe (exato): é essa pessoa, se o CAD bater com ser cadete. Um cadete que
    # esqueceu o CAD não é "corrigido" para outra pessoa parecida.
    exato = Usuario.objects.filter(chave_login=alvo).first()
    if exato is not None:
        return exato if exato.eh_cadete == cadete else None
    if len(alvo) < TAMANHO_MINIMO_PARA_TOLERAR:
        return None

    # Um erro de digitação só vale se apontar para uma única pessoa ativa do mesmo grupo.
    grupo = (
        Usuario.objects.filter(groups__name=GRUPO_CADETE)
        if cadete
        else Usuario.objects.exclude(groups__name=GRUPO_CADETE)
    )
    parecidos = [
        pk
        for pk, chave in grupo.filter(is_active=True, chave_login__isnull=False).values_list(
            "pk", "chave_login"
        )
        if ng.um_erro(alvo, chave)
    ]
    return Usuario.objects.get(pk=parecidos[0]) if len(parecidos) == 1 else None


class NomeDeGuerraBackend(ModelBackend):
    """authenticate(request, login=..., password=...). O ModelBackend continua depois dele
    só para o admin do Django, que entra pela numérica."""

    def authenticate(self, request, login=None, password=None, **kwargs):
        if login is None or password is None:
            return None
        usuario = resolver(login)
        if usuario is None:
            # Mesmo custo de hash de quem existe: o tempo da resposta não diz se o nome existe.
            Usuario().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None


def usuario_do_axes(request, credentials):
    """Com quem o axes conta as falhas (AXES_USERNAME_CALLABLE): a numérica da conta que
    o texto aponta; texto que não aponta para ninguém conta como ele mesmo, marcado com "?"
    para não somar com uma numérica de verdade."""
    credentials = credentials or {}
    if "login" in credentials:
        texto = credentials["login"] or ""
        usuario = resolver(texto)
        return usuario.numerica if usuario else f"? {' '.join(texto.split())[:40]}"
    # Admin do Django (formulário com "username" = numérica).
    return credentials.get("username")
