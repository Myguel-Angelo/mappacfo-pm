import type { components } from "@/api/schema";

// Nomes curtos para os schemas gerados da API (src/api/schema.d.ts, `just api-types`).
type S = components["schemas"];

export type Me = S["MeOut"];
export type Turma = S["TurmaOut"];
export type TurmaResumo = S["TurmaResumoOut"];
export type Cadete = S["CadeteOut"];
export type Punicao = S["PunicaoOut"];
export type Anotacao = S["AnotacaoOut"];
export type PaginaAnotacoes = S["PagedAnotacaoOut"];
export type Estatisticas = S["EstatisticasOut"];
export type TipoAnotacao = S["TipoAnotacao"];
export type StatusAnotacao = S["StatusAnotacao"];

export type Permissao =
  | "anotacoes.anotar"
  | "anotacoes.ver_anotacoes"
  | "anotacoes.despachar"
  | "anotacoes.exportar"
  | "contas.gerenciar_usuarios";
