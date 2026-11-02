"""Planilha e exportação do mappa: layout, permissão, arquivamento e atomicidade."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from anotacoes.models import Anotacao
from core.erros import RegraViolada, SemPermissao
from mappas import services
from mappas.models import Mappa
from mappas.planilha import COLUNAS, montar_planilha
from tests.factories import AnotacaoFactory, DespachoFactory, TurmaFactory, UsuarioFactory

Status = Anotacao.Status

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("armazenamento")]


def _ler(conteudo: bytes):
    return load_workbook(BytesIO(conteudo)).active


def _despachada(**kwargs):
    return DespachoFactory(**{f"anotacao__{k}": v for k, v in kwargs.items()}).anotacao


# Planilha


def test_planilha_tem_o_cabecalho_e_uma_linha_por_anotacao(comandante):
    anotacoes = [_despachada() for _ in range(3)]

    aba = _ler(montar_planilha(anotacoes))

    assert [c.value for c in aba[1]] == [titulo for titulo, _ in COLUNAS]
    assert aba.max_row == 4
    assert aba["A1"].font.bold
    assert aba.column_dimensions["C"].width == 50


def test_planilha_descreve_cadete_motivo_e_despacho():
    turma = TurmaFactory(nome="CFO II")
    cadete = UsuarioFactory(cadete=True, turma=turma, numerica="2001", nome="Fulano de Tal")
    autor = UsuarioFactory(comandante=True, nome="Cap Beltrano")
    anotacao = _despachada(cadete=cadete, autor=autor, motivo="Atraso na formatura")

    turma_c, cadete_c, motivo_c, despacho_c, _, data_c, _ = (
        c.value for c in _ler(montar_planilha([anotacao]))[2]
    )

    assert turma_c == "CFO II"
    assert cadete_c == "2001 - Fulano de Tal"
    assert motivo_c.startswith("Anotado Negativamente por Oficial Comandante Cap Beltrano em ")
    assert motivo_c.endswith(": Atraso na formatura")
    data = anotacao.despacho.data_cumprimento
    assert despacho_c == f"{anotacao.despacho.punicao.nome} - {data:%d/%m/%Y}"
    assert data_c == "__/__/____"


# Exportação


def test_sem_permissao_de_exportar(oficial):
    _despachada()

    with pytest.raises(SemPermissao):
        services.gerar_mappa(oficial, "Mappa 1")


def test_sem_despachadas_e_regra_violada(comandante, armazenamento):
    AnotacaoFactory()  # notificada não entra

    with pytest.raises(RegraViolada, match="Não há anotações despachadas"):
        services.gerar_mappa(comandante, "Mappa 1")

    assert Mappa.objects.count() == 0
    assert not armazenamento.exists() or not any(armazenamento.rglob("*.xlsx"))


def test_titulo_obrigatorio(comandante):
    _despachada()

    with pytest.raises(RegraViolada, match="título"):
        services.gerar_mappa(comandante, "   ")


def test_exportar_arquiva_as_despachadas_e_guarda_o_arquivo(comandante, armazenamento):
    despachadas = [_despachada() for _ in range(2)]
    notificada = AnotacaoFactory()

    mappa = services.gerar_mappa(comandante, "MAPA N°014/2026")

    assert set(mappa.anotacoes.all()) == set(despachadas)
    for anotacao in despachadas:
        anotacao.refresh_from_db()
        assert anotacao.status == Status.ARQUIVADA
        assert anotacao.history.first().status == Status.ARQUIVADA
    notificada.refresh_from_db()
    assert notificada.status == Status.NOTIFICADA

    arquivos = list(armazenamento.rglob("*.xlsx"))
    assert len(arquivos) == 1
    assert len(arquivos[0].stem) == 32  # uuid hex: nada do título no disco
    assert _ler(arquivos[0].read_bytes()).max_row == 3
    assert Anotacao.objects.count() == 3  # nada apagado


def test_falha_depois_de_gravar_o_arquivo_nao_muda_nada(comandante, armazenamento, monkeypatch):
    anotacao = _despachada()

    def falhar(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(Mappa.anotacoes.related_manager_cls, "set", falhar)

    with pytest.raises(RuntimeError):
        services.gerar_mappa(comandante, "Mappa 1")

    anotacao.refresh_from_db()
    assert anotacao.status == Status.DESPACHADA
    assert Mappa.objects.count() == 0
    assert not any(armazenamento.rglob("*.xlsx"))  # arquivo órfão apagado


def test_falha_ao_salvar_o_arquivo_nao_muda_nada(comandante, monkeypatch):
    anotacao = _despachada()

    def falhar(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr("mappas.storage.StoragePrivado._save", falhar)

    with pytest.raises(OSError):
        services.gerar_mappa(comandante, "Mappa 1")

    anotacao.refresh_from_db()
    assert anotacao.status == Status.DESPACHADA
    assert Mappa.objects.count() == 0


@pytest.mark.parametrize(
    ("titulo", "esperado"),
    [
        ("MAPA N°014/2026", "mapa-n014-2026.xlsx"),
        ("../../etc/passwd", "etc-passwd.xlsx"),
        ("Mappa de Março", "mappa-de-marco.xlsx"),
        ("///", "mappa.xlsx"),
    ],
)
def test_nome_de_download_seguro(titulo, esperado):
    assert services.nome_download(titulo) == esperado


def test_publicar_exige_exportar(oficial, comandante):
    _despachada()
    mappa = services.gerar_mappa(comandante, "Mappa 1")

    with pytest.raises(SemPermissao):
        services.publicar(oficial, mappa, True)

    assert services.publicar(comandante, mappa, True).publicado is True
