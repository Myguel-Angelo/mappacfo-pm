import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route } from "react-router";
import { expect, test } from "vitest";

import type { Me } from "@/api/tipos";
import { RotaProtegida } from "@/auth/RotaProtegida";
import { servidor } from "@/test/servidor";
import { renderizar, usuario } from "@/test/utils";

function sessao(me: Me | null) {
  servidor.use(
    http.get("/api/auth/me", () =>
      me ? HttpResponse.json(me) : HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
    ),
  );
}

function renderizarDespachar() {
  return renderizar(
    <Route
      path="/despachar"
      element={
        <RotaProtegida permissao="anotacoes.despachar">
          <p>Tela de despacho</p>
        </RotaProtegida>
      }
    />,
    { em: "/despachar" },
  );
}

test("sem sessao vai para o login", async () => {
  sessao(null);

  renderizarDespachar();

  expect(await screen.findByText("Outra página")).toBeInTheDocument();
  expect(screen.getByTestId("rota")).toHaveTextContent("/login");
});

test("troca de senha pendente vai para /trocar-senha", async () => {
  sessao(usuario({ deve_trocar_senha: true, permissoes: ["anotacoes.despachar"] }));

  renderizarDespachar();

  expect(await screen.findByText("Outra página")).toBeInTheDocument();
  expect(screen.getByTestId("rota")).toHaveTextContent("/trocar-senha");
});

test("sem a permissao mostra acesso negado", async () => {
  sessao(usuario());

  renderizarDespachar();

  expect(await screen.findByText("Acesso negado")).toBeInTheDocument();
  expect(screen.queryByText("Tela de despacho")).not.toBeInTheDocument();
});

test("com a permissao mostra a tela", async () => {
  sessao(usuario({ permissoes: ["anotacoes.despachar"] }));

  renderizarDespachar();

  expect(await screen.findByText("Tela de despacho")).toBeInTheDocument();
});

test("api fora do ar mostra erro e tenta de novo", async () => {
  let chamadas = 0;
  servidor.use(
    http.get("/api/auth/me", () => {
      chamadas += 1;
      return chamadas === 1
        ? new HttpResponse("Bad Gateway", { status: 502 })
        : HttpResponse.json(usuario({ permissoes: ["anotacoes.despachar"] }));
    }),
  );

  renderizarDespachar();
  await userEvent.click(await screen.findByRole("button", { name: /Tentar de novo/ }));

  expect(await screen.findByText("Tela de despacho")).toBeInTheDocument();
});
