"""Duas abas despachando o mesmo cadete na mesma data ao mesmo tempo."""

import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from anotacoes import services
from anotacoes.models import Despacho
from core.erros import RegraViolada
from tests.factories import AnotacaoFactory, TipoPunicaoFactory, UsuarioFactory


@pytest.mark.django_db(transaction=True)
def test_corrida_de_despacho_na_mesma_data():
    comandante = UsuarioFactory(comandante=True)
    cadete = UsuarioFactory(cadete=True)
    punicao = TipoPunicaoFactory()
    negativas = [AnotacaoFactory(cadete=cadete), AnotacaoFactory(cadete=cadete)]
    data = timezone.localdate() + timedelta(days=1)

    largada = threading.Barrier(2)
    resultados = []

    def despachar(negativa):
        try:
            largada.wait()
            services.despachar(comandante, negativa, punicao.pk, data)
            resultados.append("ok")
        except RegraViolada:
            resultados.append("recusado")
        finally:
            connection.close()  # cada thread abre a própria conexão

    threads = [threading.Thread(target=despachar, args=(n,)) for n in negativas]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(resultados) == ["ok", "recusado"]
    assert Despacho.objects.filter(anotacao__cadete=cadete, data_cumprimento=data).count() == 1
