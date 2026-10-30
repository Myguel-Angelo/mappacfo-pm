# MAPPA CFO

Sistema de anotações disciplinares dos cadetes do Curso de Formação de Oficiais da PM: registro de anotações, despacho pelo comandante e geração do mappa para ciência e cumprimento.

Esta é a versão 2.0, reescrita do zero a partir do sistema antigo (Django + templates, já desligado).

## Documentação

- [docs/NORTE.md](docs/NORTE.md) — o que o sistema faz, diagnóstico do legado, arquitetura alvo e roteiro por fases.
- [docs/plano/](docs/plano/README.md) — passo a passo de cada fase, com conceitos, testes manuais e critérios de pronto.

## Estado atual

Fases 1 a 4: Postgres + API Django (contas, sessão com CSRF, anotações, despacho e compensação) e o frontend em React para cadete, oficial e comandante. Próxima: fase 5, mappa e arquivos.

## Rodando localmente

Pré-requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/), [just](https://github.com/casey/just) e, para rodar ferramentas fora do container, [uv](https://docs.astral.sh/uv/) (backend) e Node 24 com [pnpm](https://pnpm.io/) (frontend).

```powershell
copy .env.example .env   # troque DJANGO_SECRET_KEY e as senhas
just up
just migrate
docker compose exec api python manage.py seed_dev   # usuários e turmas de teste
```

- **App: http://localhost:5173** — o Vite (container `web`) serve o React e repassa `/api` ao Django, então tudo fica na mesma origem (cookie de sessão e CSRF sem CORS). O primeiro `just up` demora enquanto o container instala as dependências (`just web-logs`).
- API: http://localhost:8000/api/health deve responder `{"status": "ok"}`
- Documentação interativa: http://localhost:8000/api/docs

O `seed_dev` cria `comandante`, `oficial`, `cadete-anotador`, `admin` e os cadetes `1001`–`1006`, `2001`–`2006`, `3001`–`3006`, todos com a senha `Senha-dev-123`.

| Comando | O que faz |
| --- | --- |
| `just up` / `just down` | Sobe (com rebuild) / derruba os containers; o banco fica no volume `pgdata` |
| `just logs` | Logs da api |
| `just test` | pytest dentro do container (`just test -k health` repassa argumentos) |
| `just lint` / `just fmt` | Confere / corrige com ruff |
| `just migrate`, `just shell`, `just psql` | Django e Postgres dentro dos containers |
| `just web-logs` / `just web-sh` | Logs / shell do container do frontend |
| `just api-types` | Regenera `frontend/src/api/schema.d.ts` a partir do OpenAPI (rode quando a API mudar e commite; o CI confere) |

No frontend (`cd frontend`, com `pnpm install` no host para o editor e os testes):

| Comando | O que faz |
| --- | --- |
| `pnpm test` | Vitest + Testing Library, com a API simulada pelo MSW |
| `pnpm lint` / `pnpm typecheck` | oxlint (sem `any`) / TypeScript |
| `pnpm format` / `pnpm format:check` | Prettier |
| `pnpm build` | Build de produção em `dist/` (o `Dockerfile` faz o mesmo em container) |

O `node_modules` do container fica num volume próprio (Linux); o do host (Windows) não é usado por ele.

`docker compose down -v` apaga também o volume do banco.

## Dados legados

Os backups do sistema antigo ficam em `backups/legacy/`, que é ignorado pelo git e precisa continuar assim: são dados pessoais de cadetes (LGPD).

| Arquivo | Conteúdo |
| --- | --- |
| `backup_22_10.dump` | Dump do Postgres de produção em 22/10/2026 (formato custom, restaurar com `pg_restore`) |
| `anotacao_data.tar.gz` | Planilhas de mappa exportadas (`media/exportacoes`), de 22/10/2026 |
| `anotacao_cfo_backup.sql` | Dump SQL antigo, de 19/01/2025 |
