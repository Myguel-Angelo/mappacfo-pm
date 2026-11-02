from collections import Counter

from ninja import Schema

import config.api  # noqa: F401  (importa todas as rotas e schemas)

APPS = ("config", "core", "contas", "anotacoes")


def _subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _subclasses(sub)


def test_nomes_de_schema_sao_unicos():
    # O OpenAPI identifica schemas pelo nome da classe: dois "TurmaOut" diferentes viram um
    # só, e os tipos gerados do frontend ficam errados sem nenhum erro.
    nomes = Counter(
        cls.__name__ for cls in set(_subclasses(Schema)) if cls.__module__.startswith(APPS)
    )

    assert [nome for nome, n in nomes.items() if n > 1] == []


def test_me_descreve_a_turma_resumida(client):
    schema = client.get("/api/openapi.json").json()["components"]["schemas"]
    ref = schema["MeOut"]["properties"]["turma"]["anyOf"][0]["$ref"]

    assert set(schema[ref.split("/")[-1]]["properties"]) == {"id", "nome"}
