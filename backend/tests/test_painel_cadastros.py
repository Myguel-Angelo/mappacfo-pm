"""Painel: turmas (criar, renomear, mover cadetes, formar) e tipos de punição."""

import pytest

from anotacoes.models import TipoPunicao
from contas.models import Turma, Usuario
from tests.factories import DespachoFactory, TurmaFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_admin(api):
    api.login(UsuarioFactory(grupo="Administrador").numerica)
    return api


def test_criar_e_renomear_turma(api_admin):
    criada = api_admin.post("admin/turmas", {"nome": "  CFO   IV ", "ano_ingresso": 2027}).json()

    assert criada["nome"] == "CFO IV"
    assert criada["total_cadetes"] == 0
    resp = api_admin.patch(f"admin/turmas/{criada['id']}", {"nome": "CFO 4"})
    assert resp.json()["nome"] == "CFO 4"


def test_nome_de_turma_repetido(api_admin):
    TurmaFactory(nome="CFO I")

    resp = api_admin.post("admin/turmas", {"nome": "cfo i", "ano_ingresso": 2026})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Já existe uma turma com este nome."


def test_mover_cadetes_em_lote(api_admin):
    origem, destino = TurmaFactory(), TurmaFactory()
    cadetes = [UsuarioFactory(cadete=True, turma=origem) for _ in range(3)]

    resp = api_admin.post(
        "admin/turmas/mover",
        {"cadete_ids": [c.pk for c in cadetes[:2]], "destino_id": destino.pk},
    )

    assert resp.json() == {"quantidade": 2}
    assert Usuario.objects.filter(turma=destino).count() == 2
    assert cadetes[0].history.first().turma_id == destino.pk


def test_mover_recusa_quem_nao_e_cadete_e_turma_arquivada(api_admin):
    destino = TurmaFactory()
    oficial = UsuarioFactory(oficial=True)
    arquivada = TurmaFactory(ativa=False)
    cadete = UsuarioFactory(cadete=True)

    resp = api_admin.post(
        "admin/turmas/mover", {"cadete_ids": [oficial.pk], "destino_id": destino.pk}
    )
    assert resp.json()["detail"] == "Só cadetes podem ser movidos de turma."

    resp = api_admin.post(
        "admin/turmas/mover", {"cadete_ids": [cadete.pk], "destino_id": arquivada.pk}
    )
    assert resp.json()["detail"] == "Escolha uma turma de destino ativa."


def test_formar_turma_arquiva_e_desativa_sem_apagar(api_admin):
    turma = TurmaFactory()
    cadetes = [UsuarioFactory(cadete=True, turma=turma) for _ in range(2)]
    outra = UsuarioFactory(cadete=True)

    resp = api_admin.post(f"admin/turmas/{turma.pk}/formar")

    assert resp.json() == {"quantidade": 2}
    turma.refresh_from_db()
    assert turma.ativa is False
    assert not Usuario.objects.filter(pk__in=[c.pk for c in cadetes], is_active=True).exists()
    assert Usuario.objects.get(pk=outra.pk).is_active
    assert api_admin.post(f"admin/turmas/{turma.pk}/formar").status_code == 400


def test_turma_arquivada_some_dos_filtros_mas_fica_no_painel(api_admin):
    turma = TurmaFactory(nome="CFO Antigo")
    api_admin.patch(f"admin/turmas/{turma.pk}", {"ativa": False})

    assert "CFO Antigo" not in [t["nome"] for t in api_admin.get("turmas").json()]
    assert "CFO Antigo" in [t["nome"] for t in api_admin.get("admin/turmas").json()]


def test_punicao_desativada_some_do_despacho_e_fica_nos_antigos(api_admin):
    despacho = DespachoFactory(punicao__nome="Detenção")
    punicao = despacho.punicao

    resp = api_admin.patch(f"admin/punicoes/{punicao.pk}", {"ativo": False})

    assert resp.json()["ativo"] is False
    assert resp.json()["total_despachos"] == 1
    despacho.refresh_from_db()
    assert despacho.punicao_id == punicao.pk
    assert not TipoPunicao.objects.filter(ativo=True, nome="Detenção").exists()


def test_criar_punicao_e_nome_repetido(api_admin):
    assert api_admin.post("admin/punicoes", {"nome": "Detenção"}).status_code == 201

    resp = api_admin.post("admin/punicoes", {"nome": "detenção"})

    assert resp.json()["detail"] == "Já existe um tipo de punição com este nome."


@pytest.mark.parametrize(
    ("metodo", "caminho", "corpo"),
    [
        ("get", "admin/turmas", None),
        ("post", "admin/turmas", {"nome": "X", "ano_ingresso": 2026}),
        ("patch", "admin/turmas/{turma}", {"nome": "X"}),
        ("post", "admin/turmas/mover", {"cadete_ids": [1], "destino_id": 1}),
        ("post", "admin/turmas/{turma}/formar", None),
        ("get", "admin/punicoes", None),
        ("post", "admin/punicoes", {"nome": "X"}),
        ("patch", "admin/punicoes/{punicao}", {"nome": "X"}),
    ],
)
def test_rotas_exigem_gerenciar_usuarios(api, comandante, metodo, caminho, corpo):
    turma, punicao = TurmaFactory(), TipoPunicao.objects.first()
    api.login(comandante.numerica)

    caminho = caminho.format(turma=turma.pk, punicao=punicao.pk)
    resp = api.get(caminho) if metodo == "get" else getattr(api, metodo)(caminho, corpo)

    assert resp.status_code == 403
    assert not Turma.objects.filter(nome="X").exists()
    assert not TipoPunicao.objects.filter(nome="X").exists()
