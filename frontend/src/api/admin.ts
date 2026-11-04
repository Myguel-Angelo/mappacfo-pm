import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type {
  AdminAuditoriaPagina,
  AdminImportacao,
  AdminPunicao,
  AdminResultadoImportacao,
  AdminTentativa,
  AdminTurma,
  AdminUsuario,
} from "@/api/tipos";
import type { components } from "@/api/schema";
import { POR_PAGINA } from "@/lib/paginacao";

type S = components["schemas"];

// Chaves de cache do painel: escritas invalidam o prefixo da área afetada.
const chaves = {
  usuarios: ["admin", "usuarios"] as const,
  turmas: ["admin", "turmas"] as const,
  punicoes: ["admin", "punicoes"] as const,
  auditoria: ["admin", "auditoria"] as const,
  acessos: ["admin", "acessos"] as const,
  bloqueios: ["admin", "bloqueios"] as const,
};

function querystring(filtros: Record<string, string | number | boolean | undefined>) {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(filtros)) {
    if (valor !== undefined && valor !== "") params.set(chave, String(valor));
  }
  const texto = params.toString();
  return texto ? `?${texto}` : "";
}

/** Toda escrita do painel pode mudar a auditoria e, em geral, as listas de turmas/cadetes. */
function useEscritaAdmin<V, R>(chamada: (variaveis: V) => Promise<R>, afeta: readonly string[][]) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: chamada,
    onSuccess: () => {
      for (const chave of [...afeta, chaves.auditoria]) {
        void queryClient.invalidateQueries({ queryKey: chave });
      }
    },
  });
}

// Usuários

export type FiltrosUsuarios = {
  busca?: string;
  grupo?: string;
  turma_id?: number;
  ativo?: boolean;
  page?: number;
};

export function useAdminUsuarios(filtros: FiltrosUsuarios) {
  return useQuery({
    queryKey: [...chaves.usuarios, filtros],
    queryFn: ({ signal }) =>
      api<S["PagedAdminUsuarioOut"]>(
        `/admin/usuarios${querystring({ ...filtros, page_size: POR_PAGINA })}`,
        { signal },
      ),
    placeholderData: keepPreviousData,
  });
}

export type DadosUsuario = {
  numerica: string;
  nome: string;
  email: string;
  turma_id: number | null;
  grupos: string[];
  anotar: boolean;
};

const afetaUsuarios = [[...chaves.usuarios], [...chaves.turmas], ["cadetes"]];

export function useCriarUsuario() {
  return useEscritaAdmin(
    (dados: DadosUsuario) =>
      api<{ usuario: AdminUsuario; senha_temporaria: string }>("/admin/usuarios", {
        method: "POST",
        body: dados,
      }),
    afetaUsuarios,
  );
}

export function useEditarUsuario() {
  return useEscritaAdmin(
    ({ id, ...dados }: Partial<Omit<DadosUsuario, "numerica">> & { id: number }) =>
      api<AdminUsuario>(`/admin/usuarios/${id}`, { method: "PATCH", body: dados }),
    afetaUsuarios,
  );
}

export function useDefinirAtivo() {
  return useEscritaAdmin(
    ({ id, ativo }: { id: number; ativo: boolean }) =>
      api<AdminUsuario>(`/admin/usuarios/${id}/${ativo ? "reativar" : "desativar"}`, {
        method: "POST",
      }),
    afetaUsuarios,
  );
}

export type AcaoEmLote = "desativar" | "reativar" | "permitir_anotar" | "retirar_anotar";

/** Tudo ou nada; devolve quantos mudaram de fato. Mudar de turma é useMoverCadetes. */
export function useUsuariosEmLote() {
  return useEscritaAdmin(
    (dados: { usuario_ids: number[]; acao: AcaoEmLote }) =>
      api<{ quantidade: number }>("/admin/usuarios/lote", { method: "POST", body: dados }),
    afetaUsuarios,
  );
}

export function useResetarSenha() {
  return useEscritaAdmin(
    (id: number) =>
      api<{ senha_temporaria: string }>(`/admin/usuarios/${id}/resetar-senha`, {
        method: "POST",
      }),
    [[...chaves.usuarios], [...chaves.bloqueios]],
  );
}

// Turmas

