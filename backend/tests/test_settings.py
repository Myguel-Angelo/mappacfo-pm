import importlib

import config.settings.base
import config.settings.prod


def test_settings_sem_debug_em_prod(monkeypatch):
    # Mesmo com DJANGO_DEBUG=True no ambiente, prod tem que desligar o debug.
    monkeypatch.setenv("DJANGO_DEBUG", "True")
    importlib.reload(config.settings.base)
    prod = importlib.reload(config.settings.prod)

    assert prod.DEBUG is False
