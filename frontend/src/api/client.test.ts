import { http, HttpResponse, type JsonBodyType } from "msw";
import { expect, test } from "vitest";

import { api } from "@/api/client";
import {
  ErroRede,
  ErroValidacao,
  NaoAutenticado,
  NaoEncontrado,
  RegraViolada,
  SemPermissao,
  TrocaSenhaPendente,
} from "@/api/erros";
import { servidor } from "@/test/servidor";

function responder(status: number, corpo: JsonBodyType) {
  servidor.use(http.post("/api/x", () => HttpResponse.json(corpo, { status })));
}

test.each([
  [400, { detail: "Regra", codigo: "regra_violada" }, RegraViolada],
  [401, { detail: "Unauthorized" }, NaoAutenticado],
  [403, { detail: "Sem permissão", codigo: "sem_permissao" }, SemPermissao],
  [403, { detail: "Troque", codigo: "troca_senha_pendente" }, TrocaSenhaPendente],
  [404, { detail: "Not Found" }, NaoEncontrado],
  [500, { detail: "erro" }, ErroRede],
])("status %i vira o erro certo", async (status, corpo, classe) => {
  document.cookie = "csrftoken=abc";
  responder(status, corpo);

  await expect(api("/x", { method: "POST" })).rejects.toBeInstanceOf(classe);
});

test("422 do ninja aponta o campo pelo ultimo item de loc", async () => {
  document.cookie = "csrftoken=abc";
  responder(422, {
    detail: [{ type: "string_too_short", loc: ["body", "dados", "motivo"], msg: "curto" }],
  });

  const erro = await api("/x", { method: "POST" }).catch((e: unknown) => e);

  expect(erro).toBeInstanceOf(ErroValidacao);
  expect((erro as ErroValidacao).campos).toEqual({ motivo: "curto" });
});

test("resposta que nao e json (proxy sem o django) vira erro de rede", async () => {
  servidor.use(http.get("/api/y", () => new HttpResponse("Bad Gateway", { status: 502 })));

  await expect(api("/y")).rejects.toBeInstanceOf(ErroRede);
});

test("sem cookie csrf pede o token antes de escrever", async () => {
  const ordem: string[] = [];
  servidor.use(
    http.get("/api/auth/csrf", () => {
      ordem.push("csrf");
      document.cookie = "csrftoken=novo";
      return HttpResponse.json({ csrftoken: "novo" });
    }),
    http.post("/api/x", ({ request }) => {
      ordem.push(`post ${request.headers.get("X-CSRFToken")}`);
      return HttpResponse.json({});
    }),
  );

  await api("/x", { method: "POST" });

  expect(ordem).toEqual(["csrf", "post novo"]);
});
