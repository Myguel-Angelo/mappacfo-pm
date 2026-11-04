import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { POR_PAGINA } from "@/lib/paginacao";

/** Páginas visíveis: a primeira, a última e uma de cada lado da atual; "…" no salto. */
function faixa(pagina: number, paginas: number): (number | "…")[] {
  const numeros = [...new Set([1, pagina - 1, pagina, pagina + 1, paginas])]
    .filter((n) => n >= 1 && n <= paginas)
    .sort((a, b) => a - b);
  return numeros.flatMap((n, i) => (i > 0 && n - numeros[i - 1] > 1 ? ["…" as const, n] : [n]));
}

export function Paginacao({
  pagina,
  total,
  porPagina = POR_PAGINA,
  onChange,
}: {
  pagina: number;
  total: number;
  porPagina?: number;
  onChange: (pagina: number) => void;
}) {
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  if (paginas === 1) return null;

  function ir(destino: number) {
    onChange(destino);
    // A lista nova começa no topo; sem isso, quem pagina pelo rodapé cai no fim dela.
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const inicio = (pagina - 1) * porPagina + 1;
  const fim = Math.min(pagina * porPagina, total);

  return (
    <nav
      aria-label="Paginação"
      className="flex flex-col items-center gap-2 sm:flex-row sm:justify-between"
    >
      <p className="text-sm text-muted-foreground">
        Mostrando {inicio}–{fim} de {total}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => ir(1)}
          disabled={pagina <= 1}
          aria-label="Primeira página"
        >
          <ChevronsLeft aria-hidden />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => ir(pagina - 1)}
          disabled={pagina <= 1}
          aria-label="Página anterior"
        >
          <ChevronLeft aria-hidden />
        </Button>
        {/* No celular os números não cabem: fica só "3 de 10". */}
        <span className="px-2 text-sm sm:hidden">
          {pagina} de {paginas}
        </span>
        <ul className="hidden items-center gap-1 sm:flex">
          {faixa(pagina, paginas).map((item, i) =>
            item === "…" ? (
              <li key={`salto-${i}`} aria-hidden className="px-1 text-muted-foreground">
                …
              </li>
            ) : (
              <li key={item}>
                <Button
                  variant={item === pagina ? "default" : "outline"}
                  size="icon-sm"
                  onClick={() => ir(item)}
                  aria-label={`Página ${item}`}
                  aria-current={item === pagina ? "page" : undefined}
                >
                  {item}
                </Button>
              </li>
            ),
          )}
        </ul>
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => ir(pagina + 1)}
          disabled={pagina >= paginas}
          aria-label="Próxima página"
        >
          <ChevronRight aria-hidden />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => ir(paginas)}
          disabled={pagina >= paginas}
          aria-label="Última página"
        >
          <ChevronsRight aria-hidden />
        </Button>
      </div>
    </nav>
  );
}
