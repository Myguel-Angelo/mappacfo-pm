import { PencilLine, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";

import { useCadetes, useTurmas } from "@/api/anotacoes";
import type { Cadete } from "@/api/tipos";
import { FiltroTurma, TabelaResponsiva, Titulo, type Coluna } from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DialogAnotar } from "@/pages/cadetes/DialogAnotar";

/** Busca sem acento e sem caixa: "joao" acha "João". */
function normalizar(texto: string) {
  return texto
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

export function Cadetes() {
  const [turmaId, setTurmaId] = useState<number>();
  const [busca, setBusca] = useState("");
  const [anotando, setAnotando] = useState<Cadete | null>(null);
  const turmas = useTurmas();
  const cadetes = useCadetes(turmaId);
  const termo = normalizar(useDeferredValue(busca).trim());

  const filtrados =
    cadetes.data?.filter(
      (c) => !termo || normalizar(c.nome).includes(termo) || c.numerica.includes(termo),
    ) ?? [];

  const colunas: Coluna<Cadete>[] = [
    { titulo: "Numérica", celula: (c) => c.numerica, className: "md:w-28" },
    { titulo: "Nome", celula: (c) => c.nome },
    { titulo: "Turma", celula: (c) => c.turma?.nome ?? "—", className: "md:w-32" },
    {
      titulo: "Ação",
      className: "md:w-32",
      celula: (c) => (
        <Button size="sm" onClick={() => setAnotando(c)} aria-label={`Anotar ${c.nome}`}>
          <PencilLine aria-hidden /> Anotar
        </Button>
      ),
    },
  ];

  return (
    <>
      <Titulo>Relação de cadetes</Titulo>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <FiltroTurma turmas={turmas.data} valor={turmaId} onChange={setTurmaId} />
        <div className="flex flex-1 flex-col gap-1">
          <label htmlFor="busca-cadete" className="text-sm font-bold">
            Buscar
          </label>
          <span className="relative">
            <Search
              className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden
            />
            <Input
              id="busca-cadete"
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Nome ou numérica"
              className="pl-9"
            />
          </span>
        </div>
      </div>

      {cadetes.isPending ? (
        <Carregando />
      ) : cadetes.isError ? (
        <ErroCarregar erro={cadetes.error} tentarDeNovo={() => void cadetes.refetch()} />
      ) : filtrados.length === 0 ? (
        <Vazio>
          {termo ? "Nenhum cadete encontrado para a busca." : "Nenhum cadete nesta turma."}
        </Vazio>
      ) : (
        <TabelaResponsiva
          itens={filtrados}
          colunas={colunas}
          chave={(c) => c.id}
          legenda="Cadetes"
        />
      )}

      <DialogAnotar cadete={anotando} onClose={() => setAnotando(null)} />
    </>
  );
}
