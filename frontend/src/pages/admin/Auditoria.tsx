import { LockOpen } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { toast } from "sonner";

import { mensagemDeErro } from "@/api/erros";
import { useAcessos, useAuditoria, useBloqueios, useLiberarBloqueio } from "@/api/admin";
import type { AdminAcesso, AdminAuditoriaItem, AdminTentativa } from "@/api/tipos";
import { SelectNativo, TabelaResponsiva, Titulo, type Coluna } from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Paginacao } from "@/components/paginacao";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatarDataHora } from "@/lib/formato";
import { usePaginaLocal } from "@/lib/paginacao";

const TIPOS = [
  ["anotacao", "Anotações"],
  ["despacho", "Despachos"],
  ["compensacao", "Compensações"],
  ["mappa", "Mappas"],
  ["usuario", "Usuários"],
  ["turma", "Turmas"],
  ["punicao", "Tipos de punição"],
] as const;

export function Auditoria() {
  return (
    <>
      <Titulo>Auditoria</Titulo>
      <Tabs defaultValue="alteracoes">
        <TabsList>
          <TabsTrigger value="alteracoes">Alterações</TabsTrigger>
          <TabsTrigger value="acessos">Acessos</TabsTrigger>
          <TabsTrigger value="bloqueios">Bloqueios</TabsTrigger>
        </TabsList>
        <TabsContent value="alteracoes" className="mt-4">
          <Alteracoes />
        </TabsContent>
        <TabsContent value="acessos" className="mt-4">
          <Acessos />
        </TabsContent>
        <TabsContent value="bloqueios" className="mt-4">
          <Bloqueios />
        </TabsContent>
      </Tabs>
    </>
  );
}

