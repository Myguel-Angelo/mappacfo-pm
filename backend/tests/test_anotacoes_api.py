"""Rotas de anotações: matriz de permissões, visibilidade por perfil, consultas e histórico."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from anotacoes import services
from anotacoes.models import Anotacao
from tests.factories import AnotacaoFactory, DespachoFactory, TipoPunicaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

Tipo = Anotacao.Tipo
AMANHA = (timezone.localdate() + timedelta(days=1)).isoformat()


PERFIS = {
    "cadete": lambda: UsuarioFactory(cadete=True),
    "cadete_anotador": lambda: UsuarioFactory(cadete=True, perms=["anotacoes.anotar"]),
    "oficial": lambda: UsuarioFactory(oficial=True),
    "comandante": lambda: UsuarioFactory(comandante=True),
}


def _alvo(ator):
    # Ações sobre anotações usam uma do próprio cadete quando o ator é cadete: assim a
    # anotação é visível para ele e o teste mede a permissão (403), não a visibilidade (404).
    return ator if ator.groups.filter(name="Cadete").exists() else UsuarioFactory(cadete=True)


def _punicao():
    return TipoPunicaoFactory(nome="Pernoite")


# Cada ação monta os dados de que precisa e devolve (método, caminho, corpo).
ACOES = {
    "ver_minhas": lambda ator: ("get", "anotacoes/minhas", None),
    "listar_cadetes": lambda ator: ("get", "cadetes", None),
    "listar_anotacoes": lambda ator: ("get", "anotacoes", None),
    "ver_estatisticas": lambda ator: ("get", "estatisticas/semana", None),
    "listar_punicoes": lambda ator: ("get", "punicoes", None),
    "anotar": lambda ator: (
        "post",
        "anotacoes",
        {"cadete_id": UsuarioFactory(cadete=True).pk, "tipo": "negativa", "motivo": "Atraso"},
    ),
    "despachar": lambda ator: (
        "post",
        f"anotacoes/{AnotacaoFactory(cadete=_alvo(ator)).pk}/despacho",
        {"punicao_id": _punicao().pk, "data_cumprimento": AMANHA},
    ),
    "editar_despacho": lambda ator: (
        "put",
        f"anotacoes/{DespachoFactory(anotacao__cadete=_alvo(ator)).anotacao_id}/despacho",
        {"punicao_id": _punicao().pk, "data_cumprimento": AMANHA},
    ),
    "compensar": lambda ator: _compensar(_alvo(ator)),
    "arquivar_positiva": lambda ator: (
        "post",
        f"anotacoes/{AnotacaoFactory(cadete=_alvo(ator), tipo=Tipo.POSITIVA).pk}/arquivar",
        None,
    ),
    "anular": lambda ator: (
        "post",
        f"anotacoes/{AnotacaoFactory(cadete=_alvo(ator)).pk}/anular",
        {"justificativa": "Lançada por engano"},
    ),
    "marcar_cumprida": lambda ator: (
        "post",
        f"anotacoes/{DespachoFactory(anotacao__cadete=_alvo(ator)).anotacao_id}/cumprida",
        None,
    ),
}


def _compensar(cadete):
    positiva = AnotacaoFactory(cadete=cadete, tipo=Tipo.POSITIVA)
    negativa = AnotacaoFactory(cadete=cadete)
    return "post", f"anotacoes/{positiva.pk}/compensar", {"negativa_id": negativa.pk}


#                     cadete  c/anotar  oficial  comandante
MATRIZ = {
    "ver_minhas": (200, 200, 200, 200),
    "ver_estatisticas": (403, 403, 403, 200),
    "listar_cadetes": (403, 200, 200, 200),
    "listar_anotacoes": (403, 403, 200, 200),
    "anotar": (403, 201, 201, 201),
    "listar_punicoes": (403, 403, 403, 200),
    "despachar": (403, 403, 403, 200),
    "editar_despacho": (403, 403, 403, 200),
    "compensar": (403, 403, 403, 200),
    "arquivar_positiva": (403, 403, 403, 200),
    "anular": (403, 403, 403, 200),
    "marcar_cumprida": (403, 403, 403, 200),
}

CASOS = [
    pytest.param(perfil, acao, esperado, id=f"{perfil}-{acao}")
    for acao, esperados in MATRIZ.items()
    for perfil, esperado in zip(PERFIS, esperados, strict=True)
]


@pytest.mark.parametrize(("perfil", "acao", "esperado"), CASOS)
def test_matriz_de_permissoes(api, perfil, acao, esperado):
    ator = PERFIS[perfil]()
    metodo, caminho, corpo = ACOES[acao](ator)
    api.login(ator.numerica)

    resp = api.get(caminho) if metodo == "get" else getattr(api, metodo)(caminho, corpo)

    assert resp.status_code == esperado, resp.content


def test_sem_sessao_retorna_401(api):
    assert api.get("anotacoes/minhas").status_code == 401


def test_escrita_sem_csrf_retorna_403(api, comandante):
    anotacao = AnotacaoFactory()
    api.login(comandante.numerica)

    resp = api.post(
        f"anotacoes/{anotacao.pk}/anular", {"justificativa": "Sem token"}, com_csrf=False
    )

    assert resp.status_code == 403
    anotacao.refresh_from_db()
    assert anotacao.status == Anotacao.Status.NOTIFICADA


# Visibilidade


def test_cadete_nao_ve_anotacao_de_outro_nem_pelo_id(api, cadete):
    de_outro = AnotacaoFactory()
    api.login(cadete.numerica)

    assert api.get(f"anotacoes/{de_outro.pk}").status_code == 404
    assert (
        api.post(f"anotacoes/{de_outro.pk}/anular", {"justificativa": "x" * 10}).status_code == 404
    )


def test_cadete_ve_as_proprias(api, cadete, comandante):
    propria = AnotacaoFactory(cadete=cadete)
    anulada = AnotacaoFactory(cadete=cadete)
    services.anular(comandante, anulada, "Lançada por engano")
    AnotacaoFactory()  # de outro cadete
    api.login(cadete.numerica)

    minhas = api.get("anotacoes/minhas").json()

    assert [a["id"] for a in minhas] == [propria.pk]
    assert api.get(f"anotacoes/{propria.pk}").status_code == 200


def test_anotador_ve_as_que_fez_pelo_id(api, cadete):
    anotador = UsuarioFactory(cadete=True, perms=["anotacoes.anotar"])
    feita = AnotacaoFactory(autor=anotador, cadete=cadete)
    api.login(anotador.numerica)

    assert api.get(f"anotacoes/{feita.pk}").status_code == 200
    assert api.get(f"anotacoes/{AnotacaoFactory().pk}").status_code == 404


def test_listagem_filtra_e_pagina(api, oficial):
    turma_cadete = UsuarioFactory(cadete=True)
    AnotacaoFactory(cadete=turma_cadete)
    AnotacaoFactory(cadete=turma_cadete, tipo=Tipo.POSITIVA)
    AnotacaoFactory()
    api.login(oficial.numerica)

    tudo = api.get("anotacoes").json()
    da_turma = api.get(f"anotacoes?turma_id={turma_cadete.turma_id}").json()
    positivas = api.get(f"anotacoes?turma_id={turma_cadete.turma_id}&tipo=positiva").json()

    assert tudo["count"] == 3
    assert da_turma["count"] == 2
    assert [a["tipo"] for a in da_turma["items"]] == ["positiva", "negativa"]  # positivas antes
    assert positivas["count"] == 1


def test_listar_cadetes_por_turma(api, oficial):
    cadete = UsuarioFactory(cadete=True)
    UsuarioFactory(cadete=True)
    UsuarioFactory(cadete=True, is_active=False, turma=cadete.turma)
    api.login(oficial.numerica)

    todos = api.get("cadetes").json()
    da_turma = api.get(f"cadetes?turma_id={cadete.turma_id}").json()

    assert len(todos) == 2
    assert [c["numerica"] for c in da_turma] == [cadete.numerica]


def test_despachar_sem_data_retorna_422(api, comandante):
    api.login(comandante.numerica)

    resp = api.post(f"anotacoes/{AnotacaoFactory().pk}/despacho", {"punicao_id": _punicao().pk})

    assert resp.status_code == 422


def test_regra_violada_vira_400_com_mensagem(api, comandante):
    api.login(comandante.numerica)
    ontem = (timezone.localdate() - timedelta(days=1)).isoformat()

    resp = api.post(
        f"anotacoes/{AnotacaoFactory().pk}/despacho",
        {"punicao_id": _punicao().pk, "data_cumprimento": ontem},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "regra_violada"
    assert "data futura" in resp.json()["detail"]


def test_editar_despacho_de_anotacao_sem_despacho_retorna_404(api, comandante):
    api.login(comandante.numerica)

    resp = api.put(
        f"anotacoes/{AnotacaoFactory().pk}/despacho",
        {"punicao_id": _punicao().pk, "data_cumprimento": AMANHA},
    )

    assert resp.status_code == 404


def test_compensacao_aparece_nas_duas_anotacoes(api, comandante):
    metodo, caminho, corpo = _compensar(UsuarioFactory(cadete=True))
    api.login(comandante.numerica)

    positiva = api.post(caminho, corpo).json()
    negativa = api.get(f"anotacoes/{corpo['negativa_id']}").json()

    assert positiva["status"] == negativa["status"] == "compensada"
    assert positiva["compensada_com_id"] == negativa["id"]
    assert negativa["compensada_com_id"] == positiva["id"]


# Consultas e histórico


def _criar_anotacoes(n, comandante):
    for i in range(n):
        anotacao = AnotacaoFactory()
        if i % 3 == 0:
            DespachoFactory(anotacao=anotacao, despachado_por=comandante)
        elif i % 3 == 1:
            positiva = AnotacaoFactory(cadete=anotacao.cadete, tipo=Tipo.POSITIVA)
            services.compensar(comandante, positiva, anotacao.pk)


def _contar_consultas(api, caminho):
    with CaptureQueriesContext(connection) as ctx:
        assert api.get(caminho).status_code == 200
    return len(ctx.captured_queries)


def test_listagem_tem_numero_fixo_de_consultas(api, comandante):
    api.login(comandante.numerica)
    _criar_anotacoes(3, comandante)
    poucas = _contar_consultas(api, "anotacoes")

    _criar_anotacoes(12, comandante)
    muitas = _contar_consultas(api, "anotacoes")

    assert muitas == poucas  # sem N+1


def test_historico_registra_quem_despachou(api, comandante):
    anotacao = AnotacaoFactory()
    api.login(comandante.numerica)

    api.post(
        f"anotacoes/{anotacao.pk}/despacho",
        {"punicao_id": _punicao().pk, "data_cumprimento": AMANHA},
    )

    ultima = anotacao.history.latest()
    assert ultima.status == Anotacao.Status.DESPACHADA
    assert ultima.history_user == comandante
    assert ultima.prev_record.status == Anotacao.Status.NOTIFICADA


def test_autor_vem_com_perfil_para_exibicao(api, comandante):
    AnotacaoFactory(autor=comandante)
    AnotacaoFactory()  # autor oficial (padrão da factory)
    AnotacaoFactory(autor=UsuarioFactory(cadete=True, perms=["anotacoes.anotar"]))
    api.login(comandante.numerica)

    perfis = {a["autor"]["perfil"] for a in api.get("anotacoes").json()["items"]}

    assert perfis == {"Oficial Comandante", "Oficial", "Cadete"}
