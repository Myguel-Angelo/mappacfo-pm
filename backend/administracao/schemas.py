from datetime import datetime

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
