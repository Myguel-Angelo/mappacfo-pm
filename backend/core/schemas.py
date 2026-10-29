from ninja import Schema


class ErroOut(Schema):
    detail: str
    codigo: str | None = None
    erros: list[str] | None = None
