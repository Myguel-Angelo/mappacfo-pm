"""Importação de cadetes por planilha, em duas etapas: prévia e confirmação.

A prévia lê o arquivo, analisa cada linha contra o banco e guarda o resultado. A
confirmação refaz a análise (o banco pode ter mudado nesse meio-tempo) e grava tudo numa
transação só. Rodar a mesma planilha duas vezes não duplica nada: quem já existe vira
"ignorar" (ou "atualizar", se a opção estiver marcada e algo mudou).

Todos os criados numa importação recebem a mesma senha temporária (mais fácil de entregar
a uma turma inteira) e são obrigados a trocá-la no primeiro acesso.
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
from contas import nome_guerra as ng
from contas.models import GRUPO_CADETE, Turma
from core.erros import RegraViolada
from core.permissoes import exigir

Usuario = get_user_model()

TAMANHO_MAXIMO = 2 * 1024 * 1024  # 2 MB
LINHAS_MAXIMAS = 5000
COLUNAS_OBRIGATORIAS = ["numerica", "nome", "nome_guerra", "turma"]
COLUNAS = [*COLUNAS_OBRIGATORIAS, "email"]

_TRAVA_IMPORTACAO = 6_000_002

# Ações de cada linha na prévia
CRIAR, ATUALIZAR, IGNORAR, ERRO = "criar", "atualizar", "ignorar", "erro"


# Leitura


def _normalizar_cabecalho(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode()
    texto = texto.strip().lower().replace("-", "").replace(" ", "_")
    apelidos = {
        "e_mail": "email",
        "numero": "numerica",
        "nome_de_guerra": "nome_guerra",
        "guerra": "nome_guerra",
    }
    return apelidos.get(texto, texto)


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
    """Devolve [{"linha": n, "numerica", "nome", "nome_guerra", "turma", "email"}], sem as
    linhas vazias.

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
        raise RegraViolada("A planilha precisa das colunas numerica, nome, nome_guerra e turma.")
    indice = {coluna: cabecalho.index(coluna) for coluna in COLUNAS if coluna in cabecalho}

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
    # Dono de cada nome de guerra já cadastrado (pela chave sem acento/caixa/pontuação).
    chaves = [ng.chave(ng.limpar(linha.get("nome_guerra", ""))) for linha in linhas]
    donos_da_chave = dict(
        Usuario.objects.filter(chave_login__in=[c for c in chaves if c]).values_list(
            "chave_login", "numerica"
        )
    )
    existentes = {
        u.numerica.lower(): u
        for u in Usuario.objects.annotate(numerica_min=Lower("numerica"))
        .filter(numerica_min__in=[n.lower() for n in numericas])
        .select_related("turma")
        .prefetch_related("groups")
    }

    primeira_vez: dict[str, int] = {}
    guerra_primeira_vez: dict[str, int] = {}
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
        # O CAD que vier na planilha é só do login: guarda-se o nome de guerra puro.
        nome_guerra = ng.limpar(linha.get("nome_guerra", ""))
        chave = ng.chave(nome_guerra)

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
        if not chave:
            erros.append("Nome de guerra vazio.")
        elif len(nome_guerra) > 40:
            erros.append("Nome de guerra com mais de 40 caracteres.")
        elif chave in guerra_primeira_vez:
            primeira = guerra_primeira_vez[chave]
            erros.append(f"Nome de guerra repetido no arquivo (também na linha {primeira}).")
        else:
            guerra_primeira_vez[chave] = linha["linha"]
            dono = donos_da_chave.get(chave)
            if dono is not None and dono.lower() != numerica.lower():
                erros.append(f'O nome de guerra "{nome_guerra}" já é do usuário {dono}.')
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
                if existente.nome_guerra != nome_guerra:
                    mudancas.append(f"nome de guerra: {existente.nome_guerra} → {nome_guerra}")
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
        resultado.append(
            {
                **linha,
                "nome_guerra": nome_guerra,
                "acao": acao,
                "erros": erros,
                "mudancas": mudancas,
            }
        )
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
    """Grava a importação. Devolve o resumo com a senha temporária dos criados (a mesma
    para todos), que só existe nesta resposta."""
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
            {"linha": linha["linha"], **{c: linha.get(c, "") for c in COLUNAS}}
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

    senha = gerar_senha_temporaria()
    criados, atualizados, ignorados = [], 0, 0
    for linha in linhas:
        if linha["acao"] == CRIAR:
            usuario = Usuario.objects.create_user(
                numerica=linha["numerica"],
                password=senha,
                nome=linha["nome"],
                nome_guerra=linha["nome_guerra"],
                email=linha["email"],
                turma=turma_de(linha["turma"]),
                deve_trocar_senha=True,
            )
            usuario.groups.add(grupo_cadete)
            criados.append(
                {
                    "numerica": usuario.numerica,
                    "nome": usuario.nome,
                    "login": usuario.texto_login,
                    "turma": usuario.turma.nome,
                }
            )
        elif linha["acao"] == ATUALIZAR:
            usuario = Usuario.objects.select_for_update().get(numerica__iexact=linha["numerica"])
            usuario.nome = linha["nome"]
            usuario.nome_guerra = linha["nome_guerra"]
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
    return {
        "criados": criados,
        "senha_temporaria": senha if criados else None,
        "atualizados": atualizados,
        "ignorados": ignorados,
    }
