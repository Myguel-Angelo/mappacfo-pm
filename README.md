# MAPPA CFO

Sistema de anotações disciplinares dos cadetes do Curso de Formação de Oficiais da PM: registro de anotações, despacho pelo comandante e geração do mappa para ciência e cumprimento.

Esta é a versão 2.0, reescrita do zero a partir do sistema antigo (Django + templates, já desligado).

## Documentação

- [docs/NORTE.md](docs/NORTE.md) — o que o sistema faz, diagnóstico do legado, arquitetura alvo e roteiro por fases.
- [docs/plano/](docs/plano/README.md) — passo a passo de cada fase, com conceitos, testes manuais e critérios de pronto.

## Estado atual

Fase 0 — repositório e dados legados. Ainda não há código.

## Dados legados

Os backups do sistema antigo ficam em `backups/legacy/`, que é ignorado pelo git e precisa continuar assim: são dados pessoais de cadetes (LGPD).

| Arquivo | Conteúdo |
| --- | --- |
| `backup_22_10.dump` | Dump do Postgres de produção em 22/10/2026 (formato custom, restaurar com `pg_restore`) |
| `anotacao_data.tar.gz` | Planilhas de mappa exportadas (`media/exportacoes`), de 22/10/2026 |
| `anotacao_cfo_backup.sql` | Dump SQL antigo, de 19/01/2025 |
