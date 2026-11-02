import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route } from "react-router";
import { beforeEach, expect, test } from "vitest";

import type { Mappa, Me } from "@/api/tipos";
import { RotaProtegida } from "@/auth/RotaProtegida";
import { Mappas } from "@/pages/mappas/Mappas";
import { servidor } from "@/test/servidor";
import { renderizar, usuario } from "@/test/utils";

const mappa: Mappa = {
  id: 4,
  titulo: "MAPA N°014/2026",
  gerado_em: "2026-11-02T10:00:00-03:00",
  gerado_por: { id: 1, numerica: "comandante", nome: "Cap Comandante" },
  publicado: false,
  total_anotacoes: 12,
};

let corpos: unknown[];

beforeEach(() => {
  document.cookie = "csrftoken=abc";
  corpos = [];
  servidor.use(
    http.get("/api/mappas", () => HttpResponse.json([mappa])),
    http.patch("/api/mappas/4", async ({ request }) => {
      const corpo = (await request.json()) as { publicado: boolean };
      corpos.push(corpo);
      return HttpResponse.json({ ...mappa, publicado: corpo.publicado });
    }),
  );
});

function abrirComo(me: Me) {
  servidor.use(http.get("/api/auth/me", () => HttpResponse.json(me)));
  renderizar(
    <Route
      path="/mappas"
      element={
        <RotaProtegida>
          <Mappas />
        </RotaProtegida>
      }
    />,
    { em: "/mappas" },
  );
}

test("cadete so baixa: link autenticado, sem publicar", async () => {
  abrirComo(usuario());

  const link = await screen.findByRole("link", { name: "Baixar MAPA N°014/2026" });

  expect(link).toHaveAttribute("href", "/api/mappas/4/download");
  expect(screen.queryByRole("button", { name: /Publicar/ })).not.toBeInTheDocument();
  expect(screen.queryByText("Não publicado")).not.toBeInTheDocument();
});

test("quem exporta publica e a linha atualiza", async () => {
  abrirComo(
    usuario({ turma: null, perfil: "Oficial Comandante", permissoes: ["anotacoes.exportar"] }),
  );

  expect(await screen.findByText("Não publicado")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Publicar/ }));

  expect(await screen.findByText("Publicado")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Despublicar/ })).toBeInTheDocument();
  expect(corpos).toEqual([{ publicado: true }]);
});
