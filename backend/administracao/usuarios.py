"""Gestão de usuários pelo painel. Ninguém é apagado: sair do curso é desativar.

Sessões: trocar a senha (reset) e desativar já derrubam as sessões abertas do usuário. Ver
docs/adr/0002-encerrar-sessoes.md.
"""

import secrets

from axes.utils import reset as axes_reset
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection, transaction
from django.db.models import Q

from contas.models import GRUPO_CADETE, Turma
from core.erros import RegraViolada
from core.permissoes import exigir

Usuario = get_user_model()

PERMISSAO = "contas.gerenciar_usuarios"
GRUPOS = ["Cadete", "Oficial", "Comandante", "Administrador"]

# Sem 0/o, 1/l/i: a senha temporária é lida na tela e digitada à mão.
_ALFABETO = "abcdefghjkmnpqrstuvwxyz23456789"

# Chave do pg_advisory_xact_lock que serializa mudanças de quem administra.
_TRAVA_ADMINISTRADORES = 6_000_001


def gerar_senha_temporaria() -> str:
    """Três blocos de 4 caracteres (~59 bits), ex.: "k7mq-2xpa-9dhe". Não é guardada em
    lugar nenhum: o hash vai para o banco e o texto é devolvido uma única vez."""
    return "-".join("".join(secrets.choice(_ALFABETO) for _ in range(4)) for _ in range(3))


def _permissao(codigo: str) -> Permission:
    app_label, codename = codigo.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def administradores_ativos():
    perm = _permissao(PERMISSAO)
    return Usuario.objects.filter(
        Q(groups__permissions=perm) | Q(user_permissions=perm) | Q(is_superuser=True),
        is_active=True,
    ).distinct()


def _travar_administradores():
    # Dois administradores rebaixando um ao outro ao mesmo tempo não podem, juntos, deixar
    # o sistema sem nenhum.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_TRAVA_ADMINISTRADORES])


def _conferir_administradores(admin):
    if not administradores_ativos().exists():
        raise RegraViolada("O sistema precisa de pelo menos um administrador ativo.")
    if not administradores_ativos().filter(pk=admin.pk).exists():
        raise RegraViolada("Você não pode remover a sua própria permissão de administrar.")


def _validar(numerica=None, nome=None, email=None, grupos=None):
    if numerica is not None and not numerica:
        raise RegraViolada("Informe a numérica.")
    if nome is not None and not nome:
        raise RegraViolada("Informe o nome.")
    if email:
        try:
            validate_email(email)
        except ValidationError:
            raise RegraViolada("E-mail inválido.") from None
    if grupos is not None:
        invalidos = sorted(set(grupos) - set(GRUPOS))
        if invalidos:
            raise RegraViolada(f"Grupo inválido: {', '.join(invalidos)}.")


def _turma(turma_id):
    if turma_id is None:
        return None
    turma = Turma.objects.filter(pk=turma_id).first()
    if turma is None:
        raise RegraViolada("Turma inválida.")
    if not turma.ativa:
        raise RegraViolada("Esta turma está arquivada.")
    return turma


def _aplicar_anotar(usuario, anotar: bool):
    perm = _permissao("anotacoes.anotar")
    if anotar:
        usuario.user_permissions.add(perm)
    else:
        usuario.user_permissions.remove(perm)


def _conferir_cadete_tem_turma(usuario):
    if usuario.groups.filter(name=GRUPO_CADETE).exists() and usuario.turma_id is None:
        raise RegraViolada("Cadete precisa de uma turma.")


@transaction.atomic
def criar_usuario(
    admin, *, numerica, nome, email="", turma_id=None, grupos=(), anotar=False
) -> tuple:
    """Devolve (usuario, senha_temporaria)."""
    exigir(admin, PERMISSAO)
    numerica, nome, email = numerica.strip(), nome.strip(), email.strip()
    _validar(numerica, nome, email, grupos)
    if Usuario.objects.filter(numerica__iexact=numerica).exists():
        raise RegraViolada("Já existe um usuário com esta numérica.")

    senha = gerar_senha_temporaria()
    usuario = Usuario.objects.create_user(
        numerica=numerica,
        password=senha,
        nome=nome,
        email=email,
        turma=_turma(turma_id),
        deve_trocar_senha=True,
    )
    usuario.groups.set(Group.objects.filter(name__in=grupos))
    _aplicar_anotar(usuario, anotar)
    _conferir_cadete_tem_turma(usuario)
    return usuario, senha


