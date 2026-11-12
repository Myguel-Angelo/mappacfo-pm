"""Painel: linha do tempo da auditoria, acessos e bloqueios de login."""

from datetime import timedelta

import pytest
from axes.models import AccessAttempt
from django.utils import timezone

from tests.conftest import ClienteApi
from tests.factories import AnotacaoFactory, TipoPunicaoFactory, TurmaFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return UsuarioFactory(grupo="Administrador")


@pytest.fixture
def api_admin(api, admin):
    api.login(admin.numerica)
    return api


def _como(usuario):
    cliente = ClienteApi()
    cliente.login(usuario.numerica)
    return cliente


def test_despacho_aparece_com_o_autor_e_a_mudanca_de_status(api_admin, comandante):
    anotacao = AnotacaoFactory()
    punicao = TipoPunicaoFactory(nome="Pernoite")
    amanha = (timezone.localdate() + timedelta(days=1)).isoformat()
    _como(comandante).post(
        f"anotacoes/{anotacao.pk}/despacho",
        {"punicao_id": punicao.pk, "data_cumprimento": amanha},
    )

    itens = api_admin.get("admin/auditoria").json()["items"]

    despacho = next(i for i in itens if i["tipo"] == "despacho")
    assert despacho["acao"] == "criou"
    assert despacho["usuario"]["numerica"] == comandante.numerica
    assert despacho["descricao"] == f"Despacho da anotação #{anotacao.pk}"
    alteracao = next(i for i in itens if i["tipo"] == "anotacao" and i["acao"] == "alterou")
    assert alteracao["usuario"]["numerica"] == comandante.numerica
    assert alteracao["mudancas"] == [{"campo": "status", "de": "Notificada", "para": "Despachada"}]


def test_mudanca_de_grupo_e_turma_mostra_nomes(api_admin):
    turma_a, turma_b = TurmaFactory(nome="CFO A"), TurmaFactory(nome="CFO B")
    cadete = UsuarioFactory(cadete=True, turma=turma_a)

    api_admin.patch(
        f"admin/usuarios/{cadete.pk}", {"turma_id": turma_b.pk, "grupos": ["Cadete", "Oficial"]}
    )

    itens = api_admin.get("admin/auditoria?tipo=usuario").json()["items"]
    do_cadete = [i for i in itens if i["registro_id"] == cadete.pk]
    mudancas = {}
    for item in do_cadete:  # mais recente primeiro: fica a última mudança de cada campo
        for mudanca in item["mudancas"]:
            mudancas.setdefault(mudanca["campo"], mudanca)
    assert mudancas["turma"]["de"] == "CFO A"
    assert mudancas["turma"]["para"] == "CFO B"
    assert mudancas["grupos"]["para"] == "Cadete, Oficial"


def test_filtros_por_tipo_usuario_e_periodo(api_admin, admin, comandante):
    AnotacaoFactory()  # criada fora de requisição: sem autor
    _como(comandante).post("mappas", {"titulo": "X"})  # falha (sem despachadas): nada gravado
    TurmaFactory()

    so_anotacoes = api_admin.get("admin/auditoria?tipo=anotacao").json()
    assert {i["tipo"] for i in so_anotacoes["items"]} == {"anotacao"}
    assert so_anotacoes["items"][0]["usuario"] is None

    ontem = (timezone.localdate() - timedelta(days=1)).isoformat()
    assert api_admin.get(f"admin/auditoria?fim={ontem}").json()["count"] == 0

    por_admin = api_admin.get(f"admin/auditoria?usuario_id={admin.pk}").json()
    assert por_admin["count"] == 0


def test_paginacao_intercala_as_fontes_mais_recentes_primeiro(api_admin):
    for _ in range(15):
        AnotacaoFactory()
        TurmaFactory()

    primeira = api_admin.get("admin/auditoria").json()
    segunda = api_admin.get("admin/auditoria?page=2").json()

    assert primeira["count"] == segunda["count"] >= 30
    assert len(primeira["items"]) == 20
    datas = [i["quando"] for i in primeira["items"] + segunda["items"]]
    assert datas == sorted(datas, reverse=True)
    ids = [i["id"] for i in primeira["items"] + segunda["items"]]
    assert len(ids) == len(set(ids))

    assert len(api_admin.get("admin/auditoria?page_size=7").json()["items"]) == 7


def test_acessos_e_bloqueios(api_admin, admin):
    alvo = UsuarioFactory()
    for _ in range(5):
        ClienteApi().login(alvo.numerica, "errada")

    bloqueios = api_admin.get("admin/bloqueios").json()
    assert bloqueios[0]["numerica"] == alvo.numerica
    assert bloqueios[0]["bloqueado"] is True

    acessos = api_admin.get(f"admin/acessos?numerica={admin.numerica}").json()
    assert acessos["count"] >= 1

    assert api_admin.post(f"admin/bloqueios/{alvo.numerica}/liberar").json()["quantidade"] >= 1
    assert not AccessAttempt.objects.filter(username=alvo.numerica).exists()
    assert ClienteApi().login(alvo.numerica).status_code == 200


@pytest.mark.parametrize("caminho", ["admin/auditoria", "admin/acessos", "admin/bloqueios"])
def test_auditoria_exige_gerenciar_usuarios(api, comandante, caminho):
    api.login(comandante.numerica)

    assert api.get(caminho).status_code == 403
