"""Login pelo nome de guerra: CAD obrigatório para cadetes, um erro de digitação tolerado
quando aponta para uma pessoa só, e o bloqueio contado pela conta, não pelo texto."""

import pytest

from tests.factories import SENHA, UsuarioFactory

pytestmark = pytest.mark.django_db

MSG = "Nome de guerra ou senha incorreta."


@pytest.fixture
def bruno():
    return UsuarioFactory(cadete=True, numerica="4321", nome_guerra="Bruno")


@pytest.mark.parametrize(
    "texto", ["CAD BRUNO", "cad bruno", "Cad. Brunô", "CAD-BRUNO", " CAD  Bruno "]
)
def test_cadete_entra_com_cad_e_o_nome_de_guerra(api, bruno, texto):
    resp = api.entrar(texto)

    assert resp.status_code == 200
    assert resp.json()["numerica"] == "4321"


@pytest.mark.parametrize("texto", ["BRUNO", "4321", "CAD 4321", "CADBRUNO"])
def test_sem_o_cad_ou_pela_numerica_nao_entra(api, bruno, texto):
    resp = api.entrar(texto)

    assert resp.status_code == 401
    assert resp.json()["detail"] == MSG


def test_oficial_entra_sem_cad_e_nao_com_cad(api):
    UsuarioFactory(oficial=True, nome_guerra="Ten. Cássio")

    assert api.entrar("CAD TEN CASSIO").status_code == 401
    assert api.entrar("ten cassio").status_code == 200


@pytest.mark.parametrize("texto", ["CAD BRUNOS", "CAD BRUN", "CAD BRUNA", "CAD BURNO"])
def test_um_erro_de_digitacao_e_tolerado(api, bruno, texto):
    assert api.entrar(texto).json()["numerica"] == "4321"


def test_dois_erros_nao(api, bruno):
    assert api.entrar("CAD BRUNAS").status_code == 401


def test_nome_exato_vence_o_parecido(api, bruno):
    UsuarioFactory(cadete=True, numerica="9999", nome_guerra="Brunos")

    assert api.entrar("CAD BRUNOS").json()["numerica"] == "9999"


def test_erro_que_aponta_para_duas_pessoas_nao_adivinha(api):
    UsuarioFactory(cadete=True, nome_guerra="Bruna")
    UsuarioFactory(cadete=True, nome_guerra="Bruni")

    # "BRUNO" está a um erro das duas.
    assert api.entrar("CAD BRUNO").status_code == 401


def test_nome_curto_nao_tem_tolerancia(api):
    UsuarioFactory(cadete=True, nome_guerra="Ana")

    assert api.entrar("CAD ANA").status_code == 200
    assert api.entrar("CAD ANE").status_code == 401


def test_cadete_sem_cad_nao_e_corrigido_para_um_oficial_parecido(api, bruno):
    # Mesma senha de propósito: se adivinhasse "BRUNA", entraria na conta do oficial.
    UsuarioFactory(oficial=True, nome_guerra="Bruna")

    assert api.entrar("BRUNO").status_code == 401


def test_erro_de_digitacao_nao_acha_inativo(api):
    UsuarioFactory(cadete=True, nome_guerra="Bruno", is_active=False)

    assert api.entrar("CAD BRUNOS").status_code == 401


def test_variar_a_grafia_nao_da_tentativas_a_mais(api, bruno):
    # Cada falha com uma grafia; todas contam contra a conta do BRUNO. A 5ª já bloqueia.
    for texto in ["CAD BRUNO", "CAD BRUNOS", "CAD BRUNA", "CAD BURNO"]:
        assert api.entrar(texto, "errada").status_code == 401
    assert api.entrar("CAD BRUN", "errada").status_code == 429

    resp = api.entrar("CAD BRUNO", SENHA)

    assert resp.status_code == 429
    assert resp.json()["codigo"] == "login_bloqueado"
