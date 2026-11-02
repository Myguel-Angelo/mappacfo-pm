from datetime import datetime
from uuid import UUID

from ninja import Field, Schema

from contas.api import TurmaResumoOut

# Nomes com prefixo Admin: o OpenAPI identifica schemas pelo nome (tests/test_openapi.py).


class AdminUsuarioOut(Schema):
    id: int
    numerica: str
    nome: str
    email: str
    perfil: str
    turma: TurmaResumoOut | None
    grupos: list[str]
    anotar: bool  # permissão individual (cadete anotador)
    ativo: bool
    deve_trocar_senha: bool
    ultimo_acesso: datetime | None

    @staticmethod
    def resolve_grupos(obj):
        return sorted(g.name for g in obj.groups.all())

    @staticmethod
    def resolve_anotar(obj):
        return bool(obj.perm_anotar)

    @staticmethod
    def resolve_ativo(obj):
        return obj.is_active

    @staticmethod
    def resolve_ultimo_acesso(obj):
        return obj.last_login


class AdminUsuarioFiltros(Schema):
    busca: str | None = None
    grupo: str | None = None
    turma_id: int | None = None
    ativo: bool | None = None


class AdminUsuarioCriarIn(Schema):
    numerica: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=254)
    turma_id: int | None = None
    grupos: list[str] = []
    anotar: bool = False


class AdminUsuarioEditarIn(Schema):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    turma_id: int | None = None
    grupos: list[str] | None = None
    anotar: bool | None = None


class AdminUsuarioCriadoOut(Schema):
    usuario: AdminUsuarioOut
    senha_temporaria: str


class AdminSenhaOut(Schema):
    senha_temporaria: str


# Turmas


class AdminTurmaOut(Schema):
    id: int
    nome: str
    ano_ingresso: int
    ativa: bool
    total_cadetes: int  # cadetes ativos


class AdminTurmaIn(Schema):
    nome: str = Field(min_length=1, max_length=40)
    ano_ingresso: int


class AdminTurmaEditarIn(Schema):
    nome: str | None = Field(default=None, min_length=1, max_length=40)
    ano_ingresso: int | None = None
    ativa: bool | None = None


class AdminMoverIn(Schema):
    cadete_ids: list[int]
    destino_id: int


class AdminQuantidadeOut(Schema):
    quantidade: int


# Tipos de punição


class AdminPunicaoOut(Schema):
    id: int
    nome: str
    ativo: bool
    total_despachos: int


class AdminPunicaoIn(Schema):
    nome: str = Field(min_length=1, max_length=60)


class AdminPunicaoEditarIn(Schema):
    nome: str | None = Field(default=None, min_length=1, max_length=60)
    ativo: bool | None = None


# Importação de cadetes


class AdminLinhaImportacaoOut(Schema):
    linha: int
    numerica: str
    nome: str
    turma: str
    email: str
    acao: str  # criar | atualizar | ignorar | erro
    erros: list[str]
    mudancas: list[str]


class AdminTotaisImportacaoOut(Schema):
    criar: int
    atualizar: int
    ignorar: int
    erro: int


class AdminImportacaoOut(Schema):
    id: UUID
    nome_arquivo: str
    criada_em: datetime
    expira_em: datetime
    atualizar_existentes: bool
    criar_turmas: bool
    linhas: list[AdminLinhaImportacaoOut]
    totais: AdminTotaisImportacaoOut

    @staticmethod
    def resolve_totais(obj):
        from administracao.importacao import totais

        return totais(obj.linhas)


class AdminImportacaoOpcoesIn(Schema):
    atualizar_existentes: bool = False
    criar_turmas: bool = False


class AdminCadeteCriadoOut(Schema):
    numerica: str
    nome: str
    turma: str
    senha_temporaria: str


class AdminResultadoImportacaoOut(Schema):
    criados: list[AdminCadeteCriadoOut]
    atualizados: int
    ignorados: int
