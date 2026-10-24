# ADR 0001 — Frontend em React + TypeScript + Vite

- **Status:** aceita
- **Data:** 23/10/2026
- **Contexto no roteiro:** NORTE, seções 2 e 4; implementação na [Fase 4]

## Contexto

O sistema antigo renderizava as telas com templates do Django e jQuery. Funcionava, mas a lógica de interface ficava espalhada entre templates e scripts soltos, sem tipos e sem testes, e a experiência no celular (onde a maioria dos cadetes usa o sistema) era fraca.

A versão 2.0 tem dois objetivos que pesam nesta escolha:

1. Uma interface melhor, com estados claros de carregando, vazio e erro, e que funcione bem em 360 px de largura.
2. Servir de estudo de frontend moderno para o desenvolvedor.

O backend já está decidido: uma API em Django + Django Ninja, que publica um schema OpenAPI. A autenticação será por cookie de sessão + CSRF, sem token no `localStorage`, o que exige que navegador, frontend e API fiquem no mesmo domínio.

Alternativas consideradas:

| Opção | A favor | Contra |
| --- | --- | --- |
| Templates Django + jQuery (como hoje) | Nenhum container a mais, já conhecido | Repete os problemas do sistema antigo; nenhum aprendizado novo |
| HTMX + Alpine.js sobre templates | Pouco JavaScript, sessão e CSRF triviais, um deploy só | Entrega menos aprendizado de frontend; acopla as telas às views do Django e dificulta separar API e interface |
| **React + TypeScript + Vite (SPA)** | Ecossistema maduro, tipos ponta a ponta a partir do OpenAPI, testável com Vitest, alinhado ao objetivo de estudo | Mais código, um container a mais, curva de aprendizado |

## Decisão

O frontend será uma SPA em **React + TypeScript**, com build pelo **Vite**, consumindo a API Django Ninja.

- **Roteamento:** React Router.
- **Estado do servidor:** TanStack Query (cache e invalidação após mutações).
- **Formulários:** React Hook Form + Zod.
- **Componentes:** Tailwind + shadcn/ui, instalando só o que as telas usam.
- **Tipos da API:** gerados do OpenAPI com `openapi-typescript` e commitados.
- **Mesmo domínio:** em dev, o Vite repassa `/api` para o Django; em produção, o Caddy serve o build estático e repassa `/api`. O navegador nunca fala com outra origem, então sessão e CSRF funcionam sem CORS.
- **Pacotes:** `pnpm`, com lockfile versionado.

## Consequências

**Positivas**

- Interface e API ficam separadas: a API pode ser testada sozinha (pelo `/api/docs`) e reaproveitada por outros clientes no futuro.
- Tipos gerados do OpenAPI fazem uma mudança na API quebrar o build do frontend, em vez de quebrar em produção.
- Componentes e formulários testáveis com Vitest + Testing Library.
- Cumpre o objetivo de estudo: componentes, estado, roteamento no cliente, TypeScript.

**Negativas**

- Um container a mais (`web`) no compose de dev e uma etapa de build no deploy.
- Mais código e mais dependências para manter atualizadas (Dependabot ou Renovate).
- Risco de duplicar regras de negócio no frontend. Mitigação: a API é sempre a barreira real de permissão e validação; o frontend só esconde o que o usuário não pode usar e espelha a validação para dar feedback.
- Regenerar os tipos sempre que a API mudar. Mitigação: checagem no CI.

**O que fica proibido por esta decisão**

- Chamar a API por outra origem (`http://localhost:8000`) a partir do navegador.
- Guardar sessão ou dados do usuário em `localStorage`; a fonte é sempre `/api/auth/me`.
