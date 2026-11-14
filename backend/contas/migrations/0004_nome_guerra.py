import re
import unicodedata

from django.db import migrations, models


def _chave(texto):
    # Cópia de contas.nome_guerra.chave do dia desta migração: a migração não pode mudar
    # de comportamento se a função mudar depois.
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c)).upper()
    return re.sub(r"[^A-Z0-9]", "", sem_acento) or None


def numerica_como_nome_guerra(apps, schema_editor):
    """Quem já existe entra com a numérica como nome de guerra (é única), até o painel
    preencher o de verdade: ninguém fica sem conseguir entrar."""
    Usuario = apps.get_model("contas", "Usuario")
    for usuario in Usuario.objects.all():
        usuario.nome_guerra = usuario.numerica
        usuario.chave_login = _chave(usuario.numerica)
        usuario.save(update_fields=["nome_guerra", "chave_login"])


class Migration(migrations.Migration):
    dependencies = [
        ("contas", "0003_historico"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="nome_guerra",
            field=models.CharField(default="", max_length=40, verbose_name="nome de guerra"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="historicalusuario",
            name="nome_guerra",
            field=models.CharField(default="", max_length=40, verbose_name="nome de guerra"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="usuario",
            name="chave_login",
            field=models.CharField(editable=False, max_length=40, null=True),
        ),
        migrations.RunPython(numerica_como_nome_guerra, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="usuario",
            name="chave_login",
            field=models.CharField(editable=False, max_length=40, null=True, unique=True),
        ),
    ]
