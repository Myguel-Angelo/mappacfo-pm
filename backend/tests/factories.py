import factory
from factory.django import DjangoModelFactory, Password

from contas.models import Turma, Usuario

SENHA = "Senha-de-teste-42"


class TurmaFactory(DjangoModelFactory):
    class Meta:
        model = Turma
        django_get_or_create = ["nome"]

    nome = factory.Sequence(lambda n: f"CFO {n}")
    ano_ingresso = 2026


class UsuarioFactory(DjangoModelFactory):
    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    numerica = factory.Sequence(lambda n: f"{100000 + n}")
    nome = factory.Faker("name", locale="pt_BR")
    password = Password(SENHA)
    deve_trocar_senha = False
