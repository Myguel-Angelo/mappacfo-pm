"""Planilhas .xlsx do painel: o modelo da importação de cadetes e a lista de logins de uma
importação. Só formatação (sem banco nem HTTP), no visual do sistema: cabeçalho na cor
primária com letra branca, colunas na largura certa e o cabeçalho fixo ao rolar.
"""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

ABA_CADETES = "Cadetes"

_COR_PRIMARIA = "134157"  # --primary do frontend
_FONTE_CABECALHO = Font(bold=True, color="FFFFFF")
_FUNDO_CABECALHO = PatternFill(
    start_color=_COR_PRIMARIA, end_color=_COR_PRIMARIA, fill_type="solid"
)
_FUNDO_LISTRA = PatternFill(start_color="EEF2F5", end_color="EEF2F5", fill_type="solid")
_FINA = Side(style="thin", color="C9D3DB")
_BORDA = Border(left=_FINA, right=_FINA, top=_FINA, bottom=_FINA)

# (cabeçalho, largura, explicação). O cabeçalho é o que a importação lê: não traduzir.
COLUNAS_MODELO = [
    ("numerica", 14, "Obrigatória. A numérica do cadete; não pode repetir."),
    ("nome", 40, "Obrigatório. Nome completo."),
    (
        "nome_guerra",
        22,
        'Obrigatório. É o login, sem o CAD (o cadete digita "CAD" + este nome). Não pode repetir.',
    ),
    ("turma", 14, 'Obrigatória. O nome da turma como está no sistema, ex.: "CFO I".'),
    ("email", 32, "Opcional."),
]

COLUNAS_LOGINS = [("Numérica", 14), ("Nome", 40), ("Login", 24), ("Turma", 14)]


def _tabela(aba, colunas: list[tuple[str, int]], linhas: list[list]) -> None:
    """Cabeçalho estilizado, linhas listradas com borda fina, filtro e cabeçalho fixo."""
    aba.append([titulo for titulo, _ in colunas])
    for linha in linhas:
        aba.append(linha)

    for indice, (_, largura) in enumerate(colunas, start=1):
        aba.column_dimensions[aba.cell(row=1, column=indice).column_letter].width = largura
    aba.row_dimensions[1].height = 22
    for celula in aba[1]:
        celula.font = _FONTE_CABECALHO
        celula.fill = _FUNDO_CABECALHO
        celula.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for numero, linha_planilha in enumerate(aba.iter_rows(min_row=2), start=2):
        for celula in linha_planilha:
            celula.border = _BORDA
            if numero % 2 == 1:
                celula.fill = _FUNDO_LISTRA

    aba.freeze_panes = "A2"
    aba.auto_filter.ref = aba.dimensions


def _bytes(planilha: Workbook) -> bytes:
    saida = BytesIO()
    planilha.save(saida)
    return saida.getvalue()


def modelo_importacao() -> bytes:
    """Aba Cadetes vazia para preencher (com a explicação de cada coluna num comentário do
    cabeçalho) e uma aba Instruções com um exemplo. A importação lê a aba Cadetes."""
    planilha = Workbook()
    aba = planilha.active
    aba.title = ABA_CADETES
    _tabela(aba, [(titulo, largura) for titulo, largura, _ in COLUNAS_MODELO], [])
    for celula, (_, _, explicacao) in zip(aba[1], COLUNAS_MODELO, strict=True):
        celula.comment = Comment(explicacao, "MAPPA", width=260, height=90)
    # Sem linha de dados, o filtro só atrapalharia quem cola a lista.
    aba.auto_filter.ref = None

    instrucoes = planilha.create_sheet("Instruções")
    instrucoes.column_dimensions["A"].width = 100
    instrucoes.append(["Como preencher"])
    instrucoes["A1"].font = Font(bold=True, size=14, color=_COR_PRIMARIA)
    for texto in [
        "Preencha a aba Cadetes, um cadete por linha, a partir da linha 2.",
        "Não mude os nomes das colunas (passe o mouse no cabeçalho para ver a explicação).",
        *(f"• {titulo}: {explicacao}" for titulo, _, explicacao in COLUNAS_MODELO),
        "Envie em Administração › Importar cadetes. Nada é gravado antes da prévia.",
        'Veja a aba "Exemplo" (ela não é importada).',
    ]:
        instrucoes.append([texto])
        instrucoes.cell(row=instrucoes.max_row, column=1).alignment = Alignment(wrap_text=True)
    exemplo = planilha.create_sheet("Exemplo")
    _tabela(
        exemplo,
        [(titulo, largura) for titulo, largura, _ in COLUNAS_MODELO],
        [
            ["1001", "Fulano de Tal", "Tal", "CFO I", "fulano@exemplo.com"],
            ["1002", "Beltrana da Silva", "Beltrana", "CFO I", ""],
        ],
    )
    planilha.active = 0
    return _bytes(planilha)


def logins_importacao(cadetes) -> bytes:
    """Lista para divulgar à turma: quem foi criado e com que texto entra. Sem senha."""
    planilha = Workbook()
    aba = planilha.active
    aba.title = "Logins"
    _tabela(
        aba,
        COLUNAS_LOGINS,
        [[c.numerica, c.nome, c.texto_login, c.turma.nome if c.turma else ""] for c in cadetes],
    )
    return _bytes(planilha)
