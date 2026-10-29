# MAPPA CFO

Sistema de anotações disciplinares dos cadetes do Curso de Formação de Oficiais da PM: registro de anotações, despacho pelo comandante e geração do mappa para ciência e cumprimento.

Esta é a versão 2.0, reescrita do zero a partir do sistema antigo (Django + templates, já desligado).

## Documentação

- [docs/NORTE.md](docs/NORTE.md) — o que o sistema faz, diagnóstico do legado, arquitetura alvo e roteiro por fases.
- [docs/plano/](docs/plano/README.md) — passo a passo de cada fase, com conceitos, testes manuais e critérios de pronto.

## Estado atual

Fase 1 — fundação: Postgres + API Django em containers, health check e CI.

## Rodando localmente

Pré-requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/), [just](https://github.com/casey/just) e, para rodar ferramentas fora do container, [uv](https://docs.astral.sh/uv/).

```powershell
copy .env.example .env   # troque DJANGO_SECRET_KEY e as senhas
just up
```

- API: http://localhost:8000/api/health deve responder `{"status": "ok"}`
- Documentação interativa: http://localhost:8000/api/docs

| Comando | O que faz |
| --- | --- |
| `just up` / `just down` | Sobe (com rebuild) / derruba os containers; o banco fica no volume `pgdata` |
| `just logs` | Logs da api |
| `just test` | pytest dentro do container (`just test -k health` repassa argumentos) |
| `just lint` / `just fmt` | Confere / corrige com ruff |
| `just migrate`, `just shell`, `just psql` | Django e Postgres dentro dos containers |

`docker compose down -v` apaga também o volume do banco.

## Dados legados

Os backups do sistema antigo ficam em `backups/legacy/`, que é ignorado pelo git e precisa continuar assim: são dados pessoais de cadetes (LGPD).

| Arquivo | Conteúdo |
| --- | --- |
| `backup_22_10.dump` | Dump do Postgres de produção em 22/10/2026 (formato custom, restaurar com `pg_restore`) |
| `anotacao_data.tar.gz` | Planilhas de mappa exportadas (`media/exportacoes`), de 22/10/2026 |
| `anotacao_cfo_backup.sql` | Dump SQL antigo, de 19/01/2025 |
