import { useMinhasAnotacoes } from "@/api/anotacoes";
import type { Anotacao } from "@/api/tipos";
import { SeloStatus, SeloTipo, Titulo } from "@/components/anotacoes";
import { Badge } from "@/components/ui/badge";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Paginacao } from "@/components/paginacao";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatarData, formatarDataHora, pessoaComPerfil } from "@/lib/formato";
import { usePaginaLocal } from "@/lib/paginacao";

/** Despachada que foi para o mappa: fica arquivada, mas a punição ainda é para cumprir. */
function noMappa(anotacao: Anotacao) {
  return anotacao.status === "arquivada" && anotacao.despacho !== null;
}

const ABAS: { valor: string; rotulo: string; filtro: (a: Anotacao) => boolean; vazio: string }[] = [
  {
    valor: "pendentes",
    rotulo: "Pendentes",
    filtro: (a) => a.status === "notificada",
    vazio: "Nenhuma anotação aguardando despacho.",
  },
  {
    valor: "despachadas",
    rotulo: "Despachadas",
    filtro: (a) => a.status === "despachada" || noMappa(a),
    vazio: "Nenhuma punição a cumprir.",
  },
  {
    valor: "encerradas",
    rotulo: "Encerradas",
    filtro: (a) =>
      a.status === "cumprida" ||
      a.status === "compensada" ||
      (a.status === "arquivada" && !noMappa(a)),
    vazio: "Nenhuma anotação encerrada.",
  },
];

export function MinhasAnotacoes() {
  const consulta = useMinhasAnotacoes();

  return (
    <>
      <Titulo>Minhas anotações</Titulo>
      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : (
        <Tabs defaultValue="pendentes">
          <TabsList className="w-full sm:w-auto">
            {ABAS.map((aba) => (
              <TabsTrigger key={aba.valor} value={aba.valor} className="px-1.5 text-xs sm:text-sm">
                {aba.rotulo} ({consulta.data.filter(aba.filtro).length})
              </TabsTrigger>
            ))}
          </TabsList>
          {ABAS.map((aba) => (
            <TabsContent key={aba.valor} value={aba.valor} className="mt-4">
              <ListaDaAba itens={consulta.data.filter(aba.filtro)} vazio={aba.vazio} />
            </TabsContent>
          ))}
        </Tabs>
      )}
    </>
  );
}

function ListaDaAba({ itens, vazio }: { itens: Anotacao[]; vazio: string }) {
  const pagina = usePaginaLocal(itens);
  if (itens.length === 0) return <Vazio>{vazio}</Vazio>;
  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-3">
        {pagina.itens.map((anotacao) => (
          <li key={anotacao.id}>
            <CartaoAnotacao anotacao={anotacao} />
          </li>
        ))}
      </ul>
      <Paginacao pagina={pagina.pagina} total={pagina.total} onChange={pagina.irPara} />
    </div>
  );
}

function CartaoAnotacao({ anotacao }: { anotacao: Anotacao }) {
  return (
    <article className="flex flex-col gap-2 rounded-lg bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <SeloTipo tipo={anotacao.tipo} />
        {noMappa(anotacao) ? (
          <Badge className="bg-primary text-primary-foreground">No mappa</Badge>
        ) : (
          anotacao.status !== "notificada" && <SeloStatus status={anotacao.status} />
        )}
        <span className="ml-auto text-sm text-muted-foreground">
          {formatarDataHora(anotacao.criada_em)}
        </span>
      </div>
      <p className="whitespace-pre-line">{anotacao.motivo}</p>
      <p className="text-sm text-muted-foreground">Anotado por {pessoaComPerfil(anotacao.autor)}</p>
      {anotacao.despacho && (
        <p className="rounded-md bg-secondary px-3 py-2 text-sm text-secondary-foreground">
          <strong>{anotacao.despacho.punicao.nome}</strong> em{" "}
          {formatarData(anotacao.despacho.data_cumprimento)}
        </p>
      )}
    </article>
  );
}
