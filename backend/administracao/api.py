from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Status
from ninja.pagination import PageNumberPagination, paginate

from administracao import usuarios
from administracao.schemas import (
    AdminSenhaOut,
    AdminUsuarioCriadoOut,
    AdminUsuarioCriarIn,
    AdminUsuarioEditarIn,
    AdminUsuarioFiltros,
    AdminUsuarioOut,
)
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
