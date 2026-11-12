import { KeyRound, Pencil, Search, UserCheck, UserPlus, UserX } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { toast } from "sonner";

import { useAdminTurmas, useAdminUsuarios, useDefinirAtivo, useResetarSenha } from "@/api/admin";
import type { AdminUsuario } from "@/api/tipos";
import { useUsuario } from "@/auth/sessao";
import {
  SelectNativo,
  TabelaResponsiva,
  Titulo,
  type Coluna,
  type Selecao,
} from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Paginacao } from "@/components/paginacao";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatarDataHora } from "@/lib/formato";
import { AcoesEmLote } from "@/pages/admin/AcoesEmLote";
import {
  DialogConfirmar,
  DialogSenhaTemporaria,
  SeloAtivo,
  type SenhaEntregue,
} from "@/pages/admin/comum";
import { DialogUsuario } from "@/pages/admin/DialogUsuario";
import { GRUPOS } from "@/pages/admin/grupos";

type Confirmacao = { tipo: "resetar" | "desativar" | "reativar"; usuario: AdminUsuario };

export function Usuarios() {
  const eu = useUsuario();
  const [busca, setBusca] = useState("");
  const [grupo, setGrupo] = useState("");
  const [turmaId, setTurmaId] = useState("");
  const [situacao, setSituacao] = useState("ativos");
  const [pagina, setPagina] = useState(1);
  const [editando, setEditando] = useState<AdminUsuario | "novo" | null>(null);
  const [confirmando, setConfirmando] = useState<Confirmacao | null>(null);
  const [senha, setSenha] = useState<SenhaEntregue | null>(null);
  // Marcados por id; valem entre páginas e filtros, até a ação ou "Limpar seleção".
  const [marcados, setMarcados] = useState<Map<number, AdminUsuario>>(() => new Map());

  const termo = useDeferredValue(busca.trim());
  const turmas = useAdminTurmas();
  const consulta = useAdminUsuarios({
    busca: termo,
    grupo,
    turma_id: turmaId ? Number(turmaId) : undefined,
    ativo: situacao === "todos" ? undefined : situacao === "ativos",
    page: pagina,
  });
  const resetar = useResetarSenha();
  const ativar = useDefinirAtivo();

  function filtrar(aplicar: () => void) {
    aplicar();
    setPagina(1);
  }

  function confirmar() {
    if (!confirmando) return;
    const { tipo, usuario } = confirmando;
    if (tipo === "resetar") {
      resetar.mutate(usuario.id, {
        onSuccess: ({ senha_temporaria }) => {
          setConfirmando(null);
          setSenha({ numerica: usuario.numerica, nome: usuario.nome, senha: senha_temporaria });
        },
      });
    } else {
      ativar.mutate(
        { id: usuario.id, ativo: tipo === "reativar" },
        {
          onSuccess: () => {
            setConfirmando(null);
            toast.success(tipo === "reativar" ? "Usuário reativado." : "Usuário desativado.");
          },
        },
      );
    }
  }

  const selecao: Selecao<AdminUsuario> = {
    marcados: new Set(marcados.keys()),
    rotulo: (u) => `Selecionar ${u.nome}`,
    onChange: (itens, marcado) =>
      setMarcados((atual) => {
        const novo = new Map(atual);
        for (const u of itens) {
          if (marcado) novo.set(u.id, u);
          else novo.delete(u.id);
        }
        return novo;
      }),
  };

  const colunas: Coluna<AdminUsuario>[] = [
    { titulo: "Numérica", className: "md:w-28", celula: (u) => <strong>{u.numerica}</strong> },
    {
      titulo: "Nome",
      celula: (u) => (
        <>
          {u.nome}
          {u.email && <span className="block text-xs text-muted-foreground">{u.email}</span>}
        </>
      ),
    },
    {
      titulo: "Perfis",
      className: "md:w-40",
      celula: (u) => (
        <>
          {u.grupos.join(", ") || "—"}
          {u.anotar && <span className="block text-xs text-muted-foreground">+ pode anotar</span>}
        </>
      ),
    },
    { titulo: "Turma", className: "md:w-28", celula: (u) => u.turma?.nome ?? "—" },
    {
      titulo: "Situação",
      className: "md:w-36",
      celula: (u) => (
        <span className="flex flex-col items-start gap-1">
          <SeloAtivo ativo={u.ativo} />
          {u.deve_trocar_senha && (
            <span className="text-xs text-muted-foreground">troca de senha pendente</span>
          )}
          <span className="text-xs text-muted-foreground">
            {u.ultimo_acesso
              ? `último acesso ${formatarDataHora(u.ultimo_acesso)}`
              : "nunca entrou"}
          </span>
        </span>
      ),
    },
    {
      titulo: "Ações",
      acoes: true,
      celula: (u) => (
        <>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setEditando(u)}
            aria-label={`Editar ${u.nome}`}
          >
            <Pencil aria-hidden /> Editar
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setConfirmando({ tipo: "resetar", usuario: u })}
            aria-label={`Resetar senha de ${u.nome}`}
          >
            <KeyRound aria-hidden /> Senha
          </Button>
          {u.numerica !== eu.numerica &&
            (u.ativo ? (
              <Button
                size="sm"
                variant="destructive"
                onClick={() => setConfirmando({ tipo: "desativar", usuario: u })}
                aria-label={`Desativar ${u.nome}`}
              >
                <UserX aria-hidden /> Desativar
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setConfirmando({ tipo: "reativar", usuario: u })}
                aria-label={`Reativar ${u.nome}`}
              >
                <UserCheck aria-hidden /> Reativar
              </Button>
            ))}
        </>
      ),
    },
  ];

  const textos =
    confirmando &&
    {
      resetar: {
        titulo: "Resetar senha",
        rotulo: "Gerar nova senha",
        corpo:
          "Uma senha temporária nova será gerada. As sessões abertas do usuário serão encerradas e ele terá de trocar a senha no próximo acesso. Bloqueios por tentativas de login também são liberados.",
      },
      desativar: {
        titulo: "Desativar usuário",
        rotulo: "Desativar",
        corpo:
          "O usuário não consegue mais entrar e as sessões abertas são encerradas. Nada é apagado: o histórico e as anotações continuam, e dá para reativar depois.",
      },
      reativar: {
        titulo: "Reativar usuário",
        rotulo: "Reativar",
        corpo: "O usuário volta a conseguir entrar com a senha que tinha.",
      },
    }[confirmando.tipo];

  return (
    <>
      <Titulo
        acao={
          <Button variant="sucesso" onClick={() => setEditando("novo")}>
            <UserPlus aria-hidden /> Novo usuário
          </Button>
        }
      >
        Usuários
      </Titulo>

      <div className="mb-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <div className="flex flex-col gap-1 sm:col-span-3 lg:col-span-1">
          <label htmlFor="busca-usuario" className="text-sm font-bold">
            Buscar
          </label>
          <span className="relative">
            <Search
              className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden
            />
            <Input
              id="busca-usuario"
              type="search"
              value={busca}
              onChange={(e) => filtrar(() => setBusca(e.target.value))}
              placeholder="Nome ou numérica"
              className="pl-9"
            />
          </span>
        </div>
        <label className="flex flex-col gap-1 text-sm font-bold">
          Perfil
          <SelectNativo value={grupo} onChange={(e) => filtrar(() => setGrupo(e.target.value))}>
            <option value="">Todos</option>
            {GRUPOS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </SelectNativo>
        </label>
        <label className="flex flex-col gap-1 text-sm font-bold">
          Turma
          <SelectNativo value={turmaId} onChange={(e) => filtrar(() => setTurmaId(e.target.value))}>
            <option value="">Todas</option>
            {turmas.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
                {!t.ativa && " (arquivada)"}
              </option>
            ))}
          </SelectNativo>
        </label>
        <label className="flex flex-col gap-1 text-sm font-bold">
          Situação
          <SelectNativo
            value={situacao}
            onChange={(e) => filtrar(() => setSituacao(e.target.value))}
          >
            <option value="ativos">Ativos</option>
            <option value="inativos">Inativos</option>
            <option value="todos">Todos</option>
          </SelectNativo>
        </label>
      </div>

      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.count === 0 ? (
        <Vazio>Nenhum usuário encontrado com estes filtros.</Vazio>
      ) : (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            {consulta.data.count} {consulta.data.count === 1 ? "usuário" : "usuários"}
          </p>
          <TabelaResponsiva
            itens={consulta.data.items}
            colunas={colunas}
            chave={(u) => u.id}
            legenda="Usuários"
            selecao={selecao}
          />
          <Paginacao pagina={pagina} total={consulta.data.count} onChange={setPagina} />
        </div>
      )}

      <AcoesEmLote usuarios={[...marcados.values()]} onConcluir={() => setMarcados(new Map())} />

      <DialogUsuario alvo={editando} onClose={() => setEditando(null)} onSenha={setSenha} />
      <DialogConfirmar
        aberto={confirmando !== null}
        titulo={textos ? textos.titulo : ""}
        rotulo={textos ? textos.rotulo : ""}
        perigo={confirmando?.tipo === "desativar"}
        pendente={resetar.isPending || ativar.isPending}
        erro={confirmando?.tipo === "resetar" ? resetar.error : ativar.error}
        onConfirmar={confirmar}
        onClose={() => {
          setConfirmando(null);
          resetar.reset();
          ativar.reset();
        }}
      >
        {confirmando && (
          <>
            <p>
              <strong>
                {confirmando.usuario.numerica} — {confirmando.usuario.nome}
              </strong>
            </p>
            <p>{textos?.corpo}</p>
          </>
        )}
      </DialogConfirmar>
      <DialogSenhaTemporaria entrega={senha} onClose={() => setSenha(null)} />
    </>
  );
}
