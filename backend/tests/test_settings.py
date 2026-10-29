import importlib
import sys

import config.settings.base


def test_settings_sem_debug_em_prod(monkeypatch):
    # Mesmo com DJANGO_DEBUG=True no ambiente, prod tem que desligar o debug.
    monkeypatch.setenv("DJANGO_DEBUG", "True")
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "https://exemplo.test")
    importlib.reload(config.settings.base)
    sys.modules.pop("config.settings.prod", None)

    prod = importlib.import_module("config.settings.prod")

    assert prod.DEBUG is False
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
