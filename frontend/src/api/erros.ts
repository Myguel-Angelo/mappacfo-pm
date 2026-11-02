// Erros da API como classes: as telas fazem narrowing com instanceof em vez de olhar status.

export type CorpoErro = {
  detail?: unknown;
  codigo?: string | null;
  erros?: string[] | null;
};

export class ErroApi extends Error {
  readonly status: number;
  readonly codigo: string | null;
  readonly erros: string[];

  constructor(status: number, corpo: CorpoErro, mensagemPadrao = "Erro inesperado.") {
    super(typeof corpo.detail === "string" ? corpo.detail : mensagemPadrao);
    this.name = new.target.name;
    this.status = status;
    this.codigo = corpo.codigo ?? null;
    this.erros = corpo.erros ?? [];
  }
}

/** 401: sem sessão ou sessão expirada. */
export class NaoAutenticado extends ErroApi {}

/** 403: sem a permissão (ou falha de CSRF). */
export class SemPermissao extends ErroApi {}

/** 403 troca_senha_pendente: o usuário precisa trocar a senha antes de usar o resto. */
export class TrocaSenhaPendente extends ErroApi {}

/** 400: regra de negócio ou validação da API; a mensagem vai para o formulário. */
export class RegraViolada extends ErroApi {}

/** 404: inclui anotação de outro cadete (a API não revela que existe). */
export class NaoEncontrado extends ErroApi {}

/** 429: login bloqueado pelo limite de tentativas. */
export class LoginBloqueado extends ErroApi {}

type ItemValidacao = { loc?: unknown[]; msg?: string };

/** 422: erro de schema do Ninja. `campos` mapeia o último item de `loc` para a mensagem. */
export class ErroValidacao extends ErroApi {
  readonly campos: Record<string, string>;

  constructor(status: number, corpo: CorpoErro) {
    super(status, {}, "Confira os campos do formulário.");
    this.campos = {};
    if (Array.isArray(corpo.detail)) {
      for (const item of corpo.detail as ItemValidacao[]) {
        const campo = item.loc?.at(-1);
        if (typeof campo === "string" && item.msg) this.campos[campo] = item.msg;
      }
    }
  }
}

/** API fora do ar, erro 5xx ou resposta que não é JSON (ex.: proxy sem o Django). */
export class ErroRede extends ErroApi {
  constructor(status = 0) {
    super(
      status,
      {},
      "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.",
    );
  }
}

export function erroDaResposta(status: number, corpo: CorpoErro): ErroApi {
  if (status === 400) return new RegraViolada(status, corpo);
  if (status === 401) return new NaoAutenticado(status, corpo, "Sua sessão expirou.");
  if (status === 403 && corpo.codigo === "troca_senha_pendente")
    return new TrocaSenhaPendente(status, corpo);
  if (status === 403) return new SemPermissao(status, corpo, "Sem permissão para esta ação.");
  if (status === 404) return new NaoEncontrado(status, corpo, "Não encontrado.");
  if (status === 422) return new ErroValidacao(status, corpo);
  if (status === 429) return new LoginBloqueado(status, corpo);
  if (status >= 500) return new ErroRede(status);
  return new ErroApi(status, corpo);
}

/** Mensagem para mostrar ao usuário a partir de qualquer erro capturado. */
export function mensagemDeErro(erro: unknown): string {
  if (erro instanceof ErroApi) return erro.message;
  return "Erro inesperado. Tente de novo.";
}
