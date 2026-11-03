"""Turmas e tipos de punição pelo painel. Nada é apagado: turma formada é arquivada e
punição sai de uso desativada (continua nos despachos antigos)."""

from django.contrib.auth import get_user_model
from django.db import transaction

from administracao.usuarios import PERMISSAO
from anotacoes.models import TipoPunicao
from contas.models import Turma
from core.erros import RegraViolada
from core.permissoes import exigir

Usuario = get_user_model()


_MENSAGENS = {
    Turma: ("Informe o nome da turma.", "Já existe uma turma com este nome."),
    TipoPunicao: (
        "Informe o nome do tipo de punição.",
        "Já existe um tipo de punição com este nome.",
    ),
}


def _nome(nome: str, modelo, *, exceto=None) -> str:
    vazio, repetido_msg = _MENSAGENS[modelo]
    nome = " ".join(nome.split())
    if not nome:
        raise RegraViolada(vazio)
    repetido = modelo.objects.filter(nome__iexact=nome)
    if exceto is not None:
        repetido = repetido.exclude(pk=exceto.pk)
    if repetido.exists():
        raise RegraViolada(repetido_msg)
    return nome


def _ano(ano: int) -> int:
    if not 1990 <= ano <= 2100:
        raise RegraViolada("Ano de ingresso inválido.")
    return ano


# Turmas


@transaction.atomic
def criar_turma(admin, nome: str, ano_ingresso: int) -> Turma:
    exigir(admin, PERMISSAO)
    return Turma.objects.create(nome=_nome(nome, Turma), ano_ingresso=_ano(ano_ingresso))


@transaction.atomic
def editar_turma(admin, turma, *, nome=None, ano_ingresso=None, ativa=None) -> Turma:
    exigir(admin, PERMISSAO)
    turma = Turma.objects.select_for_update().get(pk=turma.pk)
    if nome is not None:
        turma.nome = _nome(nome, Turma, exceto=turma)
    if ano_ingresso is not None:
        turma.ano_ingresso = _ano(ano_ingresso)
    if ativa is not None:
        turma.ativa = ativa
    turma.save()
    return turma


@transaction.atomic
def mover_cadetes(admin, cadete_ids: list[int], destino_id: int) -> int:
    exigir(admin, PERMISSAO)
    destino = Turma.objects.filter(pk=destino_id).first()
    if destino is None or not destino.ativa:
        raise RegraViolada("Escolha uma turma de destino ativa.")
    ids = set(cadete_ids)
    if not ids:
        raise RegraViolada("Escolha pelo menos um cadete.")
    # O grupo Cadete aparece uma vez por usuário: o join não duplica linhas (e FOR UPDATE
    # não aceita DISTINCT). Trava só as linhas de usuário.
    cadetes = list(
        Usuario.objects.select_for_update(of=("self",)).filter(pk__in=ids, groups__name="Cadete")
    )
    if len(cadetes) != len(ids):
        raise RegraViolada("Só cadetes podem ser movidos de turma.")
    for cadete in cadetes:  # save() um a um: cada mudança entra no histórico
        cadete.turma = destino
        cadete.save(update_fields=["turma"])
    return len(cadetes)


@transaction.atomic
def formar_turma(admin, turma) -> int:
    """Arquiva a turma e desativa os cadetes dela. Devolve quantos foram desativados."""
    exigir(admin, PERMISSAO)
    turma = Turma.objects.select_for_update().get(pk=turma.pk)
    if not turma.ativa:
        raise RegraViolada("Esta turma já está arquivada.")
    turma.ativa = False
    turma._change_reason = "Turma formada"
    turma.save(update_fields=["ativa"])
    cadetes = list(Usuario.objects.select_for_update().filter(turma=turma, is_active=True))
    for cadete in cadetes:
        cadete.is_active = False
        cadete._change_reason = f"Turma {turma.nome} formada"
        cadete.save(update_fields=["is_active"])
    return len(cadetes)


# Tipos de punição


@transaction.atomic
def criar_punicao(admin, nome: str) -> TipoPunicao:
    exigir(admin, PERMISSAO)
    return TipoPunicao.objects.create(nome=_nome(nome, TipoPunicao))


@transaction.atomic
def editar_punicao(admin, punicao, *, nome=None, ativo=None) -> TipoPunicao:
    exigir(admin, PERMISSAO)
    punicao = TipoPunicao.objects.select_for_update().get(pk=punicao.pk)
    if nome is not None:
        punicao.nome = _nome(nome, TipoPunicao, exceto=punicao)
    if ativo is not None:
        punicao.ativo = ativo
    punicao.save()
    return punicao
