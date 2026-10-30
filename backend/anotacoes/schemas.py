from datetime import date, datetime

from ninja import Field, Schema

from anotacoes.models import Anotacao


class TurmaOut(Schema):
    id: int
    nome: str
    ano_ingresso: int


class PessoaOut(Schema):
    id: int
    numerica: str
    nome: str


class AutorOut(PessoaOut):
    perfil: str  # "Oficial Comandante", "Oficial", "Cadete": só para exibição


class CadeteOut(PessoaOut):
    turma: TurmaOut | None


class PunicaoOut(Schema):
    id: int
    nome: str


class DespachoOut(Schema):
    id: int
    punicao: PunicaoOut
    data_cumprimento: date
    despachado_por: PessoaOut
    despachado_em: datetime


class AnotacaoOut(Schema):
    id: int
    tipo: Anotacao.Tipo
    status: Anotacao.Status
    motivo: str
    criada_em: datetime
    cadete: CadeteOut
    autor: AutorOut
    despacho: DespachoOut | None
    # Id da outra anotação da compensação (a negativa, se esta é a positiva, e vice-versa).
    compensada_com_id: int | None
    motivo_anulacao: str
    anulada_em: datetime | None

    @staticmethod
    def resolve_despacho(obj):
        return getattr(obj, "despacho", None)

    @staticmethod
    def resolve_compensada_com_id(obj):
        if compensa := getattr(obj, "compensa", None):
            return compensa.negativa_id
        if compensada_por := getattr(obj, "compensada_por", None):
            return compensada_por.positiva_id
        return None


class AnotacaoIn(Schema):
    cadete_id: int
    tipo: Anotacao.Tipo
    motivo: str = Field(min_length=3, max_length=2000)


class AnotacaoFiltros(Schema):
    turma_id: int | None = None
    cadete_id: int | None = None
    status: Anotacao.Status | None = None
    tipo: Anotacao.Tipo | None = None


class DespachoIn(Schema):
    punicao_id: int
    data_cumprimento: date  # obrigatório: no sistema antigo, faltar a data dava erro 500


class CompensarIn(Schema):
    negativa_id: int


class AnularIn(Schema):
    justificativa: str = Field(min_length=5, max_length=2000)


class RankingOut(Schema):
    numerica: str
    nome: str
    total: int


class PorTipoOut(Schema):
    positivas: int
    negativas: int


class EstatisticasOut(Schema):
    inicio: date
    total: int
    por_tipo: PorTipoOut
    mais_anotaram: list[RankingOut]
    mais_anotados: list[RankingOut]
