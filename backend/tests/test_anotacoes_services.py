"""Regras dos serviços, sem HTTP: caminho feliz e cada violação."""

from datetime import date, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from anotacoes import services
from anotacoes.models import Anotacao, Compensacao
from core.erros import RegraViolada, SemPermissao
from tests.factories import AnotacaoFactory, DespachoFactory, TipoPunicaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

Status = Anotacao.Status
Tipo = Anotacao.Tipo


# criar_anotacao


def test_oficial_anota_cadete(oficial, cadete):
    anotacao = services.criar_anotacao(oficial, cadete.pk, Tipo.NEGATIVA, "  Atraso  ")

    assert anotacao.status == Status.NOTIFICADA
    assert anotacao.autor == oficial
    assert anotacao.motivo == "Atraso"


def test_cadete_com_permissao_individual_anota(cadete):
    anotador = UsuarioFactory(cadete=True, perms=["anotacoes.anotar"])

    assert services.criar_anotacao(anotador, cadete.pk, Tipo.POSITIVA, "Destaque").pk


def test_cadete_sem_permissao_nao_anota(cadete):
    outro = UsuarioFactory(cadete=True)

    with pytest.raises(SemPermissao):
        services.criar_anotacao(outro, cadete.pk, Tipo.NEGATIVA, "x")


def test_nao_anota_a_si_mesmo():
    anotador = UsuarioFactory(cadete=True, perms=["anotacoes.anotar"])

    with pytest.raises(RegraViolada, match="si mesmo"):
        services.criar_anotacao(anotador, anotador.pk, Tipo.NEGATIVA, "x")


@pytest.mark.parametrize(
    "alvo",
    [
        lambda: UsuarioFactory(oficial=True),
        lambda: UsuarioFactory(cadete=True, is_active=False),
        lambda: None,
    ],
    ids=["nao-cadete", "cadete-inativo", "inexistente"],
)
def test_so_anota_cadete_ativo(oficial, alvo):
    usuario = alvo()
    with pytest.raises(RegraViolada, match="cadetes ativos"):
        services.criar_anotacao(oficial, usuario.pk if usuario else 999_999, Tipo.NEGATIVA, "x")


def test_motivo_em_branco(oficial, cadete):
    with pytest.raises(RegraViolada, match="motivo"):
        services.criar_anotacao(oficial, cadete.pk, Tipo.NEGATIVA, "   ")


def test_tipo_invalido(oficial, cadete):
    with pytest.raises(RegraViolada, match="Tipo"):
        services.criar_anotacao(oficial, cadete.pk, "neutra", "x")


# despachar


def test_despachar_negativa(comandante, punicao, amanha):
    negativa = AnotacaoFactory()

    despacho = services.despachar(comandante, negativa, punicao.pk, amanha)

    negativa.refresh_from_db()
    assert negativa.status == Status.DESPACHADA
    assert despacho.punicao == punicao
    assert despacho.despachado_por == comandante


def test_despachar_para_hoje_vale(comandante, punicao, hoje):
    assert services.despachar(comandante, AnotacaoFactory(), punicao.pk, hoje)


def test_despachar_exige_permissao(oficial, punicao, amanha):
    with pytest.raises(SemPermissao):
        services.despachar(oficial, AnotacaoFactory(), punicao.pk, amanha)


def test_despachar_data_no_passado(comandante, punicao, hoje):
    with pytest.raises(RegraViolada, match="hoje ou uma data futura"):
        services.despachar(comandante, AnotacaoFactory(), punicao.pk, hoje - timedelta(days=1))


def test_despachar_positiva(comandante, punicao, amanha):
    with pytest.raises(RegraViolada, match="negativas"):
        services.despachar(comandante, AnotacaoFactory(tipo=Tipo.POSITIVA), punicao.pk, amanha)


def test_despachar_duas_vezes(comandante, punicao, amanha):
    negativa = AnotacaoFactory()
    services.despachar(comandante, negativa, punicao.pk, amanha)

    with pytest.raises(RegraViolada, match="já foi despachada"):
        services.despachar(comandante, negativa, punicao.pk, amanha + timedelta(days=1))


def test_despachar_punicao_inexistente_ou_inativa(comandante, amanha):
    inativa = TipoPunicaoFactory(nome="Extinta", ativo=False)

    with pytest.raises(RegraViolada, match="inválido"):
        services.despachar(comandante, AnotacaoFactory(), 999_999, amanha)
    with pytest.raises(RegraViolada, match="desativado"):
        services.despachar(comandante, AnotacaoFactory(), inativa.pk, amanha)


