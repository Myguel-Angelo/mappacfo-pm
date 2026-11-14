"""Planilhas do painel: o modelo da importação e a lista de logins."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from administracao import importacao, planilhas
from tests.factories import TurmaFactory, UsuarioFactory
from tests.test_painel_importacao import enviar, xlsx

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_admin(api):
    api.login(UsuarioFactory(grupo="Administrador").numerica)
    return api


def abrir(conteudo: bytes):
    return load_workbook(BytesIO(conteudo))


def test_modelo_tem_as_colunas_da_importacao_e_volta_por_ela():
    planilha = abrir(planilhas.modelo_importacao())

    assert planilha.sheetnames == ["Cadetes", "Instruções", "Exemplo"]
    cadetes = planilha["Cadetes"]
    assert [c.value for c in cadetes[1]] == ["numerica", "nome", "nome_guerra", "turma", "email"]
    assert cadetes["C1"].comment.text.startswith("Obrigatório. É o login")
    assert cadetes["A1"].font.bold

    # Preenchida e salva com outra aba aberta: a importação lê a aba Cadetes, não o exemplo.
    cadetes.append(["3001", "Novo Cadete", "Novato", "CFO I", ""])
    planilha.active = planilha.sheetnames.index("Exemplo")
    saida = BytesIO()
    planilha.save(saida)
    linhas = importacao.ler_arquivo("modelo.xlsx", saida.getvalue())

    assert [(linha["numerica"], linha["nome_guerra"]) for linha in linhas] == [("3001", "Novato")]


def test_baixar_modelo(api_admin):
    resp = api_admin.get("admin/importacoes/modelo")

    assert resp.status_code == 200
    assert resp["Content-Disposition"] == 'attachment; filename="modelo-cadetes.xlsx"'
    assert abrir(resp.content).sheetnames[0] == "Cadetes"


def test_logins_da_importacao_confirmada(api_admin):
    TurmaFactory(nome="CFO I")
    planilha = xlsx(
        [
            ["numerica", "nome", "nome_guerra", "turma"],
            [1002, "Bia Lima", "Lima", "CFO I"],
            [1001, "Ana Souza", "Souza", "CFO I"],
        ]
    )
    previa = enviar(api_admin, planilha).json()
    caminho = f"admin/importacoes/{previa['id']}/logins"

    assert api_admin.get(caminho).json()["detail"] == "Esta importação ainda não foi confirmada."

    api_admin.post(f"admin/importacoes/{previa['id']}/confirmar")
    resp = api_admin.get(caminho)

    assert resp["Cache-Control"] == "private, no-store"
    linhas = list(abrir(resp.content)["Logins"].iter_rows(values_only=True))
    assert linhas == [
        ("Numérica", "Nome", "Login", "Turma"),
        ("1001", "Ana Souza", "CAD Souza", "CFO I"),
        ("1002", "Bia Lima", "CAD Lima", "CFO I"),
    ]


def test_planilhas_exigem_gerenciar_usuarios(api, comandante):
    api.login(comandante.numerica)

    assert api.get("admin/importacoes/modelo").status_code == 403
