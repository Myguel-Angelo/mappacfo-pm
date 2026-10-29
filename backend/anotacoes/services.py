"""Regras do ciclo da anotação. Toda ação de escrita do domínio passa por aqui.

Cada serviço: checa a permissão, trava as linhas envolvidas (select_for_update), valida as
regras e muda o status. Nada é apagado.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from anotacoes.models import Anotacao, Compensacao, Despacho, TipoPunicao
from core.erros import RegraViolada
from core.permissoes import exigir

Usuario = get_user_model()
Status = Anotacao.Status
Tipo = Anotacao.Tipo

# Status em que a punição do despacho vale e ocupa a data do cadete.
STATUS_COM_PUNICAO = [Status.DESPACHADA, Status.CUMPRIDA, Status.ARQUIVADA]
STATUS_ANULAVEIS = [Status.NOTIFICADA, Status.DESPACHADA]


def _travar(anotacao) -> Anotacao:
    """Relê a anotação travando a linha até o fim da transação."""
    return Anotacao.objects.select_for_update().get(pk=anotacao.pk)


def _travar_cadete(cadete_id):
    # Trava o cadete: duas abas despachando o mesmo cadete esperam uma pela outra, e a
    # checagem de data duplicada da segunda já enxerga o despacho da primeira.
    Usuario.objects.select_for_update().filter(pk=cadete_id).first()


def _punicao(punicao_id) -> TipoPunicao:
    punicao = TipoPunicao.objects.filter(pk=punicao_id).first()
    if punicao is None:
        raise RegraViolada("Tipo de punição inválido.")
    if not punicao.ativo:
        raise RegraViolada("Este tipo de punição está desativado.")
    return punicao


def _validar_data(cadete_id, data_cumprimento, *, ignorar_despacho=None):
    if data_cumprimento < timezone.localdate():
        raise RegraViolada("A data de cumprimento deve ser hoje ou uma data futura.")

    # Regra do sistema antigo: no máximo uma punição por cadete por dia.
    mesma_data = Despacho.objects.filter(
        anotacao__cadete_id=cadete_id,
        anotacao__status__in=STATUS_COM_PUNICAO,
        data_cumprimento=data_cumprimento,
    )
    if ignorar_despacho is not None:
        # Editar sem mudar a data não pode esbarrar no próprio despacho (bug do antigo).
        mesma_data = mesma_data.exclude(pk=ignorar_despacho.pk)
    if mesma_data.exists():
        raise RegraViolada("O cadete já tem uma punição nesta data.")


@transaction.atomic
def criar_anotacao(autor, cadete_id: int, tipo: str, motivo: str) -> Anotacao:
    exigir(autor, "anotacoes.anotar")

    motivo = motivo.strip()
    if not motivo:
        raise RegraViolada("Informe o motivo da anotação.")
    if tipo not in Tipo.values:
        raise RegraViolada("Tipo de anotação inválido.")
    if cadete_id == autor.pk:
        raise RegraViolada("Não é possível anotar a si mesmo.")
    cadete = Usuario.objects.cadetes().filter(pk=cadete_id).first()
    if cadete is None:
        raise RegraViolada("Só é possível anotar cadetes ativos.")

    return Anotacao.objects.create(autor=autor, cadete=cadete, tipo=tipo, motivo=motivo)


@transaction.atomic
def despachar(usuario, anotacao, punicao_id: int, data_cumprimento: date) -> Despacho:
    exigir(usuario, "anotacoes.despachar")
    _travar_cadete(anotacao.cadete_id)
    anotacao = _travar(anotacao)

    if anotacao.tipo != Tipo.NEGATIVA:
        raise RegraViolada("Só anotações negativas recebem punição.")
    if anotacao.status != Status.NOTIFICADA:
        raise RegraViolada("Esta anotação já foi despachada ou encerrada.")
    punicao = _punicao(punicao_id)
    _validar_data(anotacao.cadete_id, data_cumprimento)

    despacho = Despacho.objects.create(
        anotacao=anotacao,
        punicao=punicao,
        data_cumprimento=data_cumprimento,
        despachado_por=usuario,
    )
    anotacao.status = Status.DESPACHADA
    anotacao.save(update_fields=["status"])
    return despacho


@transaction.atomic
def editar_despacho(usuario, despacho, punicao_id: int, data_cumprimento: date) -> Despacho:
    exigir(usuario, "anotacoes.despachar")
    _travar_cadete(despacho.anotacao.cadete_id)
    despacho = Despacho.objects.select_for_update().select_related("anotacao").get(pk=despacho.pk)

    if despacho.anotacao.status != Status.DESPACHADA:
        raise RegraViolada("Só é possível editar despachos ainda não cumpridos nem arquivados.")
    punicao = _punicao(punicao_id)
    _validar_data(despacho.anotacao.cadete_id, data_cumprimento, ignorar_despacho=despacho)

    despacho.punicao = punicao
    despacho.data_cumprimento = data_cumprimento
    despacho.save(update_fields=["punicao", "data_cumprimento"])
    return despacho


@transaction.atomic
def compensar(usuario, positiva, negativa_id: int) -> Compensacao:
    exigir(usuario, "anotacoes.despachar")
    negativa = Anotacao.objects.select_for_update().filter(pk=negativa_id).first()
    if negativa is None:
        raise RegraViolada("Anotação negativa não encontrada.")
    positiva = _travar(positiva)

    if positiva.tipo != Tipo.POSITIVA or negativa.tipo != Tipo.NEGATIVA:
        raise RegraViolada("A compensação é de uma positiva por uma negativa.")
    if positiva.cadete_id != negativa.cadete_id:
        raise RegraViolada("A positiva e a negativa precisam ser do mesmo cadete.")
    if positiva.status != Status.NOTIFICADA or negativa.status != Status.NOTIFICADA:
        raise RegraViolada("As duas anotações precisam estar notificadas (pendentes).")

    compensacao = Compensacao.objects.create(
        positiva=positiva, negativa=negativa, feita_por=usuario
    )
    for anotacao in (positiva, negativa):
        anotacao.status = Status.COMPENSADA
        anotacao.save(update_fields=["status"])
    return compensacao


@transaction.atomic
def arquivar_positiva(usuario, positiva) -> Anotacao:
    """Positiva despachada sem compensar nada: sai da fila e fica registrada.

    No sistema antigo ela era apagada.
    """
    exigir(usuario, "anotacoes.despachar")
    positiva = _travar(positiva)

    if positiva.tipo != Tipo.POSITIVA:
        raise RegraViolada("Só anotações positivas são arquivadas sem punição.")
    if positiva.status != Status.NOTIFICADA:
        raise RegraViolada("Esta anotação já foi despachada ou encerrada.")

    positiva.status = Status.ARQUIVADA
    positiva.save(update_fields=["status"])
    return positiva


@transaction.atomic
def anular(usuario, anotacao, justificativa: str) -> Anotacao:
    exigir(usuario, "anotacoes.despachar")
    anotacao = _travar(anotacao)

    justificativa = justificativa.strip()
    if not justificativa:
        raise RegraViolada("Informe a justificativa da anulação.")
    if anotacao.status not in STATUS_ANULAVEIS:
        raise RegraViolada("Só anotações notificadas ou despachadas podem ser anuladas.")

    anotacao.status = Status.ANULADA
    anotacao.anulada_por = usuario
    anotacao.anulada_em = timezone.now()
    anotacao.motivo_anulacao = justificativa
    anotacao.save(update_fields=["status", "anulada_por", "anulada_em", "motivo_anulacao"])
    return anotacao


@transaction.atomic
def marcar_cumprida(usuario, anotacao) -> Anotacao:
    exigir(usuario, "anotacoes.despachar")
    anotacao = _travar(anotacao)

    if anotacao.status != Status.DESPACHADA:
        raise RegraViolada("Só anotações despachadas podem ser marcadas como cumpridas.")

    anotacao.status = Status.CUMPRIDA
    anotacao.save(update_fields=["status"])
    return anotacao


# Consultas


def ultima_segunda(hoje: date | None = None) -> date:
    # weekday(): segunda = 0. O sistema antigo usava (weekday() + 1) % 7 e caía no domingo.
    hoje = hoje or timezone.localdate()
    return hoje - timedelta(days=hoje.weekday())


def estatisticas_semana(hoje: date | None = None) -> dict:
    inicio = ultima_segunda(hoje)
    semana = Anotacao.objects.filter(criada_em__date__gte=inicio).exclude(status=Status.ANULADA)

    def ranking(campo):
        return [
            {
                "numerica": linha[f"{campo}__numerica"],
                "nome": linha[f"{campo}__nome"],
                "total": linha["total"],
            }
            for linha in semana.values(f"{campo}__numerica", f"{campo}__nome")
            .annotate(total=Count("id"))
            .order_by("-total", f"{campo}__nome")[:3]
        ]

    return {
        "inicio": inicio,
        "total": semana.count(),
        "por_tipo": semana.aggregate(
            positivas=Count("id", filter=Q(tipo=Tipo.POSITIVA)),
            negativas=Count("id", filter=Q(tipo=Tipo.NEGATIVA)),
        ),
        "mais_anotaram": ranking("autor"),
        "mais_anotados": ranking("cadete"),
    }
