import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";

import { criarQueryClient } from "@/api/queryClient";
import type { Me } from "@/api/tipos";

export function usuario(dados: Partial<Me> = {}): Me {
  return {
    numerica: "1001",
    nome: "Cadete Teste",
    email: "",
    turma: { id: 1, nome: "CFO I" },
    perfil: "Cadete",
    grupos: ["Cadete"],
    permissoes: [],
    deve_trocar_senha: false,
    ...dados,
  };
}

/** Mostra a rota atual: os testes conferem redirecionamentos por ela. */
function RotaAtual() {
  return <output data-testid="rota">{useLocation().pathname}</output>;
}

/**
 * Renderiza com QueryClient novo (sem cache entre testes) e roteador em memória.
 * `rotas` são as telas do teste; as demais caem num marcador com o caminho.
 */
export function renderizar(rotas: React.ReactNode, { em = "/" }: { em?: string } = {}) {
  const queryClient = criarQueryClient();
  queryClient.setDefaultOptions({ queries: { retry: false } });
  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[em]}>
          <Routes>
            {rotas}
            <Route path="*" element={<p>Outra página</p>} />
          </Routes>
          <RotaAtual />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}
