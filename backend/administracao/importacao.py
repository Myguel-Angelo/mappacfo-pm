"""Importação de cadetes por planilha, em duas etapas: prévia e confirmação.

A prévia lê o arquivo, analisa cada linha contra o banco e guarda o resultado. A
confirmação refaz a análise (o banco pode ter mudado nesse meio-tempo) e grava tudo numa
transação só. Rodar a mesma planilha duas vezes não duplica nada: quem já existe vira
"ignorar" (ou "atualizar", se a opção estiver marcada e algo mudou).
"""

import csv
import io
import unicodedata

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection, transaction
from django.db.models.functions import Lower
from django.utils import timezone
from openpyxl import load_workbook

from administracao.models import ImportacaoCadetes
from administracao.usuarios import PERMISSAO, gerar_senha_temporaria
from contas.models import GRUPO_CADETE, Turma
from core.erros import RegraViolada
from core.permissoes import exigir

Usuario = get_user_model()

TAMANHO_MAXIMO = 2 * 1024 * 1024  # 2 MB
LINHAS_MAXIMAS = 5000
COLUNAS_OBRIGATORIAS = ["numerica", "nome", "turma"]

_TRAVA_IMPORTACAO = 6_000_002

# Ações de cada linha na prévia
CRIAR, ATUALIZAR, IGNORAR, ERRO = "criar", "atualizar", "ignorar", "erro"


# Leitura


