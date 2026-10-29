from .base import *  # noqa: F403
from .base import env

# Fixo: em produção o debug não pode ser ligado pelo ambiente.
DEBUG = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

# HSTS e proxy (Caddy) entram na fase 8.
