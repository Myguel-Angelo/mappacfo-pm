import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, test } from "vitest";

import { Paginacao } from "@/components/paginacao";
import { usePaginaLocal } from "@/lib/paginacao";

function Controlada({ total, inicial = 1 }: { total: number; inicial?: number }) {
  const [pagina, setPagina] = useState(inicial);
  return <Paginacao pagina={pagina} total={total} onChange={setPagina} />;
}

test("uma pagina so nao mostra a paginacao", () => {
  render(<Controlada total={20} />);
  expect(screen.queryByRole("navigation", { name: "Paginação" })).not.toBeInTheDocument();
});

test("mostra o intervalo, pula paginas com reticencias e navega", async () => {
  render(<Controlada total={200} inicial={5} />);

  expect(screen.getByText("Mostrando 81–100 de 200")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Página 5" })).toHaveAttribute("aria-current", "page");
  // 1 … 4 5 6 … 10
  const numeros = screen.getAllByRole("button", { name: /^Página \d+$/ }).map((b) => b.textContent);
  expect(numeros).toEqual(["1", "4", "5", "6", "10"]);

  await userEvent.click(screen.getByRole("button", { name: "Última página" }));
  expect(screen.getByText("Mostrando 181–200 de 200")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Próxima página" })).toBeDisabled();
});

test("pagina local volta para a primeira quando o filtro muda", () => {
  const itens = Array.from({ length: 45 }, (_, i) => i);
  const { result, rerender } = renderHook(({ lista, filtro }) => usePaginaLocal(lista, filtro), {
    initialProps: { lista: itens, filtro: "" },
  });

  act(() => result.current.irPara(3));
  expect(result.current.itens).toEqual([40, 41, 42, 43, 44]);

  // A lista encolheu: fica na última página que existe.
  rerender({ lista: itens.slice(0, 30), filtro: "" });
  expect(result.current.pagina).toBe(2);

  rerender({ lista: itens, filtro: "joao" });
  expect(result.current.pagina).toBe(1);
  expect(result.current.itens).toHaveLength(20);
});
