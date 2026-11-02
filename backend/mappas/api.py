from django.db.models import Count
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from core.schemas import ErroOut
from mappas import services
from mappas.models import Mappa
from mappas.schemas import MappaIn, MappaOut, PublicacaoIn

router = Router(tags=["mappas"])

ERROS = {400: ErroOut, 403: ErroOut, 404: ErroOut}


def mappas_visiveis(usuario):
    """Quem exporta vê todos; os demais, só os publicados. Toda rota com id busca aqui:
    o cadete recebe 404 num mappa não publicado, sem saber que ele existe."""
    qs = Mappa.objects.select_related("gerado_por").annotate(total_anotacoes=Count("anotacoes"))
    if usuario.has_perm("anotacoes.exportar"):
        return qs
    return qs.filter(publicado=True)


def _mappa(request, mappa_id):
    return get_object_or_404(mappas_visiveis(request.user), pk=mappa_id)


@router.get("", response=list[MappaOut])
def listar_mappas(request):
    return mappas_visiveis(request.user)


@router.post("", response={201: MappaOut, **ERROS})
def gerar_mappa(request, dados: MappaIn):
    mappa = services.gerar_mappa(request.user, dados.titulo)
    return Status(201, _mappa(request, mappa.pk))


@router.patch("/{mappa_id}", response={200: MappaOut, **ERROS})
def publicar_mappa(request, mappa_id: int, dados: PublicacaoIn):
    mappa = _mappa(request, mappa_id)
    services.publicar(request.user, mappa, dados.publicado)
    return _mappa(request, mappa_id)


@router.get("/{mappa_id}/download", response={404: ErroOut})
def baixar_mappa(request, mappa_id: int):
    mappa = _mappa(request, mappa_id)
    try:
        arquivo = mappa.arquivo.open("rb")
    except FileNotFoundError:
        return Status(404, {"detail": "O arquivo deste mappa não foi encontrado."})
    resposta = FileResponse(
        arquivo, as_attachment=True, filename=services.nome_download(mappa.titulo)
    )
    # Arquivo com dados pessoais: nenhum cache compartilhado (proxy) guarda a resposta.
    resposta["Cache-Control"] = "private, no-store"
    return resposta
