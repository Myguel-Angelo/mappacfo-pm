import { ChevronLeft, ChevronRight } from "lucide-react";

import type { StatusAnotacao, TipoAnotacao, Turma } from "@/api/tipos";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ROTULO_STATUS, ROTULO_TIPO } from "@/lib/formato";
import { cn } from "@/lib/utils";

// Peças das telas de anotações: selos, select nativo, tabela que vira cartões e paginação.

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

/** <select> nativo com o visual do Input: no celular abre o seletor do sistema. */
export function SelectNativo({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-lg border border-input bg-card px-2.5 text-base font-normal outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive md:text-sm",
        className,
      )}
      {...props}
    />
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
};

/**
 * Tabela no desktop; abaixo de md cada linha vira um cartão e cada célula mostra o
 * título da coluna ao lado (data-label). Um só DOM para os dois tamanhos.
 */
export function TabelaResponsiva<T>({
  itens,
  colunas,
  chave,
  legenda,
}: {
  itens: T[];
  colunas: Coluna<T>[];
  chave: (item: T) => React.Key;
  legenda: string;
}) {
  return (
    <table className="w-full border-separate border-spacing-0 text-sm">
      <caption className="sr-only">{legenda}</caption>
      <thead className="max-md:sr-only">
        <tr>
          {colunas.map((coluna) => (
            <th
              key={coluna.titulo}
              scope="col"
              className="bg-primary px-3 py-2 text-left font-bold text-primary-foreground first:rounded-tl-lg last:rounded-tr-lg"
            >
              {coluna.titulo}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {itens.map((item) => (
          <tr
            key={chave(item)}
            className="bg-card max-md:mb-3 max-md:block max-md:rounded-lg max-md:border max-md:p-3 max-md:shadow-sm"
          >
            {colunas.map((coluna) => (
              <td
                key={coluna.titulo}
                data-label={coluna.titulo}
                className={cn(
                  "border-b border-border px-3 py-2 align-top",
                  "max-md:flex max-md:gap-3 max-md:border-0 max-md:px-0 max-md:py-1",
                  "max-md:before:w-28 max-md:before:shrink-0 max-md:before:font-bold max-md:before:content-[attr(data-label)]",
                  coluna.className,
                )}
              >
                <div className="min-w-0 flex-1 break-words">{coluna.celula(item)}</div>
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Paginacao({
  pagina,
  total,
  porPagina = 50,
  onChange,
}: {
  pagina: number;
  total: number;
  porPagina?: number;
  onChange: (pagina: number) => void;
}) {
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  if (paginas === 1) return null;
  return (
    <nav aria-label="Paginação" className="flex items-center justify-center gap-3">
      <Button
        variant="outline"
        onClick={() => onChange(pagina - 1)}
        disabled={pagina <= 1}
        aria-label="Página anterior"
      >
        <ChevronLeft aria-hidden />
      </Button>
      <span className="text-sm">
        Página {pagina} de {paginas}
      </span>
      <Button
        variant="outline"
        onClick={() => onChange(pagina + 1)}
        disabled={pagina >= paginas}
        aria-label="Próxima página"
      >
        <ChevronRight aria-hidden />
      </Button>
    </nav>
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
