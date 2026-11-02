import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { chaves as chavesAnotacoes } from "@/api/anotacoes";
import { api } from "@/api/client";
import type { Mappa } from "@/api/tipos";

const CHAVE_MAPPAS = ["mappas"] as const;

/**
 * Download por link comum (mesma origem: o cookie de sessão vai junto e a API decide).
 * O cliente api() só lida com JSON; buscar o .xlsx por fetch + blob não traria nada.
 */
export function urlDownload(mappa: Pick<Mappa, "id">) {
  return `/api/mappas/${mappa.id}/download`;
}

export function useMappas() {
  return useQuery({
    queryKey: CHAVE_MAPPAS,
    queryFn: ({ signal }) => api<Mappa[]>("/mappas", { signal }),
  });
}

export function useGerarMappa() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (titulo: string) => api<Mappa>("/mappas", { method: "POST", body: { titulo } }),
    onSuccess: () => {
      // As despachadas viram arquivadas: todas as listas de anotações mudam.
      void queryClient.invalidateQueries({ queryKey: chavesAnotacoes.anotacoes });
      void queryClient.invalidateQueries({ queryKey: CHAVE_MAPPAS });
    },
  });
}

export function usePublicarMappa() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, publicado }: { id: number; publicado: boolean }) =>
      api<Mappa>(`/mappas/${id}`, { method: "PATCH", body: { publicado } }),
    onSuccess: (mappa) => {
      queryClient.setQueryData<Mappa[]>(CHAVE_MAPPAS, (lista) =>
        lista?.map((m) => (m.id === mappa.id ? mappa : m)),
      );
    },
  });
}
