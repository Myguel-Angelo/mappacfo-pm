"""Montagem do Excel do mappa, com o layout da planilha do sistema antigo.

Só formatação: recebe as anotações já carregadas e devolve os bytes do .xlsx. Não toca no
banco nem em HTTP, para ser testada sozinha.
"""

from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

ABA = "Anotacoes Despachadas"

# (cabeçalho, largura) na ordem do sistema antigo.
COLUNAS = [
    ("Turma", 15),
    ("Cadete", 20),
    ("Motivo", 50),
    ("Tipo Despacho", 30),
    ("Ass. Ciência", 20),
    ("Data Cumprimento", 20),
    ("Ass. Cumprimento", 20),
]

_FONTE_CABECALHO = Font(bold=True, color="FFFFFF")
_FUNDO_CABECALHO = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid")
_ALINHAMENTO_CABECALHO = Alignment(horizontal="center", vertical="center")
_FINA = Side(style="thin")
_BORDA = Border(left=_FINA, right=_FINA, top=_FINA, bottom=_FINA)
_ALINHAMENTO_DADOS = Alignment(horizontal="left", vertical="top", wrap_text=True)


def linha(anotacao) -> list[str]:
    cadete = anotacao.cadete
    autor = anotacao.autor
    despacho = anotacao.despacho
    criada_em = timezone.localtime(anotacao.criada_em)
    quem = f"{autor.perfil} {autor.nome}".strip()
    return [
        cadete.turma.nome if cadete.turma else "S/ Turma",
        f"{cadete.numerica} - {cadete.nome}",
        f"Anotado Negativamente por {quem} em {criada_em:%d/%m/%Y %H:%M}: {anotacao.motivo}",
        f"{despacho.punicao.nome} - {despacho.data_cumprimento:%d/%m/%Y}",
        "",
        "__/__/____",  # preenchido à mão, como no antigo
        "",
    ]


def montar_planilha(anotacoes) -> bytes:
    """Anotações despachadas (com cadete__turma, autor e despacho__punicao carregados)."""
    planilha = Workbook()
    aba = planilha.active
    aba.title = ABA

    aba.append([titulo for titulo, _ in COLUNAS])
    for anotacao in anotacoes:
        aba.append(linha(anotacao))

    for indice, (_, largura) in enumerate(COLUNAS, start=1):
        aba.column_dimensions[aba.cell(row=1, column=indice).column_letter].width = largura
    for celula in aba[1]:
        celula.font = _FONTE_CABECALHO
        celula.fill = _FUNDO_CABECALHO
        celula.alignment = _ALINHAMENTO_CABECALHO
    for linha_planilha in aba.iter_rows(min_row=2):
        for celula in linha_planilha:
            celula.border = _BORDA
            celula.alignment = _ALINHAMENTO_DADOS

    # Novidade em relação ao antigo: a folha é impressa para os cadetes assinarem, então
    # sai em paisagem, cabendo na largura e com o cabeçalho repetido em cada página.
    aba.freeze_panes = "A2"
    aba.print_title_rows = "1:1"
    aba.page_setup.orientation = "landscape"
    aba.page_setup.fitToWidth = 1
    aba.page_setup.fitToHeight = 0
    aba.sheet_properties.pageSetUpPr.fitToPage = True

    saida = BytesIO()
    planilha.save(saida)
    return saida.getvalue()
