# ADR 0002 — Encerrar as sessões de um usuário pelo painel

- **Status:** aceita
- **Data:** 02/11/2026
- **Contexto no roteiro:** NORTE, seção 5; implementação na fase 6 ([plano](../plano/06-painel-administrativo.md), passo 2)

## Contexto

O painel administrativo precisa derrubar as sessões abertas de um usuário em dois casos: quando a senha dele é redefinida (pode ter vazado) e quando ele é desativado (saiu do curso). O plano listava duas opções:

| Opção | A favor | Contra |
| --- | --- | --- |
| Apagar as linhas de `Session` cujo `get_decoded()["_auth_user_id"]` é o usuário | Explícito | Precisa decodificar todas as sessões do banco a cada reset; código próprio para manter |
| Contador de versão de sessão no usuário | Barato | Campo e middleware próprios |
| **O que o Django já faz** | Nenhum código novo | Depende de entender o mecanismo |

O Django guarda na sessão um hash derivado do hash da senha (`HASH_SESSION_KEY`, de `get_session_auth_hash()`). A cada requisição, `django.contrib.auth.get_user()` compara esse valor com o do usuário no banco; se a senha mudou, a sessão é descartada e o usuário vira anônimo. E o `ModelBackend.get_user()` não devolve usuário com `is_active=False`.

## Decisão

Não há código específico para encerrar sessões:

- **Resetar a senha** chama `set_password()` com a senha temporária nova. Todas as sessões abertas daquele usuário deixam de valer na próxima requisição (a API responde 401 e o frontend volta ao login).
- **Desativar** grava `is_active=False`. A sessão continua no banco, mas não autentica mais ninguém.

Os dois comportamentos têm teste (`tests/test_painel_usuarios.py`), para uma mudança futura de backend de autenticação ou de `SESSION_ENGINE` não quebrar isso sem aviso.

## Consequências

- Simples e sem custo: nada percorre a tabela de sessões.
- As linhas de sessão antigas continuam no banco até expirar; `clearsessions` (fase 7, automações) as remove.
- Se um dia for preciso "derrubar sessões" sem trocar a senha nem desativar, a opção do contador de versão continua disponível.
