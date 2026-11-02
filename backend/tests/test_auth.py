import pytest
from django.contrib.auth.models import Group
from django.contrib.sessions.backends.db import SessionStore

from tests.factories import SENHA, UsuarioFactory

pytestmark = pytest.mark.django_db

MSG_LOGIN_INVALIDO = "Numérica ou senha incorreta."


# Login


def test_login_ok_retorna_dados_e_cria_sessao(api, usuario):
    resp = api.login(usuario.numerica)

    assert resp.status_code == 200
    assert resp.json()["numerica"] == usuario.numerica
    assert "sessionid" in api.cookies
    assert api.get("auth/me").status_code == 200


def test_login_troca_a_sessao(api, usuario):
    # Session fixation: a sessão de antes do login não pode continuar valendo.
    anterior = SessionStore()
    anterior["visitou"] = True
    anterior.create()
    api.client.cookies["sessionid"] = anterior.session_key

    api.login(usuario.numerica)

    assert api.cookies["sessionid"].value != anterior.session_key


def test_login_sem_csrf_retorna_403(api, usuario):
    resp = api.post("auth/login", {"numerica": usuario.numerica, "senha": SENHA}, com_csrf=False)

    assert resp.status_code == 403
    assert "sessionid" not in api.cookies


def test_login_senha_errada_retorna_401(api, usuario):
    resp = api.login(usuario.numerica, "errada")

    assert resp.status_code == 401
    assert resp.json()["detail"] == MSG_LOGIN_INVALIDO


def test_login_numerica_inexistente_tem_a_mesma_mensagem(api, db):
    resp = api.login("000000", "qualquer")

    assert resp.status_code == 401
    assert resp.json()["detail"] == MSG_LOGIN_INVALIDO


def test_login_com_o_hash_como_senha_retorna_401(api, usuario):
    # No sistema antigo, colar o hash do banco no campo de senha entrava.
    resp = api.login(usuario.numerica, usuario.password)

    assert resp.status_code == 401


def test_usuario_inativo_nao_loga(api):
    inativo = UsuarioFactory(is_active=False)

    assert api.login(inativo.numerica).status_code == 401


def test_senha_salva_com_argon2(usuario):
    assert usuario.password.startswith("argon2")


# Sessão


def test_me_sem_sessao_retorna_401(api):
    assert api.get("auth/me").status_code == 401


def test_me_lista_grupos_e_permissoes(api, usuario):
    usuario.groups.add(Group.objects.get(name="Administrador"))
    api.login(usuario.numerica)

    dados = api.get("auth/me").json()

    assert dados["grupos"] == ["Administrador"]
    assert dados["perfil"] == "Administrador"
    assert "contas.gerenciar_usuarios" in dados["permissoes"]


def test_logout_encerra_a_sessao(logado):
    assert logado.post("auth/logout").status_code == 204
    assert logado.get("auth/me").status_code == 401


def test_logout_sem_csrf_retorna_403(logado):
    assert logado.post("auth/logout", com_csrf=False).status_code == 403
    assert logado.get("auth/me").status_code == 200


# Troca de senha


@pytest.mark.urls("tests.urls_protegida")
def test_troca_pendente_bloqueia_rotas_e_libera_depois(api):
    novo = UsuarioFactory(deve_trocar_senha=True)
    api.login(novo.numerica)

    resp = api.get("/api-teste/protegida")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "troca_senha_pendente"
    # As rotas necessárias para trocar a senha continuam abertas.
    assert api.get("auth/me").status_code == 200

    nova = "Outra-senha-forte-77"
    resp = api.post(
        "auth/trocar-senha", {"senha_atual": SENHA, "nova_senha": nova, "confirmacao": nova}
    )
    assert resp.status_code == 200
    assert resp.json()["deve_trocar_senha"] is False

    assert api.get("/api-teste/protegida").status_code == 200


def test_troca_de_senha_mantem_a_sessao(logado, usuario):
    nova = "Outra-senha-forte-77"
    resp = logado.post(
        "auth/trocar-senha", {"senha_atual": SENHA, "nova_senha": nova, "confirmacao": nova}
    )

    assert resp.status_code == 200
    assert logado.get("auth/me").status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password(nova)


@pytest.mark.parametrize(
    ("atual", "nova", "confirmacao", "mensagem"),
    [
        ("errada", "Outra-senha-forte-77", "Outra-senha-forte-77", "Senha atual incorreta."),
        (SENHA, "Outra-senha-forte-77", "Diferente-77", "A confirmação não confere"),
        (SENHA, SENHA, SENHA, "precisa ser diferente"),
        (SENHA, "12345678", "12345678", "não atende às regras"),
    ],
    ids=["atual-errada", "confirmacao-diferente", "igual-a-atual", "fraca"],
)
def test_troca_de_senha_rejeita(logado, usuario, atual, nova, confirmacao, mensagem):
    resp = logado.post(
        "auth/trocar-senha",
        {"senha_atual": atual, "nova_senha": nova, "confirmacao": confirmacao},
    )

    assert resp.status_code == 400
    assert mensagem in resp.json()["detail"]
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA)


def test_troca_de_senha_sem_sessao_retorna_401(api):
    api.csrf()
    resp = api.post(
        "auth/trocar-senha", {"senha_atual": "a", "nova_senha": "b", "confirmacao": "b"}
    )

    assert resp.status_code == 401


# Limite de tentativas


def test_axes_bloqueia_apos_5_falhas(api, usuario):
    for _ in range(4):
        assert api.login(usuario.numerica, "errada").status_code == 401

    resp = api.login(usuario.numerica, "errada")
    assert resp.status_code == 429
    assert resp.json()["codigo"] == "login_bloqueado"

    # Bloqueado: nem a senha certa entra.
    assert api.login(usuario.numerica).status_code == 429


def test_axes_nao_bloqueia_outra_numerica_no_mesmo_ip(api, usuario):
    outro = UsuarioFactory()
    for _ in range(5):
        api.login(usuario.numerica, "errada")

    assert api.login(outro.numerica).status_code == 200
