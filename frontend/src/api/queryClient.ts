import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { ErroRede, NaoAutenticado, TrocaSenhaPendente } from "@/api/erros";

export const CHAVE_SESSAO = ["sessao"] as const;

/**
 * Erros que valem para o app inteiro, venham de query ou de mutação:
 * - 401: a sessão acabou; a sessão vira null e a RotaProtegida manda para /login.
 * - troca_senha_pendente: recarrega /auth/me, que traz deve_trocar_senha e leva a /trocar-senha.
 */
export function criarQueryClient() {
  const queryClient: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError: (erro) => tratarErroGlobal(queryClient, erro) }),
    mutationCache: new MutationCache({ onError: (erro) => tratarErroGlobal(queryClient, erro) }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // Só vale tentar de novo quando o problema é rede/servidor; 4xx não muda sozinho.
        retry: (tentativas, erro) => erro instanceof ErroRede && tentativas < 1,
      },
    },
  });
  return queryClient;
}

function tratarErroGlobal(queryClient: QueryClient, erro: Error) {
  if (erro instanceof NaoAutenticado) {
    queryClient.setQueryData(CHAVE_SESSAO, null);
  } else if (erro instanceof TrocaSenhaPendente) {
    void queryClient.invalidateQueries({ queryKey: CHAVE_SESSAO });
  }
}
