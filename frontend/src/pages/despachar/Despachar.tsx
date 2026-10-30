import { Ban, Gavel, Scale } from "lucide-react";
import { useState } from "react";

import { useAnotacoes, useTurmas } from "@/api/anotacoes";
import type { Anotacao } from "@/api/tipos";
import {
  FiltroTurma,
  Paginacao,
  SeloTipo,
  TabelaResponsiva,
  Titulo,
  type Coluna,
} from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Button } from "@/components/ui/button";
import { formatarDataHora, pessoaComPerfil } from "@/lib/formato";
import { DialogAnular, DialogDespacho, DialogPositiva } from "@/pages/despachar/dialogos";

type Acao = { tipo: "despachar" | "positiva" | "anular"; anotacao: Anotacao };

/** Agrupa por turma mantendo a ordem da API (positivas primeiro, numérica, data). */
function porTurma(itens: Anotacao[]) {
  const grupos = new Map<string, Anotacao[]>();
  for (const item of itens) {
    const turma = item.cadete.turma?.nome ?? "Sem turma";
    grupos.set(turma, [...(grupos.get(turma) ?? []), item]);
  }
  return [...grupos].sort(([a], [b]) => a.localeCompare(b, "pt-BR"));
}

export function Despachar() {
  const [turmaId, setTurmaId] = useState<number>();
  const [pagina, setPagina] = useState(1);
  const [acao, setAcao] = useState<Acao | null>(null);
  const turmas = useTurmas();
  const consulta = useAnotacoes({ status: "notificada", turma_id: turmaId, page: pagina });

  // Despachou o último item da última página: volta uma página.
  if (consulta.data && consulta.data.items.length === 0 && pagina > 1) setPagina(pagina - 1);

  const colunas: Coluna<Anotacao>[] = [
    {
      titulo: "Cadete",
      className: "md:w-48",
      celula: (a) => (
        <>
          <span className="font-bold">{a.cadete.numerica}</span> {a.cadete.nome}
        </>
      ),
    },
    { titulo: "Tipo", className: "md:w-24", celula: (a) => <SeloTipo tipo={a.tipo} /> },
    { titulo: "Motivo", celula: (a) => <span className="whitespace-pre-line">{a.motivo}</span> },
    { titulo: "Quem anotou", className: "md:w-44", celula: (a) => pessoaComPerfil(a.autor) },
    { titulo: "Data", className: "md:w-36", celula: (a) => formatarDataHora(a.criada_em) },
    {
      titulo: "Ações",
      className: "md:w-40",
      celula: (a) => (
        <div className="flex flex-wrap gap-2">
          {a.tipo === "negativa" ? (
            <Button
              size="sm"
              variant="sucesso"
              onClick={() => setAcao({ tipo: "despachar", anotacao: a })}
            >
              <Gavel aria-hidden /> Despachar
            </Button>
          ) : (
            <Button
              size="sm"
              variant="sucesso"
              onClick={() => setAcao({ tipo: "positiva", anotacao: a })}
            >
              <Scale aria-hidden /> Compensar
            </Button>
          )}
          <Button
            size="sm"
            variant="destructive"
            onClick={() => setAcao({ tipo: "anular", anotacao: a })}
          >
            <Ban aria-hidden /> Anular
          </Button>
        </div>
      ),
    },
  ];

  function fechar() {
    setAcao(null);
  }

  return (
    <>
      <Titulo>Anotações para despachar</Titulo>
      <div className="mb-4">
        <FiltroTurma
          turmas={turmas.data}
          valor={turmaId}
          onChange={(id) => {
            setTurmaId(id);
            setPagina(1);
          }}
        />
      </div>

      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.count === 0 ? (
        <Vazio>Nenhuma anotação para despachar!</Vazio>
      ) : (
        <div className="flex flex-col gap-6">
          <p className="text-sm text-muted-foreground">
            {consulta.data.count} {consulta.data.count === 1 ? "anotação" : "anotações"} aguardando
            despacho.
          </p>
          {porTurma(consulta.data.items).map(([turma, itens]) => (
            <section key={turma} aria-labelledby={`turma-${turma}`}>
              <h2 id={`turma-${turma}`} className="mb-2 text-lg font-bold text-primary">
                {turma}
              </h2>
              <TabelaResponsiva
                itens={itens}
                colunas={colunas}
                chave={(a) => a.id}
                legenda={`Anotações notificadas da turma ${turma}`}
              />
            </section>
          ))}
          <Paginacao pagina={pagina} total={consulta.data.count} onChange={setPagina} />
        </div>
      )}

      <DialogDespacho
        anotacao={acao?.tipo === "despachar" ? acao.anotacao : null}
        onClose={fechar}
      />
      <DialogPositiva
        anotacao={acao?.tipo === "positiva" ? acao.anotacao : null}
        onClose={fechar}
      />
      <DialogAnular anotacao={acao?.tipo === "anular" ? acao.anotacao : null} onClose={fechar} />
    </>
  );
}
