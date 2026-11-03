import { Download, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { mensagemDeErro } from "@/api/erros";
import { urlDownload, useMappas, usePublicarMappa } from "@/api/mappas";
import type { Mappa } from "@/api/tipos";
import { temPermissao, useUsuario } from "@/auth/sessao";
import { TabelaResponsiva, Titulo, type Coluna } from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatarDataHora } from "@/lib/formato";

export function Mappas() {
  const usuario = useUsuario();
  // Quem exporta vê todos e publica; os demais recebem da API só os publicados.
  const gerencia = temPermissao(usuario, "anotacoes.exportar");
  const consulta = useMappas();
  const publicar = usePublicarMappa();

  function alternar(mappa: Mappa) {
    publicar.mutate(
      { id: mappa.id, publicado: !mappa.publicado },
      {
        onSuccess: (atualizado) =>
          toast.success(
            atualizado.publicado ? "Mappa publicado para os cadetes." : "Mappa despublicado.",
          ),
        onError: (erro) => toast.error(mensagemDeErro(erro)),
      },
    );
  }

  const colunas: Coluna<Mappa>[] = [
    { titulo: "Título", celula: (m) => <span className="font-bold">{m.titulo}</span> },
    { titulo: "Gerado em", className: "md:w-40", celula: (m) => formatarDataHora(m.gerado_em) },
    ...(gerencia
      ? [
          { titulo: "Gerado por", className: "md:w-44", celula: (m: Mappa) => m.gerado_por.nome },
          { titulo: "Anotações", className: "md:w-28", celula: (m: Mappa) => m.total_anotacoes },
          {
            titulo: "Situação",
            className: "md:w-32",
            celula: (m: Mappa) =>
              m.publicado ? (
                <Badge className="bg-sucesso text-white">Publicado</Badge>
              ) : (
                <Badge className="bg-muted text-muted-foreground">Não publicado</Badge>
              ),
          },
        ]
      : []),
    {
      titulo: "Ações",
      className: gerencia ? "md:w-56" : "md:w-32",
      celula: (m) => (
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm">
            <a href={urlDownload(m)} download aria-label={`Baixar ${m.titulo}`}>
              <Download aria-hidden /> Baixar
            </a>
          </Button>
          {gerencia && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => alternar(m)}
              disabled={publicar.isPending && publicar.variables?.id === m.id}
            >
              {m.publicado ? <EyeOff aria-hidden /> : <Eye aria-hidden />}
              {m.publicado ? "Despublicar" : "Publicar"}
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <Titulo>Mappas</Titulo>
      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.length === 0 ? (
        <Vazio>
          {gerencia
            ? "Nenhum mappa gerado ainda. Gere o primeiro na tela Despachadas."
            : "Nenhum mappa publicado."}
        </Vazio>
      ) : (
        <TabelaResponsiva
          itens={consulta.data}
          colunas={colunas}
          chave={(m) => m.id}
          legenda="Mappas"
        />
      )}
    </>
  );
}
