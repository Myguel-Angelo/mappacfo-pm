set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# Lista os comandos
default:
    @just --list

# Sobe tudo (rebuild se algo mudou)
up:
    docker compose up -d --build

# Derruba os containers (os volumes ficam)
down:
    docker compose down

logs:
    docker compose logs -f api

migrate:
    docker compose exec api python manage.py migrate

makemigrations:
    docker compose exec api python manage.py makemigrations

shell:
    docker compose exec api python manage.py shell

psql:
    docker compose exec db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'

test *args:
    docker compose exec api pytest {{args}}

lint:
    docker compose exec api ruff check .
    docker compose exec api ruff format --check .

# Corrige o que o ruff consegue corrigir sozinho
fmt:
    docker compose exec api ruff check --fix .
    docker compose exec api ruff format .