export function useAdminTurmas() {
  return useQuery({
    queryKey: chaves.turmas,
    queryFn: ({ signal }) => api<AdminTurma[]>("/admin/turmas", { signal }),
  });
}

const afetaTurmas = [[...chaves.turmas], [...chaves.usuarios], ["turmas"], ["cadetes"]];

export function useSalvarTurma() {
  return useEscritaAdmin(
    ({ id, ...dados }: { id?: number; nome?: string; ano_ingresso?: number; ativa?: boolean }) =>
      id === undefined
        ? api<AdminTurma>("/admin/turmas", { method: "POST", body: dados })
        : api<AdminTurma>(`/admin/turmas/${id}`, { method: "PATCH", body: dados }),
    afetaTurmas,
  );
}

export function useMoverCadetes() {
  return useEscritaAdmin(
    (dados: { cadete_ids: number[]; destino_id: number }) =>
      api<{ quantidade: number }>("/admin/turmas/mover", { method: "POST", body: dados }),
    afetaTurmas,
  );
}

export function useFormarTurma() {
  return useEscritaAdmin(
    (id: number) => api<{ quantidade: number }>(`/admin/turmas/${id}/formar`, { method: "POST" }),
    afetaTurmas,
  );
}

// Tipos de punição

export function useAdminPunicoes() {
  return useQuery({
    queryKey: chaves.punicoes,
    queryFn: ({ signal }) => api<AdminPunicao[]>("/admin/punicoes", { signal }),
  });
}

export function useSalvarPunicao() {
  return useEscritaAdmin(
    ({ id, ...dados }: { id?: number; nome?: string; ativo?: boolean }) =>
      id === undefined
        ? api<AdminPunicao>("/admin/punicoes", { method: "POST", body: dados })
        : api<AdminPunicao>(`/admin/punicoes/${id}`, { method: "PATCH", body: dados }),
    [[...chaves.punicoes], ["punicoes"]],
  );
}

// Importação

export function useCriarPrevia() {
  return useMutation({
    mutationFn: ({
      arquivo,
      atualizar_existentes,
      criar_turmas,
    }: {
      arquivo: File;
      atualizar_existentes: boolean;
      criar_turmas: boolean;
    }) => {
      const formulario = new FormData();
      formulario.append("arquivo", arquivo);
      formulario.append("atualizar_existentes", String(atualizar_existentes));
      formulario.append("criar_turmas", String(criar_turmas));
      return api<AdminImportacao>("/admin/importacoes", { method: "POST", body: formulario });
    },
  });
}

export function useConfirmarImportacao() {
  return useEscritaAdmin(
    (id: string) =>
      api<AdminResultadoImportacao>(`/admin/importacoes/${id}/confirmar`, { method: "POST" }),
    afetaTurmas,
  );
}

// Auditoria e acessos

export type FiltrosAuditoria = {
  inicio?: string;
  fim?: string;
  tipo?: string;
  page?: number;
};

export function useAuditoria(filtros: FiltrosAuditoria) {
  return useQuery({
    queryKey: [...chaves.auditoria, filtros],
    queryFn: ({ signal }) =>
      api<AdminAuditoriaPagina>(
        `/admin/auditoria${querystring({ ...filtros, page_size: POR_PAGINA })}`,
        { signal },
      ),
    placeholderData: keepPreviousData,
  });
}

export function useAcessos(filtros: { numerica?: string; page?: number }) {
  return useQuery({
    queryKey: [...chaves.acessos, filtros],
    queryFn: ({ signal }) =>
      api<S["PagedAdminAcessoOut"]>(
        `/admin/acessos${querystring({ ...filtros, page_size: POR_PAGINA })}`,
        { signal },
      ),
    placeholderData: keepPreviousData,
  });
}

export function useBloqueios() {
  return useQuery({
    queryKey: chaves.bloqueios,
    queryFn: ({ signal }) => api<AdminTentativa[]>("/admin/bloqueios", { signal }),
  });
}

export function useLiberarBloqueio() {
  return useEscritaAdmin(
    (numerica: string) =>
      api<{ quantidade: number }>(`/admin/bloqueios/${encodeURIComponent(numerica)}/liberar`, {
        method: "POST",
      }),
    [[...chaves.bloqueios]],
  );
}