_NAO_INFORMADO = object()


@transaction.atomic
def editar_usuario(
    admin,
    usuario,
    *,
    nome=None,
    email=None,
    turma_id=_NAO_INFORMADO,
    grupos=None,
    anotar=None,
):
    """Muda só o que foi informado (PATCH)."""
    exigir(admin, PERMISSAO)
    _travar_administradores()
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    nome = nome.strip() if nome is not None else None
    email = email.strip() if email is not None else None
    _validar(nome=nome, email=email, grupos=grupos)

    if nome is not None:
        usuario.nome = nome
    if email is not None:
        usuario.email = email
    if turma_id is not _NAO_INFORMADO:
        # Mover para uma turma arquivada não faz sentido; manter a atual (mesmo arquivada) sim.
        usuario.turma = usuario.turma if turma_id == usuario.turma_id else _turma(turma_id)
    usuario.save()
    if grupos is not None:
        usuario.groups.set(Group.objects.filter(name__in=grupos))
    if anotar is not None:
        _aplicar_anotar(usuario, anotar)

    _conferir_cadete_tem_turma(usuario)
    _conferir_administradores(admin)
    return usuario


def _em_lote(ids) -> list:
    ids = set(ids)
    if not ids:
        raise RegraViolada("Escolha pelo menos um usuário.")
    usuarios = list(Usuario.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    if len(usuarios) != len(ids):
        raise RegraViolada("Algum dos usuários escolhidos não existe mais.")
    return usuarios


@transaction.atomic
def definir_ativo_em_lote(admin, ids, ativo: bool) -> int:
    """Tudo ou nada: se um não pode mudar (a própria conta, o último administrador), nenhum
    muda. Devolve quantos mudaram de fato (os que já estavam assim ficam como estão)."""
    exigir(admin, PERMISSAO)
    _travar_administradores()
    usuarios = _em_lote(ids)
    if not ativo and any(u.pk == admin.pk for u in usuarios):
        raise RegraViolada("Você não pode desativar a si mesmo.")
    mudam = [u for u in usuarios if u.is_active != ativo]
    for usuario in mudam:  # save() um a um: cada mudança entra no histórico
        usuario.is_active = ativo
        usuario.save(update_fields=["is_active"])
    _conferir_administradores(admin)
    return len(mudam)


def definir_ativo(admin, usuario, ativo: bool):
    definir_ativo_em_lote(admin, [usuario.pk], ativo)
    usuario.refresh_from_db()
    return usuario


@transaction.atomic
def definir_anotar_em_lote(admin, ids, anotar: bool) -> int:
    """Dá ou tira a permissão individual de anotar. Devolve quantos mudaram."""
    exigir(admin, PERMISSAO)
    usuarios = _em_lote(ids)
    perm = _permissao("anotacoes.anotar")
    com_permissao = set(
        perm.user_set.filter(pk__in=[u.pk for u in usuarios]).values_list("pk", flat=True)
    )
    mudam = [u for u in usuarios if (u.pk in com_permissao) != anotar]
    for usuario in mudam:
        _aplicar_anotar(usuario, anotar)
    return len(mudam)


@transaction.atomic
def resetar_senha(admin, usuario) -> str:
    """Nova senha temporária; as sessões abertas do usuário deixam de valer."""
    exigir(admin, PERMISSAO)
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    senha = gerar_senha_temporaria()
    usuario.set_password(senha)
    usuario.deve_trocar_senha = True
    # A senha fica fora do histórico; o motivo registra que houve o reset.
    usuario._change_reason = "Senha redefinida pelo painel"
    usuario.save(update_fields=["password", "deve_trocar_senha"])
    # Quem esqueceu a senha costuma ter errado várias vezes: libera o bloqueio do axes.
    axes_reset(username=usuario.numerica)
    return senha