def test_uma_punicao_por_cadete_por_dia(comandante, cadete, punicao, amanha):
    services.despachar(comandante, AnotacaoFactory(cadete=cadete), punicao.pk, amanha)

    with pytest.raises(RegraViolada, match="já tem uma punição nesta data"):
        services.despachar(comandante, AnotacaoFactory(cadete=cadete), punicao.pk, amanha)


def test_outro_cadete_pode_ter_punicao_na_mesma_data(comandante, punicao, amanha):
    services.despachar(comandante, AnotacaoFactory(), punicao.pk, amanha)

    assert services.despachar(comandante, AnotacaoFactory(), punicao.pk, amanha)


def test_despacho_anulado_libera_a_data(comandante, cadete, punicao, amanha):
    primeira = AnotacaoFactory(cadete=cadete)
    services.despachar(comandante, primeira, punicao.pk, amanha)
    services.anular(comandante, primeira, "Lançada no cadete errado")

    assert services.despachar(comandante, AnotacaoFactory(cadete=cadete), punicao.pk, amanha)


# editar_despacho


def test_editar_so_a_punicao_mantendo_a_data(comandante, amanha):
    # No sistema antigo isto sempre falhava: a checagem achava o próprio despacho.
    despacho = DespachoFactory(data_cumprimento=amanha)
    revista = TipoPunicaoFactory(nome="Revista")

    services.editar_despacho(comandante, despacho, revista.pk, amanha)

    despacho.refresh_from_db()
    assert despacho.punicao == revista
    assert despacho.data_cumprimento == amanha


def test_editar_para_data_ocupada(comandante, punicao, amanha):
    ocupada = DespachoFactory(data_cumprimento=amanha)
    outro = DespachoFactory(
        anotacao__cadete=ocupada.anotacao.cadete, data_cumprimento=amanha + timedelta(days=1)
    )

    with pytest.raises(RegraViolada, match="já tem uma punição"):
        services.editar_despacho(comandante, outro, punicao.pk, amanha)


def test_editar_despacho_cumprido(comandante, punicao, amanha):
    despacho = DespachoFactory(anotacao__status=Status.CUMPRIDA)

    with pytest.raises(RegraViolada, match="não cumpridos"):
        services.editar_despacho(comandante, despacho, punicao.pk, amanha)


def test_editar_despacho_exige_permissao(oficial, punicao, amanha):
    with pytest.raises(SemPermissao):
        services.editar_despacho(oficial, DespachoFactory(), punicao.pk, amanha)


def test_editar_despacho_para_o_passado(comandante, punicao, hoje):
    with pytest.raises(RegraViolada, match="hoje ou uma data futura"):
        services.editar_despacho(
            comandante, DespachoFactory(), punicao.pk, hoje - timedelta(days=1)
        )


# compensar


def test_compensar(comandante, cadete):
    positiva = AnotacaoFactory(cadete=cadete, tipo=Tipo.POSITIVA)
    negativa = AnotacaoFactory(cadete=cadete)

    compensacao = services.compensar(comandante, positiva, negativa.pk)

    positiva.refresh_from_db()
    negativa.refresh_from_db()
    assert positiva.status == negativa.status == Status.COMPENSADA
    assert compensacao.feita_por == comandante
    # Nada some: as duas continuam no banco.
    assert Anotacao.objects.filter(pk__in=[positiva.pk, negativa.pk]).count() == 2


def test_compensar_cadetes_diferentes(comandante):
    positiva = AnotacaoFactory(tipo=Tipo.POSITIVA)

    with pytest.raises(RegraViolada, match="mesmo cadete"):
        services.compensar(comandante, positiva, AnotacaoFactory().pk)


def test_compensar_tipos_trocados(comandante, cadete):
    negativa = AnotacaoFactory(cadete=cadete)
    outra_negativa = AnotacaoFactory(cadete=cadete)

    with pytest.raises(RegraViolada, match="uma positiva por uma negativa"):
        services.compensar(comandante, negativa, outra_negativa.pk)


def test_compensar_negativa_ja_despachada(comandante):
    despacho = DespachoFactory()
    positiva = AnotacaoFactory(cadete=despacho.anotacao.cadete, tipo=Tipo.POSITIVA)

    with pytest.raises(RegraViolada, match="notificadas"):
        services.compensar(comandante, positiva, despacho.anotacao.pk)


def test_compensar_negativa_inexistente(comandante):
    with pytest.raises(RegraViolada, match="não encontrada"):
        services.compensar(comandante, AnotacaoFactory(tipo=Tipo.POSITIVA), 999_999)


def test_compensar_exige_permissao(oficial, cadete):
    positiva = AnotacaoFactory(cadete=cadete, tipo=Tipo.POSITIVA)

    with pytest.raises(SemPermissao):
        services.compensar(oficial, positiva, AnotacaoFactory(cadete=cadete).pk)
    assert not Compensacao.objects.exists()


