import { useEstatisticas } from "@/api/anotacoes";
import type { Estatisticas } from "@/api/tipos";
import brasao from "@/assets/brasao-apmgd.webp";
import { temPermissao, useUsuario } from "@/auth/sessao";
import { Carregando, ErroCarregar } from "@/components/estados";
import { formatarData } from "@/lib/formato";

export function Inicio() {
  const usuario = useUsuario();
  // No sistema antigo as estatísticas só apareciam para o comandante (a API exige o mesmo).
  const veEstatisticas = temPermissao(usuario, "anotacoes.despachar");

  return (
    <div className="flex flex-col gap-8 md:flex-row md:items-start">
      <section className="flex flex-1 flex-col gap-4">
        <h1 className="text-2xl font-bold text-primary">
          Bem-vindo(a) ao sistema, {usuario.perfil} {usuario.nome}
        </h1>
        <p>
          Este sistema foi desenvolvido para otimizar o controle e gestão das suas anotações e
          relatórios. Utilize o menu de navegação para acessar suas funções.
        </p>
        {veEstatisticas && <BlocoEstatisticas />}
      </section>
      <img
        src={brasao}
        alt="Brasão da Academia de Polícia Militar Gonçalves Dias"
        className="mx-auto w-40 md:w-64"
      />
    </div>
  );
}

function BlocoEstatisticas() {
  const consulta = useEstatisticas(true);

  if (consulta.isPending) return <Carregando linhas={2} />;
  if (consulta.isError) {
    return <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />;
  }
  return <Estatistica dados={consulta.data} />;
}

function Estatistica({ dados }: { dados: Estatisticas }) {
  return (
    <section aria-labelledby="titulo-estatisticas" className="rounded-lg bg-card p-4 shadow-sm">
      <h2 id="titulo-estatisticas" className="text-lg font-bold text-primary">
        Estatísticas da semana
      </h2>
      <p className="text-sm text-muted-foreground">Desde {formatarData(dados.inicio)}</p>

      <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
        <Numero rotulo="Anotações" valor={dados.total} />
        <Numero rotulo="Positivas" valor={dados.por_tipo.positivas} />
        <Numero rotulo="Negativas" valor={dados.por_tipo.negativas} />
      </dl>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Ranking titulo="Mais anotaram" itens={dados.mais_anotaram} />
        <Ranking titulo="Mais anotados" itens={dados.mais_anotados} />
      </div>
    </section>
  );
}

function Numero({ rotulo, valor }: { rotulo: string; valor: number }) {
  return (
    <div className="rounded-md bg-secondary p-2">
      <dt className="text-xs text-secondary-foreground">{rotulo}</dt>
      <dd className="text-2xl font-bold text-primary">{valor}</dd>
    </div>
  );
}

function Ranking({ titulo, itens }: { titulo: string; itens: Estatisticas["mais_anotados"] }) {
  return (
    <div>
      <h3 className="font-bold">{titulo}</h3>
      {itens.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhuma anotação nesta semana.</p>
      ) : (
        <ol className="list-decimal pl-5 text-sm">
          {itens.map((item) => (
            <li key={item.numerica}>
              {item.nome} ({item.numerica}) — {item.total}{" "}
              {item.total === 1 ? "anotação" : "anotações"}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
