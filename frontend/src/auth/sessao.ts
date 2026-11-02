import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { NaoAutenticado } from "@/api/erros";
import { CHAVE_SESSAO } from "@/api/queryClient";
import type { Me, Permissao } from "@/api/tipos";

/** Sessão do usuário: a fonte é sempre /auth/me (nada em localStorage). null = deslogado. */
export function useSessao() {
  return useQuery({
    queryKey: CHAVE_SESSAO,
    queryFn: async (): Promise<Me | null> => {
      try {
        return await api<Me>("/auth/me");
      } catch (erro) {
        if (erro instanceof NaoAutenticado) return null;
        throw erro;
      }
    },
    staleTime: 5 * 60_000,
  });
}

/** Usuário logado, para telas dentro da RotaProtegida (que garante a sessão). */
export function useUsuario(): Me {
  const { data } = useSessao();
  if (!data) throw new Error("useUsuario fora de uma RotaProtegida");
  return data;
}

export function temPermissao(usuario: Me | null | undefined, permissao: Permissao) {
  return usuario?.permissoes.includes(permissao) ?? false;
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: { numerica: string; senha: string }) =>
      api<Me>("/auth/login", { method: "POST", body: dados }),
    onSuccess: (usuario) => {
      // Outro usuário pode ter usado o navegador antes: nada do cache anterior serve.
      queryClient.clear();
      queryClient.setQueryData(CHAVE_SESSAO, usuario);
    },
  });
}

export function useLogout() {
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    // Recarrega a página: nada da sessão anterior fica na memória (cache, formulários) e o
    // próximo login começa no início, não na última tela de quem saiu.
    onSettled: () => window.location.replace("/login"),
  });
}

export function useTrocarSenha() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: { senha_atual: string; nova_senha: string; confirmacao: string }) =>
      api<Me>("/auth/trocar-senha", { method: "POST", body: dados }),
    onSuccess: (usuario) => queryClient.setQueryData(CHAVE_SESSAO, usuario),
  });
}
