"""Painel: importação de cadetes com prévia e confirmação."""

from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from administracao import importacao
from administracao.models import ImportacaoCadetes
from contas.models import Turma, Usuario
from core.erros import RegraViolada
from tests.conftest import ClienteApi
from tests.factories import TurmaFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return UsuarioFactory(grupo="Administrador")


@pytest.fixture
def api_admin(api, admin):
    api.login(admin.numerica)
    return api


def enviar(api, conteudo: bytes, nome="cadetes.csv", **opcoes):
    return api.client.post(
        "/api/admin/importacoes",
        {"arquivo": SimpleUploadedFile(nome, conteudo), **opcoes},
        headers={"X-CSRFToken": api.cookies["csrftoken"].value},
    )


def csv_excel(linhas: list[str]) -> bytes:
    """Como o Excel brasileiro salva: ; e cp1252."""
    return "\r\n".join(linhas).encode("cp1252")


def xlsx(linhas: list[list]) -> bytes:
    planilha = Workbook()
    for linha in linhas:
        planilha.active.append(linha)
    saida = BytesIO()
    planilha.save(saida)
    return saida.getvalue()


def test_previa_lista_cada_erro_com_a_linha_e_nao_grava(api_admin):
    TurmaFactory(nome="CFO I")
    UsuarioFactory(oficial=True, numerica="9000")
    conteudo = csv_excel(
        [
            "Numérica;Nome;Turma;E-mail",
            "1001;João Câmara;CFO I;joao@pm.ma.gov.br",
            "1001;Repetido;CFO I;",
            ";;;",
            "1002;Sem Turma;CFO X;",
            "1003;;CFO I;email-ruim",
            "9000;Oficial;CFO I;",
        ]
    )

    resp = enviar(api_admin, conteudo)

    assert resp.status_code == 201
    previa = resp.json()
    linhas = {linha["linha"]: linha for linha in previa["linhas"]}
    assert linhas[2]["acao"] == "criar"
    assert linhas[2]["nome"] == "João Câmara"  # acento certo vindo de cp1252
    assert linhas[3]["erros"] == ["Numérica repetida no arquivo (também na linha 2)."]
    assert 4 not in linhas  # linha vazia ignorada
    assert linhas[5]["erros"] == ['Turma "CFO X" não existe.']
    assert linhas[6]["erros"] == ["Nome vazio.", "E-mail inválido."]
    assert linhas[7]["erros"] == ["A numérica pertence a um usuário que não é cadete."]
    assert previa["totais"] == {"criar": 1, "atualizar": 0, "ignorar": 0, "erro": 4}
    assert not Usuario.objects.filter(numerica="1001").exists()

    confirmar = api_admin.post(f"admin/importacoes/{previa['id']}/confirmar")
    assert confirmar.status_code == 400
    assert not Usuario.objects.filter(numerica="1001").exists()


def test_confirmar_cria_os_cadetes_com_senha_que_funciona(api_admin):
    TurmaFactory(nome="CFO I")
    previa = enviar(api_admin, xlsx([["numerica", "nome", "turma"], [1001, "Ana", "CFO I"]])).json()

    resultado = api_admin.post(f"admin/importacoes/{previa['id']}/confirmar").json()

    assert resultado["atualizados"] == 0
    [criado] = resultado["criados"]
    assert criado["numerica"] == "1001"  # 1001.0 do Excel vira "1001"
    cadete = Usuario.objects.get(numerica="1001")
    assert cadete.groups.filter(name="Cadete").exists()
    assert cadete.turma.nome == "CFO I"
    assert ClienteApi().login("1001", criado["senha_temporaria"]).json()["deve_trocar_senha"]
    # A senha não fica guardada na prévia nem no resumo.
    salvo = ImportacaoCadetes.objects.get(pk=previa["id"])
    assert criado["senha_temporaria"] not in str(salvo.linhas) + str(salvo.resumo)


def test_mesma_planilha_duas_vezes_nao_duplica(api_admin):
    TurmaFactory(nome="CFO I")
    conteudo = csv_excel(["numerica;nome;turma", "1001;Ana;CFO I", "1002;Bia;CFO I"])
    primeira = enviar(api_admin, conteudo).json()
    api_admin.post(f"admin/importacoes/{primeira['id']}/confirmar")

    segunda = enviar(api_admin, conteudo, atualizar_existentes=True).json()

    assert segunda["totais"] == {"criar": 0, "atualizar": 0, "ignorar": 2, "erro": 0}
    resultado = api_admin.post(f"admin/importacoes/{segunda['id']}/confirmar").json()
    assert resultado == {"criados": [], "atualizados": 0, "ignorados": 2}
    assert Usuario.objects.filter(numerica__in=["1001", "1002"]).count() == 2


