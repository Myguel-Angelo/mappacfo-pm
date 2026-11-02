import { Ban, CircleCheck, Pencil } from "lucide-react";
import { useState } from "react";

import { useAnotacoes, useTurmas } from "@/api/anotacoes";
import type { Anotacao } from "@/api/tipos";
import {
  FiltroTurma,
  Paginacao,
  TabelaResponsiva,
  Titulo,
  type Coluna,
} from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Button } from "@/components/ui/button";
import { formatarData, formatarDataHora, pessoaComPerfil } from "@/lib/formato";
import { DialogAnular, DialogCumprida, DialogDespacho } from "@/pages/despachar/dialogos";

type Acao = { tipo: "editar" | "cumprida" | "anular"; anotacao: Anotacao };

export function Despachadas() {
  const [turmaId, setTurmaId] = useState<number>();
  const [pagina, setPagina] = useState(1);
  const [acao, setAcao] = useState<Acao | null>(null);
  const turmas = useTurmas();
  const consulta = useAnotacoes({ status: "despachada", turma_id: turmaId, page: pagina });

  if (consulta.data && consulta.data.items.length === 0 && pagina > 1) setPagina(pagina - 1);

  const colunas: Coluna<Anotacao>[] = [
    {
      titulo: "Cadete",
      className: "md:w-48",
      celula: (a) => (
        <>
          <span className="font-bold">{a.cadete.numerica}</span> {a.cadete.nome}
          {a.cadete.turma && (
            <span className="block text-xs text-muted-foreground">{a.cadete.turma.nome}</span>
          )}
        </>
      ),
    },
    { titulo: "Motivo", celula: (a) => <span className="whitespace-pre-line">{a.motivo}</span> },
    { titulo: "Quem anotou", className: "md:w-40", celula: (a) => pessoaComPerfil(a.autor) },
    {
      titulo: "Punição",
      className: "md:w-36",
      celula: (a) => <strong>{a.despacho?.punicao.nome}</strong>,
    },
    {
      titulo: "Cumprimento",
      className: "md:w-28",
      celula: (a) => (a.despacho ? formatarData(a.despacho.data_cumprimento) : "—"),
    },
    {
      titulo: "Despacho",
      className: "md:w-36",
      celula: (a) =>
        a.despacho && (
          <span className="text-xs">
            {a.despacho.despachado_por.nome}
            <span className="block text-muted-foreground">
              {formatarDataHora(a.despacho.despachado_em)}
            </span>
          </span>
        ),
    },
    {
      titulo: "Ações",
      className: "md:w-40",
      celula: (a) => (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setAcao({ tipo: "editar", anotacao: a })}
          >
            <Pencil aria-hidden /> Editar
          </Button>
          <Button
            size="sm"
            variant="sucesso"
            onClick={() => setAcao({ tipo: "cumprida", anotacao: a })}
          >
            <CircleCheck aria-hidden /> Cumprida
          </Button>
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
      <Titulo>Anotações despachadas</Titulo>
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
        <Vazio>Nenhuma punição aguardando cumprimento.</Vazio>
      ) : (
        <div className="flex flex-col gap-4">
          <TabelaResponsiva
            itens={consulta.data.items}
            colunas={colunas}
            chave={(a) => a.id}
            legenda="Anotações despachadas"
          />
          <Paginacao pagina={pagina} total={consulta.data.count} onChange={setPagina} />
        </div>
      )}

      <DialogDespacho
        anotacao={acao?.tipo === "editar" ? acao.anotacao : null}
        onClose={fechar}
        editar
      />
      <DialogCumprida
        anotacao={acao?.tipo === "cumprida" ? acao.anotacao : null}
        onClose={fechar}
      />
      <DialogAnular anotacao={acao?.tipo === "anular" ? acao.anotacao : null} onClose={fechar} />
    </>
  );
}
