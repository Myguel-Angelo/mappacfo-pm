import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route } from "react-router";
import { expect, test } from "vitest";

import type { Me } from "@/api/tipos";
import { RotaProtegida } from "@/auth/RotaProtegida";
import { Layout } from "@/components/Layout";
import { servidor } from "@/test/servidor";
import { renderizar, usuario } from "@/test/utils";

function abrirComo(me: Me, em = "/") {
  servidor.use(http.get("/api/auth/me", () => HttpResponse.json(me)));
  renderizar(
    <Route
      element={
        <RotaProtegida>
          <Layout />
        </RotaProtegida>
      }
    >
      <Route index element={<p>Início</p>} />
      <Route path="trocar-senha" element={<p>Trocar senha</p>} />
    </Route>,
    { em },
  );
}

test("perfil mostra nome e iniciais; alterar senha e sair ficam no menu dele", async () => {
  abrirComo(usuario({ nome: "Cap João da Silva" }));

  const perfil = await screen.findByRole("button", { name: "Menu de Cap João da Silva" });
  expect(perfil).toHaveTextContent("CS");
  expect(perfil).toHaveTextContent("Cap João da Silva");
  expect(screen.queryByRole("menuitem", { name: "Sair" })).not.toBeInTheDocument();

  await userEvent.click(perfil);
  expect(await screen.findByRole("menuitem", { name: "Sair" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("menuitem", { name: "Alterar senha" }));

  expect(screen.getByTestId("rota")).toHaveTextContent("/trocar-senha");
});

test("na troca de senha obrigatoria nao ha menu principal, so o perfil", async () => {
  abrirComo(usuario({ deve_trocar_senha: true }), "/trocar-senha");

  expect(await screen.findByRole("button", { name: /^Menu de/ })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Abrir menu" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /Minhas anotações/ })).not.toBeInTheDocument();
});
