from django.db import migrations

from core.migracoes import dar_permissoes, tirar_permissoes

# "Cadete com permissão de anotar" do sistema antigo = grupo Cadete + permissão individual
# anotacoes.anotar, dada pelo painel (fase 6).
GRUPOS = {
    "Oficial": ["anotar", "ver_anotacoes"],
    "Comandante": ["anotar", "ver_anotacoes", "despachar", "exportar"],
}

PUNICOES = ["Pernoite", "Revista"]


def avancar(apps, schema_editor):
    dar_permissoes(apps, GRUPOS, "anotacoes")
    TipoPunicao = apps.get_model("anotacoes", "TipoPunicao")
    for nome in PUNICOES:
        TipoPunicao.objects.get_or_create(nome=nome)


def voltar(apps, schema_editor):
    tirar_permissoes(apps, GRUPOS, "anotacoes")


class Migration(migrations.Migration):
    dependencies = [
        ("anotacoes", "0001_initial"),
        ("contas", "0002_grupos"),
    ]

    operations = [migrations.RunPython(avancar, voltar)]
