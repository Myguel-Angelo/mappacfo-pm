import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import { api } from "@/api/client";
import type {
  Anotacao,
  Cadete,
  Estatisticas,
  PaginaAnotacoes,
  Punicao,
  StatusAnotacao,
  TipoAnotacao,
  Turma,
} from "@/api/tipos";

// Chaves de cache: tudo que lista anotações começa com "anotacoes", para uma escrita
// invalidar todas as listas de uma vez.
export const chaves = {
  turmas: ["turmas"] as const,
  cadetes: (turmaId?: number) => ["cadetes", turmaId ?? "todas"] as const,
  punicoes: ["punicoes"] as const,
  estatisticas: ["estatisticas"] as const,
  anotacoes: ["anotacoes"] as const,
  minhas: ["anotacoes", "minhas"] as const,
  lista: (filtros: FiltrosAnotacoes) => ["anotacoes", "lista", filtros] as const,
};

export type FiltrosAnotacoes = {
  turma_id?: number;
  cadete_id?: number;
  status?: StatusAnotacao;
  tipo?: TipoAnotacao;
  page?: number;
};

function querystring(filtros: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(filtros)) {
    if (valor !== undefined && valor !== "") params.set(chave, String(valor));
  }
  const texto = params.toString();
  return texto ? `?${texto}` : "";
}

// Consultas

export function useTurmas() {
  return useQuery({
    queryKey: chaves.turmas,
    queryFn: ({ signal }) => api<Turma[]>("/turmas", { signal }),
    staleTime: 10 * 60_000,
  });
}

export function useCadetes(turmaId?: number) {
  return useQuery({
    queryKey: chaves.cadetes(turmaId),
    queryFn: ({ signal }) =>
      api<Cadete[]>(`/cadetes${querystring({ turma_id: turmaId })}`, { signal }),
    placeholderData: keepPreviousData,
  });
}

export function usePunicoes() {
  return useQuery({
    queryKey: chaves.punicoes,
    queryFn: ({ signal }) => api<Punicao[]>("/punicoes", { signal }),
    staleTime: 10 * 60_000,
  });
}

export function useEstatisticas(habilitado: boolean) {
  return useQuery({
    queryKey: chaves.estatisticas,
    queryFn: ({ signal }) => api<Estatisticas>("/estatisticas/semana", { signal }),
    enabled: habilitado,
  });
}

export function useMinhasAnotacoes() {
  return useQuery({
    queryKey: chaves.minhas,
    queryFn: ({ signal }) => api<Anotacao[]>("/anotacoes/minhas", { signal }),
  });
}

export function useAnotacoes(filtros: FiltrosAnotacoes, habilitado = true) {
  return useQuery({
    queryKey: chaves.lista(filtros),
    queryFn: ({ signal }) => api<PaginaAnotacoes>(`/anotacoes${querystring(filtros)}`, { signal }),
    placeholderData: keepPreviousData,
    enabled: habilitado,
  });
}

// Mutações: toda escrita devolve a anotação atualizada; as listas são recarregadas.

function invalidarAnotacoes(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: chaves.anotacoes });
  void queryClient.invalidateQueries({ queryKey: chaves.estatisticas });
}

function useEscrita<V>(chamada: (variaveis: V) => Promise<Anotacao>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: chamada,
    onSuccess: () => invalidarAnotacoes(queryClient),
  });
}

export function useCriarAnotacao() {
  return useEscrita((dados: { cadete_id: number; tipo: TipoAnotacao; motivo: string }) =>
    api<Anotacao>("/anotacoes", { method: "POST", body: dados }),
  );
}

export type DadosDespacho = { punicao_id: number; data_cumprimento: string };

export function useDespachar() {
  return useEscrita(({ id, ...dados }: DadosDespacho & { id: number }) =>
    api<Anotacao>(`/anotacoes/${id}/despacho`, { method: "POST", body: dados }),
  );
}

export function useEditarDespacho() {
  return useEscrita(({ id, ...dados }: DadosDespacho & { id: number }) =>
    api<Anotacao>(`/anotacoes/${id}/despacho`, { method: "PUT", body: dados }),
  );
}

export function useCompensar() {
  return useEscrita(({ id, negativa_id }: { id: number; negativa_id: number }) =>
    api<Anotacao>(`/anotacoes/${id}/compensar`, { method: "POST", body: { negativa_id } }),
  );
}

export function useArquivar() {
  return useEscrita((id: number) => api<Anotacao>(`/anotacoes/${id}/arquivar`, { method: "POST" }));
}

export function useAnular() {
  return useEscrita(({ id, justificativa }: { id: number; justificativa: string }) =>
    api<Anotacao>(`/anotacoes/${id}/anular`, { method: "POST", body: { justificativa } }),
  );
}

export function useMarcarCumprida() {
  return useEscrita((id: number) => api<Anotacao>(`/anotacoes/${id}/cumprida`, { method: "POST" }));
}
