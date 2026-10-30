import { ErroRede, erroDaResposta, type CorpoErro } from "@/api/erros";

const METODOS_SEGUROS = new Set(["GET", "HEAD", "OPTIONS"]);

export function lerCookie(nome: string): string | undefined {
  const prefixo = `${nome}=`;
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(prefixo))
    ?.slice(prefixo.length);
}

/** Garante o cookie csrftoken (o Django só o envia quando alguém pede o token). */
export async function garantirCsrf(): Promise<void> {
  if (lerCookie("csrftoken")) return;
  await fetch("/api/auth/csrf", { credentials: "same-origin" });
}

type Opcoes = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
};

/**
 * Chama a API pelo caminho relativo (/api/...), sempre na mesma origem.
 * O token CSRF é lido do cookie a cada chamada: o login gira o token.
 */
export async function api<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const metodo = opcoes.method ?? "GET";
  const headers = new Headers({ Accept: "application/json" });
  if (opcoes.body !== undefined) headers.set("Content-Type", "application/json");
  if (!METODOS_SEGUROS.has(metodo)) {
    await garantirCsrf();
    headers.set("X-CSRFToken", lerCookie("csrftoken") ?? "");
  }

  let resp: Response;
  try {
    resp = await fetch(`/api${caminho}`, {
      method: metodo,
      headers,
      body: opcoes.body === undefined ? undefined : JSON.stringify(opcoes.body),
      credentials: "same-origin",
      signal: opcoes.signal,
    });
  } catch (erro) {
    if (erro instanceof DOMException && erro.name === "AbortError") throw erro;
    throw new ErroRede();
  }

  if (resp.status === 204) return undefined as T;

  const corpo = await lerJson(resp);
  if (corpo === undefined) throw new ErroRede(resp.status);
  if (!resp.ok) throw erroDaResposta(resp.status, corpo as CorpoErro);
  return corpo as T;
}

async function lerJson(resp: Response): Promise<unknown> {
  if (!resp.headers.get("Content-Type")?.includes("application/json")) return undefined;
  try {
    return await resp.json();
  } catch {
    return undefined;
  }
}
