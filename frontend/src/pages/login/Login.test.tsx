import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route } from "react-router";
import { beforeEach, expect, test } from "vitest";

import { Login } from "@/pages/login/Login";
import { servidor } from "@/test/servidor";
import { renderizar, usuario } from "@/test/utils";

beforeEach(() => {
  document.cookie = "csrftoken=token-do-cookie";
  servidor.use(
    http.get("/api/auth/me", () => HttpResponse.json({ detail: "Unauthorized" }, { status: 401 })),
  );
});

async function entrar(numerica = "1001", senha = "Senha-dev-123") {
  const usuarioEvento = userEvent.setup();
  renderizar(<Route path="/login" element={<Login />} />, { em: "/login" });
  await usuarioEvento.type(await screen.findByLabelText("Numérica"), numerica);
  await usuarioEvento.type(screen.getByLabelText("Senha"), senha);
  await usuarioEvento.click(screen.getByRole("button", { name: "Entrar" }));
}

test("campos vazios mostram os erros sem chamar a api", async () => {
  const usuarioEvento = userEvent.setup();
  renderizar(<Route path="/login" element={<Login />} />, { em: "/login" });

  await usuarioEvento.click(await screen.findByRole("button", { name: "Entrar" }));

  expect(screen.getByText("Informe a numérica.")).toBeInTheDocument();
  expect(screen.getByText("Informe a senha.")).toBeInTheDocument();
});

test("senha errada mostra a mensagem da api e limpa a senha", async () => {
  servidor.use(
    http.post("/api/auth/login", () =>
      HttpResponse.json({ detail: "Numérica ou senha incorreta." }, { status: 401 }),
    ),
  );

  await entrar("1001", "errada");

  expect(await screen.findByText("Numérica ou senha incorreta.")).toBeInTheDocument();
  expect(screen.getByLabelText("Senha")).toHaveValue("");
});

test("bloqueio do axes explica a espera", async () => {
  servidor.use(
    http.post("/api/auth/login", () =>
      HttpResponse.json(
        {
          detail: "Muitas tentativas de login. Aguarde 15 minutos e tente de novo.",
          codigo: "login_bloqueado",
        },
        { status: 429 },
      ),
    ),
  );

  await entrar();

  expect(await screen.findByText(/Aguarde 15 minutos/)).toBeInTheDocument();
});

test("sucesso manda o token csrf do cookie e vai para o inicio", async () => {
  let csrf: string | null = null;
  servidor.use(
    http.post("/api/auth/login", ({ request }) => {
      csrf = request.headers.get("X-CSRFToken");
      return HttpResponse.json(usuario());
    }),
  );

  await entrar();

  expect(await screen.findByTestId("rota")).toHaveTextContent(/^\/$/);
  expect(csrf).toBe("token-do-cookie");
});
