FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
RUN useradd --create-home app
WORKDIR /app

# Dependências antes do código: o cache desta camada só invalida quando o lock muda.
FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Dev: inclui pytest, ruff etc.; o código entra por bind mount (compose.override.yaml).
FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
COPY . .
USER app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS runtime
COPY --from=deps /opt/venv /opt/venv
COPY . .
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3"]
