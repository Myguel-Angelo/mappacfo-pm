from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from faker import Faker

from contas.models import Turma, Usuario

SENHA = "Senha-dev-123"


class Command(BaseCommand):
    help = "Cria turmas e um usuário de cada perfil para testar à mão (só com DEBUG)."

    def add_arguments(self, parser):
        parser.add_argument("--cadetes", type=int, default=6, help="cadetes por turma")

    @transaction.atomic
    def handle(self, *args, cadetes, **options):
        if not settings.DEBUG:
            raise CommandError("seed_dev só roda com DEBUG=True.")

        fake = Faker("pt_BR")
        Faker.seed(42)
        turmas = [
            Turma.objects.get_or_create(nome=nome, defaults={"ano_ingresso": ano})[0]
            for nome, ano in [("CFO I", 2026), ("CFO II", 2025), ("CFO III", 2024)]
        ]

        def usuario(numerica, nome, grupo, turma=None):
            u, criado = Usuario.objects.get_or_create(
                numerica=numerica, defaults={"nome": nome, "turma": turma}
            )
            if criado:
                u.set_password(SENHA)
                u.deve_trocar_senha = False
                u.save()
            u.groups.add(Group.objects.get(name=grupo))
            return u

        usuario("comandante", "Cap Comandante Dev", "Comandante")
        usuario("oficial", "Ten Oficial Dev", "Oficial")
        usuario("admin", "Administrador Dev", "Administrador")
        for t, turma in enumerate(turmas, start=1):
            for n in range(1, cadetes + 1):
                usuario(f"{t}{n:03d}", fake.name(), "Cadete", turma)

        anotador = usuario("cadete-anotador", "Cadete Anotador Dev", "Cadete", turmas[-1])
        anotador.user_permissions.add(
            Permission.objects.get(content_type__app_label="anotacoes", codename="anotar")
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Usuários: comandante, oficial, admin, cadete-anotador e cadetes 1001.. "
                f"(numérica = login), senha {SENHA}"
            )
        )
