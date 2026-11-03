from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Busca de nomes sem acento no painel ("joao" acha "João")."""

    dependencies = []

    operations = [UnaccentExtension()]
