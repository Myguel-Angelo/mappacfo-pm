import { ChevronDown } from "lucide-react";
import { useId } from "react";

import type { StatusAnotacao, TipoAnotacao, Turma } from "@/api/tipos";
import { Badge } from "@/components/ui/badge";
import { ROTULO_STATUS, ROTULO_TIPO } from "@/lib/formato";
import { cn } from "@/lib/utils";

// Peças das telas de anotações: selos, select nativo e tabela que vira cartões.

export function SeloTipo({ tipo }: { tipo: TipoAnotacao }) {
  return (
    <Badge
      className={cn(
        "font-bold",
        tipo === "positiva" ? "bg-sucesso text-white" : "bg-destructive text-white",
      )}
    >
      {ROTULO_TIPO[tipo]}
    </Badge>
  );
}

const COR_STATUS: Record<StatusAnotacao, string> = {
  notificada: "bg-amber-100 text-amber-900",
  despachada: "bg-primary text-primary-foreground",
  compensada: "bg-secondary text-secondary-foreground",
  cumprida: "bg-green-100 text-green-900",
  arquivada: "bg-muted text-muted-foreground",
  anulada: "bg-red-100 text-red-900",
};

export function SeloStatus({ status }: { status: StatusAnotacao }) {
  return <Badge className={COR_STATUS[status]}>{ROTULO_STATUS[status]}</Badge>;
}

/**
 * <select> nativo com o visual do Input: no celular abre o seletor do sistema. A seta é
 * nossa (appearance-none): a do navegador fica colada na borda e muda de um para outro.
 */
export function SelectNativo({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <span className="relative block w-full">
      <select
        className={cn(
          "h-10 w-full appearance-none rounded-lg border border-input bg-card pr-9 pl-2.5 text-base font-normal outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive md:text-sm",
          className,
        )}
        {...props}
      />
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground"
      />
    </span>
  );
}

export function FiltroTurma({
  turmas,
  valor,
  onChange,
}: {
  turmas: Turma[] | undefined;
  valor: number | undefined;
  onChange: (turmaId: number | undefined) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm font-bold sm:w-56">
      Turma
      <SelectNativo
        value={valor ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
      >
        <option value="">Todas</option>
        {turmas?.map((turma) => (
          <option key={turma.id} value={turma.id}>
            {turma.nome}
          </option>
        ))}
      </SelectNativo>
    </label>
  );
}

export type Coluna<T> = {
  titulo: string;
  celula: (item: T) => React.ReactNode;
  className?: string;
  /** Coluna de botões: só a largura deles, numa linha a partir de lg (abaixo, quebram). */
  acoes?: boolean;
  /** Conteúdo do cabeçalho no lugar do título (o título segue como rótulo no celular). */
  cabecalho?: React.ReactNode;
};

/** Linhas marcáveis: as chaves marcadas ficam com quem usa a tabela (valem entre páginas). */
export type Selecao<T> = {
  marcados: ReadonlySet<React.Key>;
  onChange: (itens: T[], marcado: boolean) => void;
  rotulo: (item: T) => string;
};

/** Marca ou desmarca a página inteira; fica "alguns marcados" no meio do caminho. */
function CaixaPagina<T>({
  selecao,
  itens,
  chave,
  rotulo,
  id,
}: {
  selecao: Selecao<T>;
  itens: T[];
  chave: (item: T) => React.Key;
  rotulo?: string;
  id?: string;
}) {
  const marcadosNaPagina = itens.filter((item) => selecao.marcados.has(chave(item))).length;
  const todos = itens.length > 0 && marcadosNaPagina === itens.length;
  return (
    <input
      type="checkbox"
      id={id}
      aria-label={rotulo}
      className="size-4 align-middle accent-primary"
      checked={todos}
      // "Alguns marcados" só existe como propriedade do DOM, não como atributo.
      ref={(el) => {
        if (el) el.indeterminate = marcadosNaPagina > 0 && !todos;
      }}
      onChange={(e) => selecao.onChange(itens, e.target.checked)}
    />
  );
}

function colunaSelecao<T>(
  selecao: Selecao<T>,
  itens: T[],
  chave: (item: T) => React.Key,
): Coluna<T> {
  return {
    titulo: "Selecionar",
    className: "md:w-10",
    cabecalho: (
      <CaixaPagina
        selecao={selecao}
        itens={itens}
        chave={chave}
        rotulo="Selecionar todos desta página"
      />
    ),
    celula: (item) => (
      <input
        type="checkbox"
        aria-label={selecao.rotulo(item)}
        className="size-4 align-middle accent-primary"
        checked={selecao.marcados.has(chave(item))}
        onChange={(e) => selecao.onChange([item], e.target.checked)}
      />
    ),
  };
}

/**
 * Tabela no desktop; abaixo de md cada linha vira um cartão e cada célula mostra o
 * título da coluna ao lado (data-label). Um só DOM para os dois tamanhos.
 */
export function TabelaResponsiva<T>({
  itens,
  colunas,
  chave,
  legenda,
  selecao,
}: {
  itens: T[];
  colunas: Coluna<T>[];
  chave: (item: T) => React.Key;
  legenda: string;
  selecao?: Selecao<T>;
}) {
  const idMarcarPagina = useId();
  const todas = selecao ? [colunaSelecao(selecao, itens, chave), ...colunas] : colunas;
  return (
    // Se os botões numa linha não couberem (perto de lg), a tabela rola aqui, não a página.
    <div className="md:overflow-x-auto">
      {/* No celular o cabeçalho (com a caixa de marcar a página) vira só leitor de tela. */}
      {selecao && itens.length > 0 && (
        <div className="mb-3 flex items-center gap-2 text-sm font-bold md:hidden">
          <CaixaPagina selecao={selecao} itens={itens} chave={chave} id={idMarcarPagina} />
          <label htmlFor={idMarcarPagina}>Marcar todos desta página</label>
        </div>
      )}
      <table className="w-full border-separate border-spacing-0 text-sm">
        <caption className="sr-only">{legenda}</caption>
        <thead className="max-md:sr-only">
          <tr>
            {todas.map((coluna) => (
              <th
                key={coluna.titulo}
                scope="col"
                className="bg-primary px-3 py-2 text-left font-bold text-primary-foreground first:rounded-tl-lg last:rounded-tr-lg"
              >
                {coluna.cabecalho ?? coluna.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {itens.map((item) => (
            <tr
              key={chave(item)}
              className={cn(
                "bg-card max-md:mb-3 max-md:block max-md:rounded-lg max-md:border max-md:p-3 max-md:shadow-sm",
                selecao?.marcados.has(chave(item)) && "bg-accent max-md:border-primary",
              )}
            >
              {todas.map((coluna) => (
                <td
                  key={coluna.titulo}
                  data-label={coluna.titulo}
                  className={cn(
                    "border-b border-border px-3 py-2 align-middle",
                    "max-md:flex max-md:gap-3 max-md:border-0 max-md:px-0 max-md:py-1",
                    "max-md:before:w-28 max-md:before:shrink-0 max-md:before:font-bold max-md:before:content-[attr(data-label)]",
                    coluna.acoes && "md:w-px",
                    coluna.className,
                  )}
                >
                  <div
                    className={cn(
                      "min-w-0 flex-1 break-words",
                      coluna.acoes && "flex flex-wrap gap-2 lg:flex-nowrap",
                    )}
                  >
                    {coluna.celula(item)}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Titulo({ children, acao }: { children: React.ReactNode; acao?: React.ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h1 className="text-2xl font-bold text-primary">{children}</h1>
      {acao}
    </div>
  );
}