# arquivar_positiva


def test_arquivar_positiva(comandante):
    positiva = services.arquivar_positiva(comandante, AnotacaoFactory(tipo=Tipo.POSITIVA))

    assert positiva.status == Status.ARQUIVADA


def test_arquivar_negativa(comandante):
    with pytest.raises(RegraViolada, match="positivas"):
        services.arquivar_positiva(comandante, AnotacaoFactory())


def test_arquivar_positiva_ja_encerrada(comandante):
    positiva = AnotacaoFactory(tipo=Tipo.POSITIVA, status=Status.COMPENSADA)

    with pytest.raises(RegraViolada, match="encerrada"):
        services.arquivar_positiva(comandante, positiva)


# anular


@pytest.mark.parametrize("status", [Status.NOTIFICADA, Status.DESPACHADA])
def test_anular(comandante, status):
    anotacao = AnotacaoFactory(status=status)

    services.anular(comandante, anotacao, "  Lançada por engano  ")

    anotacao.refresh_from_db()
    assert anotacao.status == Status.ANULADA
    assert anotacao.anulada_por == comandante
    assert anotacao.anulada_em is not None
    assert anotacao.motivo_anulacao == "Lançada por engano"


@pytest.mark.parametrize("status", [Status.COMPENSADA, Status.CUMPRIDA, Status.ANULADA])
def test_nao_anula_encerrada(comandante, status):
    anotacao = AnotacaoFactory()
    if status == Status.ANULADA:
        services.anular(comandante, anotacao, "Primeira anulação")
    else:
        Anotacao.objects.filter(pk=anotacao.pk).update(status=status)

    with pytest.raises(RegraViolada, match="notificadas ou despachadas"):
        services.anular(comandante, anotacao, "Justificativa")


def test_banco_exige_dados_completos_da_anulacao():
    anotacao = AnotacaoFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        Anotacao.objects.filter(pk=anotacao.pk).update(status=Status.ANULADA)


def test_anular_sem_justificativa(comandante):
    with pytest.raises(RegraViolada, match="justificativa"):
        services.anular(comandante, AnotacaoFactory(), "   ")


def test_anular_exige_permissao(oficial):
    with pytest.raises(SemPermissao):
        services.anular(oficial, AnotacaoFactory(), "Justificativa")


# marcar_cumprida


def test_marcar_cumprida(comandante):
    despacho = DespachoFactory()

    anotacao = services.marcar_cumprida(comandante, despacho.anotacao)

    assert anotacao.status == Status.CUMPRIDA


def test_marcar_cumprida_sem_despacho(comandante):
    with pytest.raises(RegraViolada, match="despachadas"):
        services.marcar_cumprida(comandante, AnotacaoFactory())


def test_marcar_cumprida_exige_permissao(oficial):
    with pytest.raises(SemPermissao):
        services.marcar_cumprida(oficial, DespachoFactory().anotacao)


# Proteção no banco


def test_banco_impede_apagar_anotacao_despachada():
    despacho = DespachoFactory()

    with pytest.raises(ProtectedError):
        despacho.anotacao.delete()


def test_banco_impede_apagar_cadete_com_anotacao():
    anotacao = AnotacaoFactory()

    with pytest.raises(ProtectedError):
        anotacao.cadete.delete()


# Estatísticas


@pytest.mark.parametrize(
    ("hoje", "segunda"),
    [
        (date(2026, 10, 26), date(2026, 10, 26)),  # segunda
        (date(2026, 10, 29), date(2026, 10, 26)),  # quinta
        (date(2026, 11, 1), date(2026, 10, 26)),  # domingo: o antigo devolvia o próprio domingo
    ],
)
def test_ultima_segunda(hoje, segunda):
    assert services.ultima_segunda(hoje) == segunda


def test_estatisticas_semana(oficial, comandante):
    cadete = UsuarioFactory(cadete=True, nome="Aaa Mais Anotado")
    for _ in range(3):
        AnotacaoFactory(cadete=cadete, autor=oficial)
    AnotacaoFactory(autor=comandante, tipo=Tipo.POSITIVA)
    anulada = AnotacaoFactory(cadete=cadete, autor=oficial)
    services.anular(comandante, anulada, "Não conta")

    dados = services.estatisticas_semana()

    assert dados["total"] == 4
    assert dados["por_tipo"] == {"positivas": 1, "negativas": 3}
    assert dados["mais_anotaram"][0] == {
        "numerica": oficial.numerica,
        "nome": oficial.nome,
        "total": 3,
    }
    assert dados["mais_anotados"][0]["numerica"] == cadete.numerica