function Alteracoes() {
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [tipo, setTipo] = useState("");
  const [pagina, setPagina] = useState(1);
  const consulta = useAuditoria({ inicio, fim, tipo, page: pagina });

  function filtrar(aplicar: () => void) {
    aplicar();
    setPagina(1);
  }

  return (
    <>
      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-sm font-bold">
          De
          <Input
            type="date"
            value={inicio}
            onChange={(e) => filtrar(() => setInicio(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-bold">
          Até
          <Input type="date" value={fim} onChange={(e) => filtrar(() => setFim(e.target.value))} />
        </label>
        <label className="flex flex-col gap-1 text-sm font-bold">
          Registro
          <SelectNativo value={tipo} onChange={(e) => filtrar(() => setTipo(e.target.value))}>
            <option value="">Todos</option>
            {TIPOS.map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </SelectNativo>
        </label>
      </div>

      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.count === 0 ? (
        <Vazio>Nenhuma alteração no período.</Vazio>
      ) : (
        <div className="flex flex-col gap-3">
          <ol className="flex flex-col gap-2">
            {consulta.data.items.map((item) => (
              <li key={item.id}>
                <ItemAuditoria item={item} />
              </li>
            ))}
          </ol>
          <Paginacao pagina={pagina} total={consulta.data.count} onChange={setPagina} />
        </div>
      )}
    </>
  );
}

const COR_ACAO: Record<string, string> = {
  criou: "bg-green-100 text-green-900",
  alterou: "bg-secondary text-secondary-foreground",
  apagou: "bg-red-100 text-red-900",
};

function ItemAuditoria({ item }: { item: AdminAuditoriaItem }) {
  return (
    <article className="rounded-lg bg-card p-3 text-sm shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={COR_ACAO[item.acao]}>{item.acao}</Badge>
        <span className="font-bold">{item.descricao}</span>
        <span className="ml-auto text-xs text-muted-foreground">
          {formatarDataHora(item.quando)}
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        por{" "}
        {item.usuario ? `${item.usuario.numerica} — ${item.usuario.nome}` : "sistema (fora do app)"}
        {item.motivo && ` · ${item.motivo}`}
      </p>
      {item.mudancas.length > 0 && (
        <ul className="mt-2 flex flex-col gap-0.5">
          {item.mudancas.map((m) => (
            <li key={m.campo}>
              <span className="font-medium">{m.campo}:</span>{" "}
              <span className="text-muted-foreground line-through">{m.de}</span> → {m.para}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function Acessos() {
  const [numerica, setNumerica] = useState("");
  const [pagina, setPagina] = useState(1);
  const termo = useDeferredValue(numerica.trim());
  const consulta = useAcessos({ numerica: termo, page: pagina });

  const colunas: Coluna<AdminAcesso>[] = [
    { titulo: "Numérica", className: "md:w-32", celula: (a) => <strong>{a.numerica}</strong> },
    { titulo: "Entrou", className: "md:w-40", celula: (a) => formatarDataHora(a.entrou_em) },
    {
      titulo: "Saiu",
      className: "md:w-40",
      celula: (a) => (a.saiu_em ? formatarDataHora(a.saiu_em) : "—"),
    },
    { titulo: "IP", className: "md:w-32", celula: (a) => a.ip ?? "—" },
    {
      titulo: "Navegador",
      celula: (a) => (
        <span className="line-clamp-2 text-xs text-muted-foreground" title={a.navegador}>
          {a.navegador || "—"}
        </span>
      ),
    },
  ];

  return (
    <>
      <label className="mb-4 flex flex-col gap-1 text-sm font-bold sm:w-64">
        Numérica
        <Input
          type="search"
          value={numerica}
          onChange={(e) => {
            setNumerica(e.target.value);
            setPagina(1);
          }}
          placeholder="Todas"
        />
      </label>
      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.count === 0 ? (
        <Vazio>Nenhum acesso registrado.</Vazio>
      ) : (
        <div className="flex flex-col gap-3">
          <TabelaResponsiva
            itens={consulta.data.items}
            colunas={colunas}
            chave={(a) => `${a.numerica}-${a.entrou_em}`}
            legenda="Acessos"
          />
          <Paginacao pagina={pagina} total={consulta.data.count} onChange={setPagina} />
        </div>
      )}
    </>
  );
}

function Bloqueios() {
  const consulta = useBloqueios();
  const liberar = useLiberarBloqueio();
  const pagina = usePaginaLocal(consulta.data ?? []);

  const colunas: Coluna<AdminTentativa>[] = [
    { titulo: "Numérica", className: "md:w-32", celula: (t) => <strong>{t.numerica}</strong> },
    { titulo: "IP", className: "md:w-32", celula: (t) => t.ip ?? "—" },
    { titulo: "Falhas", className: "md:w-20", celula: (t) => t.falhas },
    { titulo: "Última", className: "md:w-40", celula: (t) => formatarDataHora(t.ultima_em) },
    {
      titulo: "Situação",
      className: "md:w-28",
      celula: (t) =>
        t.bloqueado ? (
          <Badge className="bg-red-100 text-red-900">Bloqueado</Badge>
        ) : (
          <span className="text-xs text-muted-foreground">tentativas</span>
        ),
    },
    {
      titulo: "Ação",
      className: "md:w-32",
      celula: (t) => (
        <Button
          size="sm"
          variant="outline"
          disabled={liberar.isPending}
          onClick={() =>
            liberar.mutate(t.numerica, {
              onSuccess: () => toast.success(`Login de ${t.numerica} liberado.`),
              onError: (erro) => toast.error(mensagemDeErro(erro)),
            })
          }
        >
          <LockOpen aria-hidden /> Liberar
        </Button>
      ),
    },
  ];

  return (
    <>
      <p className="mb-4 text-sm text-muted-foreground">
        Após 5 senhas erradas, a numérica fica bloqueada naquele IP por 15 minutos. Liberar zera as
        tentativas na hora.
      </p>
      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.length === 0 ? (
        <Vazio>Nenhuma tentativa de login com erro.</Vazio>
      ) : (
        <div className="flex flex-col gap-4">
          <TabelaResponsiva
            itens={pagina.itens}
            colunas={colunas}
            chave={(t) => `${t.numerica}-${t.ip}`}
            legenda="Tentativas de login com erro"
          />
          <Paginacao pagina={pagina.pagina} total={pagina.total} onChange={pagina.irPara} />
        </div>
      )}
    </>
  );
}
