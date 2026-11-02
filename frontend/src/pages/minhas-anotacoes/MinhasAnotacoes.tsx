import { useMinhasAnotacoes } from "@/api/anotacoes";
import type { Anotacao, StatusAnotacao } from "@/api/tipos";
import { SeloStatus, SeloTipo, Titulo } from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatarData, formatarDataHora, pessoaComPerfil } from "@/lib/formato";

const ABAS: { valor: string; rotulo: string; status: StatusAnotacao[]; vazio: string }[] = [
  {
    valor: "pendentes",
    rotulo: "Pendentes",
    status: ["notificada"],
    vazio: "Nenhuma anotação aguardando despacho.",
  },
  {
    valor: "despachadas",
    rotulo: "Despachadas",
    status: ["despachada"],
    vazio: "Nenhuma punição a cumprir.",
  },
  {
    valor: "encerradas",
    rotulo: "Encerradas",
    status: ["cumprida", "compensada", "arquivada"],
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
                {aba.rotulo} ({consulta.data.filter((a) => aba.status.includes(a.status)).length})
              </TabsTrigger>
            ))}
          </TabsList>
          {ABAS.map((aba) => {
            const itens = consulta.data.filter((a) => aba.status.includes(a.status));
            return (
              <TabsContent key={aba.valor} value={aba.valor} className="mt-4">
                {itens.length === 0 ? (
                  <Vazio>{aba.vazio}</Vazio>
                ) : (
                  <ul className="flex flex-col gap-3">
                    {itens.map((anotacao) => (
                      <li key={anotacao.id}>
                        <CartaoAnotacao anotacao={anotacao} />
                      </li>
                    ))}
                  </ul>
                )}
              </TabsContent>
            );
          })}
        </Tabs>
      )}
    </>
  );
}

function CartaoAnotacao({ anotacao }: { anotacao: Anotacao }) {
  return (
    <article className="flex flex-col gap-2 rounded-lg bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <SeloTipo tipo={anotacao.tipo} />
        {anotacao.status !== "notificada" && <SeloStatus status={anotacao.status} />}
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
