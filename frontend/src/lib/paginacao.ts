import { useState } from "react";

/** Itens por página: o mesmo NINJA_PAGINATION_PER_PAGE da API, para as listas baterem. */
export const POR_PAGINA = 20;

/**
 * Paginação no navegador, para listas que a API devolve inteiras. Mudar `filtro` (busca,
 * turma...) volta para a página 1; se a lista encolher, a página fica na última que existe.
 */
export function usePaginaLocal<T>(itens: T[], filtro: string = "") {
  const [estado, setEstado] = useState({ filtro, pagina: 1 });
  const paginas = Math.max(1, Math.ceil(itens.length / POR_PAGINA));
  const pagina = Math.min(estado.filtro === filtro ? estado.pagina : 1, paginas);

  return {
    itens: itens.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA),
    pagina,
    total: itens.length,
    irPara: (destino: number) => setEstado({ filtro, pagina: destino }),
  };
}
