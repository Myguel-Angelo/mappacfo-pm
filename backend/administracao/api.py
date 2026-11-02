from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from ninja import File, Form, Query, Router, Status
from ninja.files import UploadedFile
from ninja.pagination import PageNumberPagination, paginate

from administracao import cadastros, importacao, usuarios
from administracao.models import ImportacaoCadetes
from administracao.schemas import (
    AdminImportacaoOpcoesIn,
    AdminImportacaoOut,
    AdminMoverIn,
    AdminPunicaoEditarIn,
    AdminPunicaoIn,
    AdminPunicaoOut,
    AdminQuantidadeOut,
    AdminResultadoImportacaoOut,
    AdminSenhaOut,
    AdminTurmaEditarIn,
    AdminTurmaIn,
    AdminTurmaOut,
    AdminUsuarioCriadoOut,
    AdminUsuarioCriarIn,
    AdminUsuarioEditarIn,
    AdminUsuarioFiltros,
    AdminUsuarioOut,
)
from anotacoes.models import TipoPunicao
from contas.models import Turma
from core.permissoes import exigir
from core.schemas import ErroOut

Usuario = get_user_model()

# Toda rota daqui exige contas.gerenciar_usuarios (leitura inclusive).
router = Router(tags=["administração"])

ERROS = {400: ErroOut, 403: ErroOut, 404: ErroOut}


def _admin(request):
    exigir(request.user, usuarios.PERMISSAO)


# Usuários


def _usuarios():
    return Usuario.objects.select_related("turma").prefetch_related(
        "groups",
        Prefetch(
            "user_permissions",
            queryset=Permission.objects.filter(
                content_type__app_label="anotacoes", codename="anotar"
            ),
            to_attr="perm_anotar",
        ),
    )


def _usuario(usuario_id):
    return get_object_or_404(_usuarios(), pk=usuario_id)


@router.get("/usuarios", response={200: list[AdminUsuarioOut], 403: ErroOut})
@paginate(PageNumberPagination, page_size=50)
def listar_usuarios(request, filtros: Query[AdminUsuarioFiltros]):
    _admin(request)
    qs = _usuarios()
    if filtros.busca:
        termo = filtros.busca.strip()
        qs = qs.filter(Q(nome__unaccent__icontains=termo) | Q(numerica__icontains=termo))
    if filtros.grupo:
        qs = qs.filter(groups__name=filtros.grupo)
    if filtros.turma_id is not None:
        qs = qs.filter(turma_id=filtros.turma_id)
    if filtros.ativo is not None:
        qs = qs.filter(is_active=filtros.ativo)
    return qs.order_by("-is_active", "nome")


@router.post("/usuarios", response={201: AdminUsuarioCriadoOut, **ERROS})
def criar_usuario(request, dados: AdminUsuarioCriarIn):
    usuario, senha = usuarios.criar_usuario(request.user, **dados.dict())
    return Status(201, {"usuario": _usuario(usuario.pk), "senha_temporaria": senha})


@router.patch("/usuarios/{usuario_id}", response={200: AdminUsuarioOut, **ERROS})
def editar_usuario(request, usuario_id: int, dados: AdminUsuarioEditarIn):
    _admin(request)
    usuario = _usuario(usuario_id)
    usuarios.editar_usuario(request.user, usuario, **dados.dict(exclude_unset=True))
    return _usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/desativar", response={200: AdminUsuarioOut, **ERROS})
def desativar_usuario(request, usuario_id: int):
    _admin(request)
    usuarios.definir_ativo(request.user, _usuario(usuario_id), False)
    return _usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/reativar", response={200: AdminUsuarioOut, **ERROS})
def reativar_usuario(request, usuario_id: int):
    _admin(request)
    usuarios.definir_ativo(request.user, _usuario(usuario_id), True)
    return _usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/resetar-senha", response={200: AdminSenhaOut, **ERROS})
def resetar_senha(request, usuario_id: int):
    _admin(request)
    return {"senha_temporaria": usuarios.resetar_senha(request.user, _usuario(usuario_id))}


# Turmas


def _turmas():
    return Turma.objects.annotate(
        total_cadetes=Count("usuarios", filter=Q(usuarios__is_active=True))
    ).order_by("-ativa", "-ano_ingresso", "nome")


def _turma(turma_id):
    return get_object_or_404(_turmas(), pk=turma_id)


@router.get("/turmas", response={200: list[AdminTurmaOut], 403: ErroOut})
def listar_turmas(request):
    _admin(request)
    return _turmas()


@router.post("/turmas", response={201: AdminTurmaOut, **ERROS})
def criar_turma(request, dados: AdminTurmaIn):
    turma = cadastros.criar_turma(request.user, dados.nome, dados.ano_ingresso)
    return Status(201, _turma(turma.pk))


@router.post("/turmas/mover", response={200: AdminQuantidadeOut, **ERROS})
def mover_cadetes(request, dados: AdminMoverIn):
    quantidade = cadastros.mover_cadetes(request.user, dados.cadete_ids, dados.destino_id)
    return {"quantidade": quantidade}


@router.patch("/turmas/{turma_id}", response={200: AdminTurmaOut, **ERROS})
def editar_turma(request, turma_id: int, dados: AdminTurmaEditarIn):
    _admin(request)
    cadastros.editar_turma(request.user, _turma(turma_id), **dados.dict(exclude_unset=True))
    return _turma(turma_id)


@router.post("/turmas/{turma_id}/formar", response={200: AdminQuantidadeOut, **ERROS})
def formar_turma(request, turma_id: int):
    _admin(request)
    return {"quantidade": cadastros.formar_turma(request.user, _turma(turma_id))}


# Tipos de punição


def _punicoes():
    return TipoPunicao.objects.annotate(total_despachos=Count("despachos")).order_by(
        "-ativo", "nome"
    )


def _punicao(punicao_id):
    return get_object_or_404(_punicoes(), pk=punicao_id)


@router.get("/punicoes", response={200: list[AdminPunicaoOut], 403: ErroOut})
def listar_punicoes(request):
    _admin(request)
    return _punicoes()


@router.post("/punicoes", response={201: AdminPunicaoOut, **ERROS})
def criar_punicao(request, dados: AdminPunicaoIn):
    punicao = cadastros.criar_punicao(request.user, dados.nome)
    return Status(201, _punicao(punicao.pk))


@router.patch("/punicoes/{punicao_id}", response={200: AdminPunicaoOut, **ERROS})
def editar_punicao(request, punicao_id: int, dados: AdminPunicaoEditarIn):
    _admin(request)
    cadastros.editar_punicao(request.user, _punicao(punicao_id), **dados.dict(exclude_unset=True))
    return _punicao(punicao_id)


# Importação de cadetes


@router.post("/importacoes", response={201: AdminImportacaoOut, **ERROS})
def criar_previa(request, opcoes: Form[AdminImportacaoOpcoesIn], arquivo: File[UploadedFile]):
    previa = importacao.criar_previa(
        request.user,
        arquivo.name or "planilha",
        arquivo.read(importacao.TAMANHO_MAXIMO + 1),
        atualizar_existentes=opcoes.atualizar_existentes,
        criar_turmas=opcoes.criar_turmas,
    )
    return Status(201, previa)


@router.post(
    "/importacoes/{importacao_id}/confirmar",
    response={200: AdminResultadoImportacaoOut, **ERROS},
)
def confirmar_importacao(request, importacao_id: UUID):
    _admin(request)
    previa = get_object_or_404(ImportacaoCadetes, pk=importacao_id)
    return importacao.confirmar(request.user, previa)
