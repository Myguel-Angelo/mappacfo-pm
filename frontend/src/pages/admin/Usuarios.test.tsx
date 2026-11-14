import { screen, waitFor, within } from "@testing-library/react";
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
  nome_guerra: "Novato",
  login: "CAD Novato",
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

test("marca varios e desativa em lote; a selecao some depois", async () => {
  const outro: AdminUsuario = { ...novo, id: 10, numerica: "4002", nome: "Outro Cadete" };
  const oficial: AdminUsuario = {
    ...novo,
    id: 11,
    numerica: "of1",
    nome: "Ten Oficial",
    grupos: ["Oficial"],
    turma: null,
  };
  servidor.use(
    http.get("/api/admin/usuarios", () =>
      HttpResponse.json({ items: [novo, outro, oficial], count: 3 }),
    ),
    http.post("/api/admin/usuarios/lote", async ({ request }) => {
      corpos.push(await request.json());
      return HttpResponse.json({ quantidade: 2 });
    }),
  );
  abrir();

  await userEvent.click(await screen.findByRole("checkbox", { name: "Selecionar Novo Cadete" }));
  await userEvent.click(screen.getByRole("checkbox", { name: "Selecionar Outro Cadete" }));
  const barra = screen.getByRole("region", { name: "Ações nos selecionados" });
  expect(barra).toHaveTextContent("2 selecionados");
  expect(within(barra).getByRole("button", { name: /Mudar turma/ })).toBeEnabled();

  // Com um oficial no meio, mudar de turma não vale para todos.
  await userEvent.click(screen.getByRole("checkbox", { name: "Selecionar Ten Oficial" }));
  expect(within(barra).getByRole("button", { name: /Mudar turma/ })).toBeDisabled();
  await userEvent.click(screen.getByRole("checkbox", { name: "Selecionar Ten Oficial" }));

  await userEvent.click(within(barra).getByRole("button", { name: /Desativar/ }));
  const dialogo = screen.getByRole("dialog");
  expect(dialogo).toHaveTextContent("4002 — Outro Cadete");
  await userEvent.click(within(dialogo).getByRole("button", { name: "Desativar (2)" }));

  // hidden: com o diálogo aberto o Radix esconde o resto da página dos leitores de tela.
  await waitFor(() =>
    expect(
      screen.queryByRole("region", { name: "Ações nos selecionados", hidden: true }),
    ).not.toBeInTheDocument(),
  );
  expect(corpos).toEqual([{ usuario_ids: [9, 10], acao: "desativar" }]);
});

test("marcar o cabecalho seleciona a pagina inteira", async () => {
  const outro: AdminUsuario = { ...novo, id: 10, numerica: "4002", nome: "Outro Cadete" };
  servidor.use(
    http.get("/api/admin/usuarios", () => HttpResponse.json({ items: [novo, outro], count: 2 })),
  );
  abrir();

  const todos = await screen.findByRole("checkbox", { name: "Selecionar todos desta página" });
  await userEvent.click(screen.getByRole("checkbox", { name: "Selecionar Novo Cadete" }));
  expect(todos).toHaveProperty("indeterminate", true);

  await userEvent.click(todos);
  expect(screen.getByRole("region", { name: "Ações nos selecionados" })).toHaveTextContent(
    "2 selecionados",
  );
  expect(todos).toBeChecked();
});
