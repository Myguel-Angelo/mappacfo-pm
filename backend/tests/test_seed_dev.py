import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from contas.models import Usuario


@pytest.mark.django_db
def test_seed_dev_cria_um_usuario_de_cada_perfil(settings):
    settings.DEBUG = True

    call_command("seed_dev", cadetes=2)
    call_command("seed_dev", cadetes=2)  # idempotente

    assert Usuario.objects.get(numerica="comandante").has_perm("anotacoes.despachar")
    assert Usuario.objects.get(numerica="cadete-anotador").has_perm("anotacoes.anotar")
    assert Usuario.objects.cadetes().count() == 3 * 2 + 1


@pytest.mark.django_db
def test_seed_dev_nao_roda_sem_debug(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError):
        call_command("seed_dev")
