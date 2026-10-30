from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Status
from ninja.pagination import PageNumberPagination, paginate

from anotacoes import services
from anotacoes.models import Anotacao, TipoPunicao
from anotacoes.schemas import (
    AnotacaoFiltros,
    AnotacaoIn,
    AnotacaoOut,
    AnularIn,
    CadeteOut,
    CompensarIn,
    DespachoIn,
    EstatisticasOut,
    PunicaoOut,
    TurmaOut,
)
from contas.models import Turma
from core.permissoes import exigir
from core.schemas import ErroOut

Usuario = get_user_model()

router = Router(tags=["anotações"])

ERROS = {400: ErroOut, 403: ErroOut, 404: ErroOut}


def anotacoes_visiveis(usuario):
    """Anotações que o usuário pode ver. Toda rota que recebe um id busca aqui dentro:
    um cadete nunca carrega a anotação de outro, nem adivinhando o id (404)."""
    qs = Anotacao.objects.select_related(
        "cadete__turma",
        "autor",
        "despacho__punicao",
        "despacho__despachado_por",
        "compensa",
        "compensada_por",
    )
    if usuario.has_perm("anotacoes.ver_anotacoes"):
        return qs
    return qs.filter(Q(cadete=usuario) | Q(autor=usuario))


def _anotacao(request, anotacao_id):
    return get_object_or_404(anotacoes_visiveis(request.user), pk=anotacao_id)


def _recarregar(request, anotacao):
    return anotacoes_visiveis(request.user).get(pk=anotacao.pk)


# Consultas de apoio


@router.get("/turmas", response=list[TurmaOut])
def listar_turmas(request):
    return Turma.objects.filter(ativa=True)


@router.get("/cadetes", response={200: list[CadeteOut], 403: ErroOut})
def listar_cadetes(request, turma_id: int | None = None):
    exigir(request.user, "anotacoes.anotar")
    cadetes = Usuario.objects.cadetes().select_related("turma").order_by("turma__nome", "numerica")
    if turma_id is not None:
        cadetes = cadetes.filter(turma_id=turma_id)
    return cadetes


@router.get("/punicoes", response={200: list[PunicaoOut], 403: ErroOut})
def listar_punicoes(request):
    exigir(request.user, "anotacoes.despachar")
    return TipoPunicao.objects.filter(ativo=True)


@router.get("/estatisticas/semana", response={200: EstatisticasOut, 403: ErroOut})
def estatisticas_semana(request):
    # No sistema antigo o bloco de estatísticas só aparecia para o Oficial Comandante.
    exigir(request.user, "anotacoes.despachar")
    return services.estatisticas_semana()


# Anotações


@router.get("/anotacoes/minhas", response=list[AnotacaoOut])
def minhas_anotacoes(request):
    return (
        anotacoes_visiveis(request.user)
        .filter(cadete=request.user)
        .exclude(status=Anotacao.Status.ANULADA)
        .order_by("-criada_em")
    )


@router.get("/anotacoes", response={200: list[AnotacaoOut], 403: ErroOut})
@paginate(PageNumberPagination, page_size=50)
def listar_anotacoes(request, filtros: Query[AnotacaoFiltros]):
    exigir(request.user, "anotacoes.ver_anotacoes")
    qs = anotacoes_visiveis(request.user)
    if filtros.turma_id is not None:
        qs = qs.filter(cadete__turma_id=filtros.turma_id)
    if filtros.cadete_id is not None:
        qs = qs.filter(cadete_id=filtros.cadete_id)
    if filtros.status is not None:
        qs = qs.filter(status=filtros.status)
    if filtros.tipo is not None:
        qs = qs.filter(tipo=filtros.tipo)
    # Ordem da fila do comandante no sistema antigo: positivas primeiro, por turma e numérica.
    return qs.order_by("-tipo", "cadete__turma__nome", "cadete__numerica", "criada_em")


@router.get("/anotacoes/{anotacao_id}", response={200: AnotacaoOut, 404: ErroOut})
def detalhar_anotacao(request, anotacao_id: int):
    return _anotacao(request, anotacao_id)


@router.post("/anotacoes", response={201: AnotacaoOut, **ERROS})
def criar_anotacao(request, dados: AnotacaoIn):
    anotacao = services.criar_anotacao(request.user, dados.cadete_id, dados.tipo, dados.motivo)
    return Status(201, _recarregar(request, anotacao))


@router.post("/anotacoes/{anotacao_id}/despacho", response={200: AnotacaoOut, **ERROS})
def despachar(request, anotacao_id: int, dados: DespachoIn):
    anotacao = _anotacao(request, anotacao_id)
    services.despachar(request.user, anotacao, dados.punicao_id, dados.data_cumprimento)
    return _recarregar(request, anotacao)


@router.put("/anotacoes/{anotacao_id}/despacho", response={200: AnotacaoOut, **ERROS})
def editar_despacho(request, anotacao_id: int, dados: DespachoIn):
    anotacao = _anotacao(request, anotacao_id)
    exigir(request.user, "anotacoes.despachar")
    despacho = getattr(anotacao, "despacho", None)
    if despacho is None:
        return Status(404, {"detail": "Esta anotação não tem despacho."})
    services.editar_despacho(request.user, despacho, dados.punicao_id, dados.data_cumprimento)
    return _recarregar(request, anotacao)


@router.post("/anotacoes/{anotacao_id}/compensar", response={200: AnotacaoOut, **ERROS})
def compensar(request, anotacao_id: int, dados: CompensarIn):
    positiva = _anotacao(request, anotacao_id)
    services.compensar(request.user, positiva, dados.negativa_id)
    return _recarregar(request, positiva)


@router.post("/anotacoes/{anotacao_id}/arquivar", response={200: AnotacaoOut, **ERROS})
def arquivar_positiva(request, anotacao_id: int):
    positiva = _anotacao(request, anotacao_id)
    services.arquivar_positiva(request.user, positiva)
    return _recarregar(request, positiva)


@router.post("/anotacoes/{anotacao_id}/anular", response={200: AnotacaoOut, **ERROS})
def anular(request, anotacao_id: int, dados: AnularIn):
    anotacao = _anotacao(request, anotacao_id)
    services.anular(request.user, anotacao, dados.justificativa)
    return _recarregar(request, anotacao)


@router.post("/anotacoes/{anotacao_id}/cumprida", response={200: AnotacaoOut, **ERROS})
def marcar_cumprida(request, anotacao_id: int):
    anotacao = _anotacao(request, anotacao_id)
    services.marcar_cumprida(request.user, anotacao)
    return _recarregar(request, anotacao)
