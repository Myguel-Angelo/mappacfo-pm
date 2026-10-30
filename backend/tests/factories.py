from datetime import timedelta

import factory
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from factory.django import DjangoModelFactory, Password

from anotacoes.models import Anotacao, Despacho, TipoPunicao
from contas.models import Turma, Usuario

SENHA = "Senha-de-teste-42"


class TurmaFactory(DjangoModelFactory):
    class Meta:
        model = Turma
        django_get_or_create = ["nome"]

    nome = factory.Sequence(lambda n: f"CFO {n}")
    ano_ingresso = 2026


class UsuarioFactory(DjangoModelFactory):
    """UsuarioFactory(grupo="Cadete"), ou os traits cadete/oficial/comandante.

    `perms=["anotacoes.anotar"]` dá permissões individuais.
    """

    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    class Params:
        cadete = factory.Trait(grupo="Cadete", turma=factory.SubFactory(TurmaFactory))
        oficial = factory.Trait(grupo="Oficial")
        comandante = factory.Trait(grupo="Comandante")

    numerica = factory.Sequence(lambda n: f"{100000 + n}")
    nome = factory.Faker("name", locale="pt_BR")
    password = Password(SENHA)
    deve_trocar_senha = False
    grupo = None

    @classmethod
    def _create(cls, model_class, *args, grupo=None, **kwargs):
        usuario = super()._create(model_class, *args, **kwargs)
        if grupo:
            usuario.groups.add(Group.objects.get(name=grupo))
        return usuario

    @factory.post_generation
    def perms(obj, create, extracted, **kwargs):
        for perm in extracted or []:
            app_label, codename = perm.split(".")
            obj.user_permissions.add(
                Permission.objects.get(content_type__app_label=app_label, codename=codename)
            )


class TipoPunicaoFactory(DjangoModelFactory):
    class Meta:
        model = TipoPunicao
        django_get_or_create = ["nome"]

    nome = "Pernoite"


class AnotacaoFactory(DjangoModelFactory):
    class Meta:
        model = Anotacao

    tipo = Anotacao.Tipo.NEGATIVA
    motivo = factory.Faker("sentence", locale="pt_BR")
    cadete = factory.SubFactory(UsuarioFactory, cadete=True)
    autor = factory.SubFactory(UsuarioFactory, oficial=True)


class DespachoFactory(DjangoModelFactory):
    """Cria o despacho e deixa a anotação como despachada (sem passar pelo serviço)."""

    class Meta:
        model = Despacho

    anotacao = factory.SubFactory(AnotacaoFactory, status=Anotacao.Status.DESPACHADA)
    punicao = factory.SubFactory(TipoPunicaoFactory)
    data_cumprimento = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=1))
    despachado_por = factory.SubFactory(UsuarioFactory, comandante=True)