def test_atualizar_existentes_so_quando_marcado(api_admin):
    turma_nova = TurmaFactory(nome="CFO II")
    UsuarioFactory(cadete=True, numerica="1001", nome="Ana Antiga")
    conteudo = csv_excel(["numerica;nome;turma", "1001;Ana Nova;CFO II"])

    sem_opcao = enviar(api_admin, conteudo).json()
    assert sem_opcao["linhas"][0]["acao"] == "ignorar"

    com_opcao = enviar(api_admin, conteudo, atualizar_existentes=True).json()
    assert com_opcao["linhas"][0]["acao"] == "atualizar"
    assert "nome: Ana Antiga → Ana Nova" in com_opcao["linhas"][0]["mudancas"]
    api_admin.post(f"admin/importacoes/{com_opcao['id']}/confirmar")
    cadete = Usuario.objects.get(numerica="1001")
    assert (cadete.nome, cadete.turma) == ("Ana Nova", turma_nova)


def test_criar_turmas_quando_marcado(api_admin):
    previa = enviar(
        api_admin, csv_excel(["numerica,nome,turma", "1001,Ana,CFO V"]), criar_turmas=True
    ).json()

    assert previa["linhas"][0]["acao"] == "criar"
    api_admin.post(f"admin/importacoes/{previa['id']}/confirmar")
    assert Turma.objects.filter(nome="CFO V").exists()


def test_previa_expirada(api_admin):
    TurmaFactory(nome="CFO I")
    previa = enviar(api_admin, csv_excel(["numerica;nome;turma", "1001;Ana;CFO I"])).json()
    ImportacaoCadetes.objects.filter(pk=previa["id"]).update(
        criada_em=ImportacaoCadetes.objects.get(pk=previa["id"]).criada_em - timedelta(minutes=31)
    )

    resp = api_admin.post(f"admin/importacoes/{previa['id']}/confirmar")

    assert resp.json()["detail"] == "A prévia expirou (30 minutos). Envie a planilha de novo."


def test_nao_confirma_duas_vezes(api_admin):
    TurmaFactory(nome="CFO I")
    previa = enviar(api_admin, csv_excel(["numerica;nome;turma", "1001;Ana;CFO I"])).json()
    api_admin.post(f"admin/importacoes/{previa['id']}/confirmar")

    resp = api_admin.post(f"admin/importacoes/{previa['id']}/confirmar")

    assert resp.json()["detail"] == "Esta importação já foi confirmada."


def test_falha_no_meio_desfaz_tudo(admin, monkeypatch):
    TurmaFactory(nome="CFO I")
    linhas = importacao.ler_arquivo(
        "x.csv", csv_excel(["numerica;nome;turma", "1001;Ana;CFO I", "1002;Bia;CFO I"])
    )
    previa = ImportacaoCadetes.objects.create(
        criada_por=admin,
        nome_arquivo="x.csv",
        linhas=importacao.analisar(linhas, atualizar_existentes=False, criar_turmas=False),
    )
    original = Usuario.objects.create_user
    chamadas = []

    def falhar_na_segunda(*args, **kwargs):
        chamadas.append(1)
        if len(chamadas) == 2:
            raise RuntimeError("falha simulada")
        return original(*args, **kwargs)

    monkeypatch.setattr(Usuario.objects, "create_user", falhar_na_segunda)

    with pytest.raises(RuntimeError):
        importacao.confirmar(admin, previa)

    assert not Usuario.objects.filter(numerica__in=["1001", "1002"]).exists()
    previa.refresh_from_db()
    assert previa.confirmada_em is None


def test_banco_mudou_entre_previa_e_confirmacao(api_admin):
    TurmaFactory(nome="CFO I")
    previa = enviar(api_admin, csv_excel(["numerica;nome;turma", "1001;Ana;CFO I"])).json()
    UsuarioFactory(oficial=True, numerica="1001")  # alguém cadastrou um oficial com a numérica

    resp = api_admin.post(f"admin/importacoes/{previa['id']}/confirmar")

    assert resp.status_code == 400
    assert not Usuario.objects.filter(numerica="1001", groups__name="Cadete").exists()


@pytest.mark.parametrize(
    ("conteudo", "mensagem"),
    [
        (b"", "A planilha está vazia."),
        (b"nome;turma\nAna;CFO I", "A planilha precisa das colunas numerica, nome e turma."),
        (b"numerica;nome;turma\n", "A planilha não tem nenhum cadete."),
        (b"PK\x03\x04lixo", "Não foi possível ler a planilha. Envie um .xlsx ou .csv."),
    ],
)
def test_arquivos_invalidos(conteudo, mensagem):
    with pytest.raises(RegraViolada, match=mensagem.replace(".", r"\.")):
        importacao.ler_arquivo("x.csv", conteudo)


def test_importacao_exige_gerenciar_usuarios(api, comandante):
    api.login(comandante.numerica)

    resp = enviar(api, csv_excel(["numerica;nome;turma", "1001;Ana;CFO I"]))

    assert resp.status_code == 403
    assert not ImportacaoCadetes.objects.exists()
