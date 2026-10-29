from .base import *  # noqa: F403

# Fixo: em produção o debug não pode ser ligado pelo ambiente.
DEBUG = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS, proxy (Caddy) e CSRF_TRUSTED_ORIGINS entram na fase 8.
