from datetime import datetime

from ninja import Field, Schema

from anotacoes.schemas import PessoaOut


class MappaOut(Schema):
    id: int
    titulo: str
    gerado_em: datetime
    gerado_por: PessoaOut
    publicado: bool
    total_anotacoes: int


class MappaIn(Schema):
    titulo: str = Field(min_length=1, max_length=120)


class PublicacaoIn(Schema):
    publicado: bool
