"""Rotas de mappa: quem gera, quem vê, publicação e download só com sessão."""

import pytest

from anotacoes.models import Anotacao
from mappas import services
from tests.factories import DespachoFactory, UsuarioFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("armazenamento")]


@pytest.fixture
def mappa(comandante):
    DespachoFactory()
    return services.gerar_mappa(comandante, "MAPA N°014/2026")


def test_comandante_gera_e_recebe_o_resumo(api, comandante):
    DespachoFactory()
    DespachoFactory()
    api.login(comandante.numerica)

    resp = api.post("mappas", {"titulo": "Mappa da semana"})

    assert resp.status_code == 201
    dados = resp.json()
    assert dados["titulo"] == "Mappa da semana"
    assert dados["total_anotacoes"] == 2
    assert dados["publicado"] is False
    assert dados["gerado_por"]["numerica"] == comandante.numerica
    assert api.get("anotacoes?status=despachada").json()["count"] == 0
    assert api.get("anotacoes?status=arquivada").json()["count"] == 2


def test_gerar_sem_despachadas_e_400(api, comandante):
    api.login(comandante.numerica)

    resp = api.post("mappas", {"titulo": "Vazio"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Não há anotações despachadas para exportar."


@pytest.mark.parametrize("perfil", ["cadete", "oficial"])
def test_so_quem_exporta_gera_e_publica(api, mappa, perfil):
    ator = UsuarioFactory(**{perfil: True})
    api.login(ator.numerica)

    assert api.post("mappas", {"titulo": "X"}).status_code == 403
    # O mappa não publicado nem aparece para quem não exporta.
    assert api.patch(f"mappas/{mappa.pk}", {"publicado": True}).status_code == 404


def test_publicar_exige_permissao_mesmo_se_o_mappa_e_visivel(api, mappa, oficial):
    services.publicar(mappa.gerado_por, mappa, True)
    api.login(oficial.numerica)

    assert api.patch(f"mappas/{mappa.pk}", {"publicado": False}).status_code == 403


def test_cadete_lista_so_os_publicados(api, comandante, cadete):
    DespachoFactory()
    publicado = services.gerar_mappa(comandante, "Publicado")
    services.publicar(comandante, publicado, True)
    DespachoFactory()
    services.gerar_mappa(comandante, "Rascunho")
    api.login(cadete.numerica)

    assert [m["titulo"] for m in api.get("mappas").json()] == ["Publicado"]


def test_comandante_publica_e_despublica(api, mappa, comandante):
    api.login(comandante.numerica)

    assert api.patch(f"mappas/{mappa.pk}", {"publicado": True}).json()["publicado"] is True
    assert api.patch(f"mappas/{mappa.pk}", {"publicado": False}).json()["publicado"] is False


def test_download_anonimo_e_401(api, mappa):
    services.publicar(mappa.gerado_por, mappa, True)

    assert api.get(f"mappas/{mappa.pk}/download").status_code == 401


def test_cadete_nao_baixa_mappa_nao_publicado(api, mappa, cadete):
    api.login(cadete.numerica)

    assert api.get(f"mappas/{mappa.pk}/download").status_code == 404


def test_cadete_baixa_o_publicado_com_nome_seguro(api, mappa, cadete):
    services.publicar(mappa.gerado_por, mappa, True)
    api.login(cadete.numerica)

    resp = api.get(f"mappas/{mappa.pk}/download")

    assert resp.status_code == 200
    assert resp["Content-Disposition"] == 'attachment; filename="mapa-n014-2026.xlsx"'
    assert resp["Cache-Control"] == "private, no-store"
    assert b"".join(resp.streaming_content)[:2] == b"PK"  # xlsx é um zip


def test_arquivo_sumido_do_disco_e_404(api, mappa, comandante):
    mappa.arquivo.storage.delete(mappa.arquivo.name)
    api.login(comandante.numerica)

    assert api.get(f"mappas/{mappa.pk}/download").status_code == 404


def test_troca_de_senha_pendente_bloqueia_o_download(api, mappa):
    services.publicar(mappa.gerado_por, mappa, True)
    cadete = UsuarioFactory(cadete=True, deve_trocar_senha=True)
    api.login(cadete.numerica)

    resp = api.get(f"mappas/{mappa.pk}/download")

    assert resp.status_code == 403
    assert resp.json()["codigo"] == "troca_senha_pendente"


def test_nao_existe_rota_de_apagar(api, mappa, comandante):
    api.login(comandante.numerica)
    api.csrf()

    resp = api.client.delete(
        f"/api/mappas/{mappa.pk}", headers={"X-CSRFToken": api.cookies["csrftoken"].value}
    )

    assert resp.status_code == 405
    assert Anotacao.objects.filter(status=Anotacao.Status.ARQUIVADA).count() == 1


def test_storage_privado_nao_gera_url(mappa):
    with pytest.raises(ValueError):
        mappa.arquivo.url  # noqa: B018
