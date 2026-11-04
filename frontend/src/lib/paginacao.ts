import { useState } from "react";

/** Itens por página. As listas paginadas na API pedem este tamanho (page_size). */
export const POR_PAGINA = 20;

/**
 * Paginação no navegador, para listas que a API devolve inteiras. Mudar `filtro` (busca,
 * turma...) volta para a página 1; se a lista encolher, a página fica na última que existe.
 */
export function usePaginaLocal<T>(itens: T[], filtro: string = "") {
  const [estado, setEstado] = useState({ filtro, pagina: 1 });
  // Ajuste durante a renderização (padrão do React): o filtro mudou, a página guardada vira
  // 1. Só esconder a antiga traria ela de volta quando o filtro voltasse ao valor anterior.
  if (estado.filtro !== filtro) setEstado({ filtro, pagina: 1 });
  const paginas = Math.max(1, Math.ceil(itens.length / POR_PAGINA));
  const pagina = Math.min(estado.filtro === filtro ? estado.pagina : 1, paginas);

  return {
    itens: itens.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA),
    pagina,
    total: itens.length,
    irPara: (destino: number) => setEstado({ filtro, pagina: destino }),
  };
}
