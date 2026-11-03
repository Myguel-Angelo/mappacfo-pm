"""Exportação e publicação do mappa. Nenhuma anotação é apagada (o antigo apagava)."""

import re

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from anotacoes.models import Anotacao
from core.erros import RegraViolada
from core.permissoes import exigir
from mappas.models import Mappa
from mappas.planilha import montar_planilha

Status = Anotacao.Status


def nome_download(titulo: str) -> str:
    """Nome do arquivo baixado, derivado do título: sem barras, acentos ou "..".

    "MAPA N°014/2026" → "mapa-n014-2026.xlsx".
    """
    nome = slugify(re.sub(r"[/\\.]+", " ", titulo))
    return f"{nome or 'mappa'}.xlsx"


@transaction.atomic
def gerar_mappa(usuario, titulo: str) -> Mappa:
    exigir(usuario, "anotacoes.exportar")

    titulo = titulo.strip()
    if not titulo:
        raise RegraViolada("Informe o título do mappa.")

    # Trava as despachadas: duas exportações ao mesmo tempo não levam as mesmas anotações;
    # a segunda espera e encontra a lista vazia. of=("self",) porque a turma é um join
    # opcional, que o Postgres não deixa travar.
    anotacoes = list(
        Anotacao.objects.select_for_update(of=("self",))
        .filter(status=Status.DESPACHADA)
        .select_related("cadete__turma", "autor", "despacho__punicao")
        .prefetch_related("autor__groups")
        .order_by("cadete__turma__nome", "cadete__numerica", "despacho__data_cumprimento")
    )
    if not anotacoes:
        raise RegraViolada("Não há anotações despachadas para exportar.")

    mappa = Mappa(titulo=titulo, gerado_por=usuario)
    mappa.arquivo.save("mappa.xlsx", ContentFile(montar_planilha(anotacoes)), save=False)
    try:
        mappa.save()
        mappa.anotacoes.set(anotacoes)
        # save() um a um (e não update()) para cada anotação ganhar sua linha no histórico.
        for anotacao in anotacoes:
            anotacao.status = Status.ARQUIVADA
            anotacao.save(update_fields=["status"])
    except Exception:
        # O banco desfaz tudo no rollback, mas o arquivo já está no disco: apaga para não
        # deixar órfão.
        mappa.arquivo.delete(save=False)
        raise
    return mappa


@transaction.atomic
def publicar(usuario, mappa, publicado: bool) -> Mappa:
    exigir(usuario, "anotacoes.exportar")
    mappa = Mappa.objects.select_for_update().get(pk=mappa.pk)
    mappa.publicado = publicado
    mappa.save(update_fields=["publicado"])
    return mappa
