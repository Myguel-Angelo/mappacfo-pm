from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

# O navegador fala com o Vite (localhost:5173), que repassa /api ao Django.
# O .env.example deixa a variável vazia (ela é obrigatória só em prod): vazio usa o padrão.
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[]) or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
