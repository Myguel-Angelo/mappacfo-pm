import type { StatusAnotacao, TipoAnotacao } from "@/api/tipos";

const dataHora = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

/** "2026-10-30" → "30/10/2026", sem passar por Date (evita o deslocamento de fuso). */
export function formatarData(iso: string) {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

export function formatarDataHora(iso: string) {
  return dataHora.format(new Date(iso));
}

/** Data de hoje no fuso do navegador, no formato do <input type="date">. */
export function hojeIso() {
  const hoje = new Date();
  const mes = String(hoje.getMonth() + 1).padStart(2, "0");
  const dia = String(hoje.getDate()).padStart(2, "0");
  return `${hoje.getFullYear()}-${mes}-${dia}`;
}

export const ROTULO_STATUS: Record<StatusAnotacao, string> = {
  notificada: "Notificada",
  despachada: "Despachada",
  compensada: "Compensada",
  cumprida: "Cumprida",
  arquivada: "Arquivada",
  anulada: "Anulada",
};

export const ROTULO_TIPO: Record<TipoAnotacao, string> = {
  positiva: "Positiva",
  negativa: "Negativa",
};

/** "Oficial Comandante Fulano", como o sistema antigo mostrava quem anotou. */
export function pessoaComPerfil(pessoa: { nome: string; perfil?: string }) {
  return pessoa.perfil ? `${pessoa.perfil} ${pessoa.nome}` : pessoa.nome;
}
