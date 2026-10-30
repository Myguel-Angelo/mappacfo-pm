import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";

import type { Anotacao } from "@/api/tipos";
import { hojeIso } from "@/lib/formato";
import { DialogDespacho } from "@/pages/despachar/dialogos";
import { servidor } from "@/test/servidor";
import { renderizar } from "@/test/utils";

const anotacao: Anotacao = {
  id: 7,
  tipo: "negativa",
  status: "notificada",
  motivo: "Atraso na formatura",
  criada_em: "2026-10-29T10:00:00-03:00",
  cadete: { id: 3, numerica: "1001", nome: "Cadete Teste", turma: null },
  autor: { id: 2, numerica: "oficial", nome: "Ten Oficial", perfil: "Oficial" },
  despacho: null,
  compensada_com_id: null,
  motivo_anulacao: "",
  anulada_em: null,
};

let corpos: unknown[];

beforeEach(() => {
  document.cookie = "csrftoken=abc";
  corpos = [];
  servidor.use(
    http.get("/api/punicoes", () =>
      HttpResponse.json([
        { id: 1, nome: "Pernoite" },
        { id: 2, nome: "Revista" },
      ]),
    ),
    http.post("/api/anotacoes/7/despacho", async ({ request }) => {
      corpos.push(await request.json());
      return HttpResponse.json({ ...anotacao, status: "despachada" });
    }),
  );
});

function abrir(onClose = vi.fn()) {
  renderizar(<Route path="/" element={<DialogDespacho anotacao={anotacao} onClose={onClose} />} />);
  return onClose;
}

async function escolherPunicao() {
  const select = screen.getByLabelText("Punição");
  await screen.findByRole("option", { name: "Pernoite" });
  await userEvent.selectOptions(select, "Pernoite");
}

test("data de cumprimento e obrigatoria", async () => {
  abrir();
  await escolherPunicao();

  await userEvent.click(screen.getByRole("button", { name: "Despachar" }));

  expect(await screen.findByText("Informe a data de cumprimento.")).toBeInTheDocument();
  expect(corpos).toEqual([]);
});

test("data no passado nao passa", async () => {
  abrir();
  await escolherPunicao();
  await userEvent.type(screen.getByLabelText("Data de cumprimento"), "2020-01-01");

  await userEvent.click(screen.getByRole("button", { name: "Despachar" }));

  expect(
    await screen.findByText("A data de cumprimento não pode estar no passado."),
  ).toBeInTheDocument();
  expect(corpos).toEqual([]);
});

test("despacha com punicao e data e fecha", async () => {
  const onClose = abrir();
  await escolherPunicao();
  await userEvent.type(screen.getByLabelText("Data de cumprimento"), hojeIso());

  await userEvent.click(screen.getByRole("button", { name: "Despachar" }));

  await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
  expect(corpos).toEqual([{ punicao_id: 1, data_cumprimento: hojeIso() }]);
});

test("regra violada da api aparece no formulario", async () => {
  servidor.use(
    http.post("/api/anotacoes/7/despacho", () =>
      HttpResponse.json(
        { detail: "O cadete já tem uma punição nesta data.", codigo: "regra_violada" },
        { status: 400 },
      ),
    ),
  );
  const onClose = abrir();
  await escolherPunicao();
  await userEvent.type(screen.getByLabelText("Data de cumprimento"), hojeIso());

  await userEvent.click(screen.getByRole("button", { name: "Despachar" }));

  expect(await screen.findByText("O cadete já tem uma punição nesta data.")).toBeInTheDocument();
  expect(onClose).not.toHaveBeenCalled();
});
