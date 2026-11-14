"""Painel: gestão de usuários, senha temporária, sessões e o último administrador."""

import pytest
from axes.models import AccessAttempt

from administracao import usuarios
from contas.models import Usuario
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


def test_senha_temporaria_tem_formato_legivel():
    senha = usuarios.gerar_senha_temporaria()

    assert len(senha) == 14
    assert senha.count("-") == 2
    assert not set(senha) & set("0o1li")


def test_criar_usuario_devolve_a_senha_uma_vez_e_pede_troca(api_admin):
    turma = TurmaFactory()

    resp = api_admin.post(
        "admin/usuarios",
        {
            "numerica": "4001",
            "nome": "Novo Cadete",
            "nome_guerra": "CAD Novato",
            "turma_id": turma.pk,
            "grupos": ["Cadete"],
        },
    )

    assert resp.status_code == 201
    dados = resp.json()
    senha = dados["senha_temporaria"]
    assert dados["usuario"]["grupos"] == ["Cadete"]
    # O CAD da entrada é só do login: guarda-se o nome de guerra puro.
    assert dados["usuario"]["nome_guerra"] == "Novato"
    assert dados["usuario"]["login"] == "CAD Novato"
    assert dados["usuario"]["deve_trocar_senha"] is True
    # A senha não volta em nenhuma outra resposta.
    assert senha not in api_admin.get("admin/usuarios").content.decode()

    novo = ClienteApi()
    assert novo.login("4001", senha).json()["deve_trocar_senha"] is True
    assert novo.get("anotacoes/minhas").json()["codigo"] == "troca_senha_pendente"


@pytest.mark.parametrize(
    ("dados", "mensagem"),
    [
        (
            {"numerica": "4002", "nome": "X", "nome_guerra": "X", "grupos": ["Cadete"]},
            "Cadete precisa de uma turma.",
        ),
        (
            {"numerica": "4002", "nome": "X", "nome_guerra": "X", "grupos": ["Chefe"]},
            "Grupo inválido: Chefe.",
        ),
        (
            {"numerica": "4002", "nome": "X", "nome_guerra": "X", "email": "nao-e-email"},
            "E-mail inválido.",
        ),
    ],
)
def test_criar_valida_os_dados(api_admin, dados, mensagem):
    resp = api_admin.post("admin/usuarios", dados)

    assert resp.status_code == 400
    assert resp.json()["detail"] == mensagem
    assert not Usuario.objects.filter(numerica="4002").exists()


def test_numerica_repetida_e_recusada(api_admin):
    UsuarioFactory(numerica="ABC1")

    resp = api_admin.post(
        "admin/usuarios", {"numerica": "abc1", "nome": "Outro", "nome_guerra": "Outro"}
    )

    assert resp.json()["detail"] == "Já existe um usuário com esta numérica."


def test_nome_de_guerra_repetido_e_recusado_mesmo_com_acento_e_caixa(api_admin):
    UsuarioFactory(nome_guerra="Ten. Cássio")
    cadete = UsuarioFactory(cadete=True, nome_guerra="Bruno")

    resp = api_admin.post(
        "admin/usuarios", {"numerica": "5001", "nome": "Outro", "nome_guerra": "ten cassio"}
    )
    assert resp.json()["detail"] == 'Já existe um usuário com o nome de guerra "ten cassio".'

    resp = api_admin.patch(f"admin/usuarios/{cadete.pk}", {"nome_guerra": "TEN CASSIO"})
    assert resp.status_code == 400
    # Manter o próprio nome (mudando só a caixa) não é repetição.
    resp = api_admin.patch(f"admin/usuarios/{cadete.pk}", {"nome_guerra": "BRUNO"})
    assert resp.json()["login"] == "CAD BRUNO"


def test_busca_acha_pelo_nome_de_guerra(api_admin):
    UsuarioFactory(cadete=True, nome="Bruno Henrique Souza", nome_guerra="Henrique")
    UsuarioFactory(cadete=True, nome="Outra Pessoa", nome_guerra="Outra")

    itens = api_admin.get("admin/usuarios?busca=henrique").json()["items"]

    assert [u["nome_guerra"] for u in itens] == ["Henrique"]


def test_editar_muda_so_o_informado_e_da_anotar(api_admin):
    cadete = UsuarioFactory(cadete=True, nome="Antigo", email="a@b.com")

    resp = api_admin.patch(f"admin/usuarios/{cadete.pk}", {"nome": "Novo", "anotar": True})

    dados = resp.json()
    assert dados["nome"] == "Novo"
    assert dados["email"] == "a@b.com"
    assert dados["anotar"] is True
    cadete = Usuario.objects.get(pk=cadete.pk)
    assert cadete.has_perm("anotacoes.anotar")


def test_busca_ignora_acento(api_admin):
    UsuarioFactory(nome="João Câmara")

    nomes = [u["nome"] for u in api_admin.get("admin/usuarios?busca=joao camara").json()["items"]]

    assert nomes == ["João Câmara"]


def test_resetar_senha_derruba_a_sessao_e_libera_o_bloqueio(api_admin):
    alvo = UsuarioFactory(oficial=True)
    sessao_do_alvo = ClienteApi()
    sessao_do_alvo.login(alvo.numerica)
    AccessAttempt.objects.create(
        username=alvo.numerica, ip_address="10.0.0.1", failures_since_start=5
    )

    senha = api_admin.post(f"admin/usuarios/{alvo.pk}/resetar-senha").json()["senha_temporaria"]

    assert sessao_do_alvo.get("auth/me").status_code == 401
    assert not AccessAttempt.objects.filter(username=alvo.numerica).exists()
    assert ClienteApi().login(alvo.numerica, senha).json()["deve_trocar_senha"] is True
    # O login do alvo (last_login) não gera linha: a última continua sendo a do reset.
    assert alvo.history.first().history_change_reason == "Senha redefinida pelo painel"


