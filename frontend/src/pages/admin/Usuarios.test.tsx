import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route } from "react-router";
import { beforeEach, expect, test } from "vitest";

import type { AdminUsuario } from "@/api/tipos";
import { RotaProtegida } from "@/auth/RotaProtegida";
import { Usuarios } from "@/pages/admin/Usuarios";
import { servidor } from "@/test/servidor";
import { renderizar, usuario } from "@/test/utils";

const novo: AdminUsuario = {
  id: 9,
  numerica: "4001",
  nome: "Novo Cadete",
  email: "",
  perfil: "Cadete",
  turma: { id: 1, nome: "CFO I" },
  grupos: ["Cadete"],
  anotar: false,
  ativo: true,
  deve_trocar_senha: true,
  ultimo_acesso: null,
};

let corpos: unknown[];

beforeEach(() => {
  document.cookie = "csrftoken=abc";
  corpos = [];
  servidor.use(
    http.get("/api/auth/me", () =>
      HttpResponse.json(
        usuario({
          numerica: "admin",
          turma: null,
          grupos: ["Administrador"],
          permissoes: ["contas.gerenciar_usuarios"],
        }),
      ),
    ),
    http.get("/api/admin/usuarios", () => HttpResponse.json({ items: [], count: 0 })),
    http.get("/api/admin/turmas", () =>
      HttpResponse.json([
        { id: 1, nome: "CFO I", ano_ingresso: 2026, ativa: true, total_cadetes: 0 },
      ]),
    ),
    http.post("/api/admin/usuarios", async ({ request }) => {
      corpos.push(await request.json());
      return HttpResponse.json(
        { usuario: novo, senha_temporaria: "abcd-efgh-jkmn" },
        { status: 201 },
      );
    }),
  );
});

function abrir() {
  renderizar(
    <Route
      path="/admin/usuarios"
      element={
        <RotaProtegida permissao="contas.gerenciar_usuarios">
          <Usuarios />
        </RotaProtegida>
      }
    />,
    { em: "/admin/usuarios" },
  );
}

test("cadete sem turma nao e enviado", async () => {
  abrir();
  await userEvent.click(await screen.findByRole("button", { name: "Novo usuário" }));
  const dialogo = screen.getByRole("dialog");
  await userEvent.type(within(dialogo).getByLabelText("Numérica (login)"), "4001");
  await userEvent.type(within(dialogo).getByLabelText("Nome completo"), "Novo Cadete");

  await userEvent.click(within(dialogo).getByRole("button", { name: "Criar e gerar senha" }));

  expect(await within(dialogo).findByText("Cadete precisa de uma turma.")).toBeInTheDocument();
  expect(corpos).toEqual([]);
});

test("cria e mostra a senha temporaria uma unica vez", async () => {
  abrir();
  await userEvent.click(await screen.findByRole("button", { name: "Novo usuário" }));
  const dialogo = screen.getByRole("dialog");
  await userEvent.type(within(dialogo).getByLabelText("Numérica (login)"), "4001");
  await userEvent.type(within(dialogo).getByLabelText("Nome completo"), "Novo Cadete");
  await within(dialogo).findByRole("option", { name: "CFO I" });
  await userEvent.selectOptions(within(dialogo).getByLabelText("Turma"), "CFO I");

  await userEvent.click(within(dialogo).getByRole("button", { name: "Criar e gerar senha" }));

  expect(await screen.findByText("abcd-efgh-jkmn")).toBeInTheDocument();
  expect(corpos).toEqual([
    {
      numerica: "4001",
      nome: "Novo Cadete",
      email: "",
      turma_id: 1,
      grupos: ["Cadete"],
      anotar: false,
    },
  ]);
  await userEvent.click(screen.getByRole("button", { name: "Já anotei" }));
  expect(screen.queryByText("abcd-efgh-jkmn")).not.toBeInTheDocument();
});
