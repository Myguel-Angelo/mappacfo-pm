"""Nome de guerra: normalização, prefixo CAD e a tolerância de um erro de digitação."""

import pytest

from contas import nome_guerra as ng
from tests.factories import UsuarioFactory


@pytest.mark.parametrize(
    ("texto", "chave"),
    [
        ("Ten. Cássio", "TENCASSIO"),
        ("ten cassio", "TENCASSIO"),
        ("  Maj C.Henrique ", "MAJCHENRIQUE"),
        ("Garcêz", "GARCEZ"),
        ("...", ""),
    ],
)
def test_chave_ignora_acento_caixa_espaco_e_pontuacao(texto, chave):
    assert ng.chave(texto) == chave


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("CAD BRUNO", (True, " BRUNO")),
        ("cad.bruno", (True, ".BRUNO")),
        ("Cád-Bruno", (True, "-BRUNO")),
        ("CADU", (False, "CADU")),
        ("Ten Cássio", (False, "TEN CASSIO")),
    ],
)
def test_separar_prefixo(texto, esperado):
    assert ng.separar_prefixo(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "guardado"),
    [("CAD  Bruno", "Bruno"), ("cad. Bruno  Lima", "Bruno Lima"), ("Cadu", "Cadu")],
)
def test_limpar_tira_o_cad_e_os_espacos(texto, guardado):
    assert ng.limpar(texto) == guardado


@pytest.mark.parametrize(
    ("a", "b", "um"),
    [
        ("BRUNOS", "BRUNO", True),  # a mais
        ("BRUN", "BRUNO", True),  # a menos
        ("BRUNA", "BRUNO", True),  # trocada
        ("BURNO", "BRUNO", True),  # vizinhas invertidas
        ("BRUNO", "BRUNO", False),  # igual não é erro
        ("BRUNAS", "BRUNO", False),  # dois erros
        ("BORUN", "BRUNO", False),
    ],
)
def test_um_erro(a, b, um):
    assert ng.um_erro(a, b) is um
    assert ng.um_erro(b, a) is um


@pytest.mark.django_db
def test_modelo_guarda_limpo_e_atualiza_a_chave():
    usuario = UsuarioFactory(nome_guerra="CAD  Bruno")
    assert (usuario.nome_guerra, usuario.chave_login) == ("Bruno", "BRUNO")

    usuario.nome_guerra = "Bruno Lima"
    usuario.save(update_fields=["nome_guerra"])
    usuario.refresh_from_db()
    assert usuario.chave_login == "BRUNOLIMA"