def test_desativar_derruba_a_sessao_e_nao_apaga(api_admin):
    alvo = UsuarioFactory(cadete=True)
    sessao_do_alvo = ClienteApi()
    sessao_do_alvo.login(alvo.numerica)

    assert api_admin.post(f"admin/usuarios/{alvo.pk}/desativar").json()["ativo"] is False

    assert sessao_do_alvo.get("auth/me").status_code == 401
    assert Usuario.objects.filter(pk=alvo.pk).exists()
    assert api_admin.post(f"admin/usuarios/{alvo.pk}/reativar").json()["ativo"] is True


def test_admin_nao_desativa_a_si_mesmo(api_admin, admin):
    resp = api_admin.post(f"admin/usuarios/{admin.pk}/desativar")

    assert resp.json()["detail"] == "Você não pode desativar a si mesmo."


def test_desativar_em_lote_conta_so_quem_mudou(api_admin):
    ativos = UsuarioFactory.create_batch(2, cadete=True)
    ja_inativo = UsuarioFactory(cadete=True, is_active=False)
    ids = [u.pk for u in [*ativos, ja_inativo]]

    resp = api_admin.post("admin/usuarios/lote", {"usuario_ids": ids, "acao": "desativar"})

    assert resp.json() == {"quantidade": 2}
    assert not Usuario.objects.filter(pk__in=ids, is_active=True).exists()
    assert ativos[0].history.first().is_active is False

    resp = api_admin.post("admin/usuarios/lote", {"usuario_ids": ids, "acao": "reativar"})
    assert resp.json() == {"quantidade": 3}


def test_lote_e_tudo_ou_nada(api_admin, admin):
    alvo = UsuarioFactory(cadete=True)

    resp = api_admin.post(
        "admin/usuarios/lote", {"usuario_ids": [alvo.pk, admin.pk], "acao": "desativar"}
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Você não pode desativar a si mesmo."
    alvo.refresh_from_db()
    assert alvo.is_active is True


def test_lote_recusa_usuario_que_nao_existe(api_admin):
    alvo = UsuarioFactory(cadete=True)

    resp = api_admin.post(
        "admin/usuarios/lote", {"usuario_ids": [alvo.pk, 999_999], "acao": "permitir_anotar"}
    )

    assert resp.json()["detail"] == "Algum dos usuários escolhidos não existe mais."
    assert not alvo.has_perm("anotacoes.anotar")


def test_permitir_e_retirar_anotar_em_lote(api_admin):
    cadetes = UsuarioFactory.create_batch(3, cadete=True)
    ids = [c.pk for c in cadetes]

    resp = api_admin.post("admin/usuarios/lote", {"usuario_ids": ids, "acao": "permitir_anotar"})

    assert resp.json() == {"quantidade": 3}
    lista = api_admin.get("admin/usuarios?grupo=Cadete").json()["items"]
    assert all(u["anotar"] for u in lista if u["id"] in ids)

    resp = api_admin.post("admin/usuarios/lote", {"usuario_ids": ids[:2], "acao": "retirar_anotar"})
    assert resp.json() == {"quantidade": 2}
    assert [Usuario.objects.get(pk=i).has_perm("anotacoes.anotar") for i in ids] == [
        False,
        False,
        True,
    ]


def test_lote_exige_gerenciar_usuarios(api):
    ator = UsuarioFactory(comandante=True)
    alvo = UsuarioFactory(cadete=True)
    api.login(ator.numerica)

    resp = api.post("admin/usuarios/lote", {"usuario_ids": [alvo.pk], "acao": "desativar"})

    assert resp.status_code == 403
    alvo.refresh_from_db()
    assert alvo.is_active is True


def test_unico_administrador_nao_perde_a_permissao(api_admin, admin):
    resp = api_admin.patch(f"admin/usuarios/{admin.pk}", {"grupos": ["Oficial"]})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "O sistema precisa de pelo menos um administrador ativo."
    assert admin.groups.filter(name="Administrador").exists()


def test_admin_nao_remove_a_propria_permissao_mesmo_havendo_outro(api_admin, admin):
    UsuarioFactory(grupo="Administrador")

    resp = api_admin.patch(f"admin/usuarios/{admin.pk}", {"grupos": ["Oficial"]})

    assert resp.json()["detail"] == "Você não pode remover a sua própria permissão de administrar."


def test_outro_admin_pode_ser_rebaixado_se_sobrar_alguem(api_admin):
    outro = UsuarioFactory(grupo="Administrador")

    resp = api_admin.patch(f"admin/usuarios/{outro.pk}", {"grupos": ["Oficial"]})

    assert resp.json()["grupos"] == ["Oficial"]


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("get", "admin/usuarios"),
        ("post", "admin/usuarios"),
        ("patch", "admin/usuarios/{id}"),
        ("post", "admin/usuarios/{id}/desativar"),
        ("post", "admin/usuarios/{id}/reativar"),
        ("post", "admin/usuarios/{id}/resetar-senha"),
    ],
)
@pytest.mark.parametrize("perfil", ["cadete", "oficial", "comandante"])
def test_rotas_de_usuarios_exigem_gerenciar_usuarios(api, perfil, metodo, caminho):
    ator = UsuarioFactory(**{perfil: True})
    alvo = UsuarioFactory()
    api.login(ator.numerica)

    # Válido: o 403 vem da permissão, não do schema.
    corpo = {"numerica": "9999", "nome": "X", "nome_guerra": "X"}
    resp = getattr(api, metodo)(caminho.format(id=alvo.pk), *([corpo] if metodo != "get" else []))

    assert resp.status_code == 403