def _normalizar_cabecalho(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode()
    texto = texto.strip().lower().replace("-", "").replace(" ", "_")
    return {"email": "email", "e_mail": "email", "numero": "numerica"}.get(texto, texto)


def _celula(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)  # 1001.0 do Excel vira "1001"
    return " ".join(str(valor).split())


def _ler_csv(conteudo: bytes) -> list[list]:
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("cp1252")  # CSV salvo pelo Excel brasileiro
    try:
        dialeto = csv.Sniffer().sniff(texto[:4096], delimiters=";,\t")
    except csv.Error:
        dialeto = csv.excel
        dialeto.delimiter = ";"
    return list(csv.reader(io.StringIO(texto), dialeto))


def _ler_xlsx(conteudo: bytes) -> list[list]:
    try:
        planilha = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - qualquer arquivo corrompido vira a mesma mensagem
        raise RegraViolada("Não foi possível ler a planilha. Envie um .xlsx ou .csv.") from None
    try:
        return [list(linha) for linha in planilha.active.iter_rows(values_only=True)]
    finally:
        planilha.close()


def ler_arquivo(nome: str, conteudo: bytes) -> list[dict]:
    """Devolve [{"linha": n, "numerica", "nome", "turma", "email"}], sem as linhas vazias.

    `linha` é o número da linha na planilha (cabeçalho = 1), para o oficial achar o erro.
    """
    if len(conteudo) > TAMANHO_MAXIMO:
        raise RegraViolada("O arquivo passa de 2 MB.")
    ehxlsx = nome.lower().endswith(".xlsx") or conteudo[:2] == b"PK"
    tabela = _ler_xlsx(conteudo) if ehxlsx else _ler_csv(conteudo)

    tabela = [[_celula(v) for v in linha] for linha in tabela]
    inicio = next((i for i, linha in enumerate(tabela) if any(linha)), None)
    if inicio is None:
        raise RegraViolada("A planilha está vazia.")
    cabecalho = [_normalizar_cabecalho(v) for v in tabela[inicio]]
    if any(c not in cabecalho for c in COLUNAS_OBRIGATORIAS):
        raise RegraViolada("A planilha precisa das colunas numerica, nome e turma.")
    indice = {
        coluna: cabecalho.index(coluna)
        for coluna in [*COLUNAS_OBRIGATORIAS, "email"]
        if coluna in cabecalho
    }

    linhas = []
    for numero, valores in enumerate(tabela[inicio + 1 :], start=inicio + 2):
        if not any(valores):
            continue
        linha = {"linha": numero, "email": ""}  # e-mail é opcional
        linha.update({c: valores[i] if i < len(valores) else "" for c, i in indice.items()})
        linhas.append(linha)
    if not linhas:
        raise RegraViolada("A planilha não tem nenhum cadete.")
    if len(linhas) > LINHAS_MAXIMAS:
        raise RegraViolada(f"A planilha passa de {LINHAS_MAXIMAS} linhas.")
    return linhas


# Análise


def analisar(linhas: list[dict], *, atualizar_existentes: bool, criar_turmas: bool) -> list[dict]:
    """Decide o que cada linha faz. Não grava nada."""
    turmas = {t.nome.lower(): t for t in Turma.objects.all()}
    numericas = [linha["numerica"] for linha in linhas if linha["numerica"]]
    # Sem diferenciar maiúsculas: "abc1" na planilha é o mesmo usuário "ABC1".
    existentes = {
        u.numerica.lower(): u
        for u in Usuario.objects.annotate(numerica_min=Lower("numerica"))
        .filter(numerica_min__in=[n.lower() for n in numericas])
        .select_related("turma")
        .prefetch_related("groups")
    }

    primeira_vez: dict[str, int] = {}
    resultado = []
    for linha in linhas:
        erros: list[str] = []
        mudancas: list[str] = []
        numerica, nome, turma_nome, email = (
            linha["numerica"],
            linha["nome"],
            linha["turma"],
            linha["email"],
        )

        if not numerica:
            erros.append("Numérica vazia.")
        elif numerica.lower() in primeira_vez:
            erros.append(
                f"Numérica repetida no arquivo (também na linha {primeira_vez[numerica.lower()]})."
            )
        else:
            primeira_vez[numerica.lower()] = linha["linha"]
        if len(numerica) > 20:
            erros.append("Numérica com mais de 20 caracteres.")
        if not nome:
            erros.append("Nome vazio.")
        if len(nome) > 120:
            erros.append("Nome com mais de 120 caracteres.")
        if email:
            try:
                validate_email(email)
            except ValidationError:
                erros.append("E-mail inválido.")

        turma = turmas.get(turma_nome.lower()) if turma_nome else None
        if not turma_nome:
            erros.append("Turma vazia.")
        elif turma is None and not criar_turmas:
            erros.append(f'Turma "{turma_nome}" não existe.')
        elif turma is not None and not turma.ativa:
            erros.append(f'Turma "{turma.nome}" está arquivada.')

        existente = existentes.get(numerica.lower()) if numerica else None
        if existente is not None and not erros:
            if not any(g.name == GRUPO_CADETE for g in existente.groups.all()):
                erros.append("A numérica pertence a um usuário que não é cadete.")
            else:
                if existente.nome != nome:
                    mudancas.append(f"nome: {existente.nome} → {nome}")
                if email and existente.email != email:
                    mudancas.append(f"e-mail: {existente.email or '(vazio)'} → {email}")
                turma_atual = existente.turma.nome if existente.turma else "(sem turma)"
                if turma_atual.lower() != turma_nome.lower():
                    mudancas.append(f"turma: {turma_atual} → {turma_nome}")
                if not existente.is_active:
                    mudancas.append("usuário desativado: reative pelo painel se for o caso")

        if erros:
            acao = ERRO
        elif existente is None:
            acao = CRIAR
        elif mudancas and atualizar_existentes:
            acao = ATUALIZAR
        else:
            acao = IGNORAR
        if acao == CRIAR and turma is None:
            mudancas.append(f'turma nova "{turma_nome}" será criada')
        resultado.append({**linha, "acao": acao, "erros": erros, "mudancas": mudancas})
    return resultado


def totais(linhas: list[dict]) -> dict:
    contagem = {CRIAR: 0, ATUALIZAR: 0, IGNORAR: 0, ERRO: 0}
    for linha in linhas:
        contagem[linha["acao"]] += 1
    return contagem


# Etapas


def criar_previa(
    admin, nome_arquivo: str, conteudo: bytes, *, atualizar_existentes: bool, criar_turmas: bool
):
    exigir(admin, PERMISSAO)
    linhas = ler_arquivo(nome_arquivo, conteudo)
    return ImportacaoCadetes.objects.create(
        criada_por=admin,
        nome_arquivo=nome_arquivo[:255],
        atualizar_existentes=atualizar_existentes,
        criar_turmas=criar_turmas,
        linhas=analisar(
            linhas, atualizar_existentes=atualizar_existentes, criar_turmas=criar_turmas
        ),
    )


@transaction.atomic
def confirmar(admin, importacao) -> dict:
    """Grava a importação. Devolve o resumo com as senhas temporárias dos criados, que só
    existem nesta resposta."""
    exigir(admin, PERMISSAO)
    importacao = ImportacaoCadetes.objects.select_for_update().get(pk=importacao.pk)
    if importacao.criada_por_id != admin.pk:
        raise RegraViolada("Esta prévia foi feita por outro administrador.")
    if importacao.confirmada_em is not None:
        raise RegraViolada("Esta importação já foi confirmada.")
    if importacao.expirada:
        raise RegraViolada("A prévia expirou (30 minutos). Envie a planilha de novo.")

    # O banco pode ter mudado desde a prévia: analisa de novo. A trava impede duas
    # confirmações ao mesmo tempo criando a mesma numérica.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_TRAVA_IMPORTACAO])
    linhas = analisar(
        [
            {c: linha[c] for c in ("linha", "numerica", "nome", "turma", "email")}
            for linha in importacao.linhas
        ],
        atualizar_existentes=importacao.atualizar_existentes,
        criar_turmas=importacao.criar_turmas,
    )
    if any(linha["acao"] == ERRO for linha in linhas):
        raise RegraViolada(
            "A planilha tem linhas com erro. Corrija e envie de novo; nada foi gravado."
        )

    grupo_cadete = Group.objects.get(name=GRUPO_CADETE)
    turmas = {t.nome.lower(): t for t in Turma.objects.all()}

    def turma_de(nome):
        if nome.lower() not in turmas:
            turmas[nome.lower()] = Turma.objects.create(
                nome=nome, ano_ingresso=timezone.localdate().year
            )
        return turmas[nome.lower()]

    criados, atualizados, ignorados = [], 0, 0
    for linha in linhas:
        if linha["acao"] == CRIAR:
            senha = gerar_senha_temporaria()
            usuario = Usuario.objects.create_user(
                numerica=linha["numerica"],
                password=senha,
                nome=linha["nome"],
                email=linha["email"],
                turma=turma_de(linha["turma"]),
                deve_trocar_senha=True,
            )
            usuario.groups.add(grupo_cadete)
            criados.append(
                {
                    "numerica": usuario.numerica,
                    "nome": usuario.nome,
                    "turma": usuario.turma.nome,
                    "senha_temporaria": senha,
                }
            )
        elif linha["acao"] == ATUALIZAR:
            usuario = Usuario.objects.select_for_update().get(numerica__iexact=linha["numerica"])
            usuario.nome = linha["nome"]
            if linha["email"]:
                usuario.email = linha["email"]
            usuario.turma = turma_de(linha["turma"])
            usuario._change_reason = f"Importação {importacao.nome_arquivo}"
            usuario.save()
            atualizados += 1
        else:
            ignorados += 1

    importacao.linhas = linhas
    importacao.confirmada_em = timezone.now()
    importacao.resumo = {
        "criados": len(criados),
        "atualizados": atualizados,
        "ignorados": ignorados,
    }
    importacao.save(update_fields=["linhas", "confirmada_em", "resumo"])
    return {"criados": criados, "atualizados": atualizados, "ignorados": ignorados}
