import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Archive, ArchiveRestore, ArrowRightLeft, GraduationCap, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useAdminTurmas, useFormarTurma, useMoverCadetes, useSalvarTurma } from "@/api/admin";
import { api } from "@/api/client";
import type { components } from "@/api/schema";
import type { AdminTurma, AdminUsuario } from "@/api/tipos";
import { SelectNativo, TabelaResponsiva, Titulo, type Coluna } from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
import { Paginacao } from "@/components/paginacao";
import { Campo, ErroFormulario } from "@/components/formulario";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { hojeIso } from "@/lib/formato";
import { aplicarErrosNosCampos } from "@/lib/formulario";
import { usePaginaLocal } from "@/lib/paginacao";
import { Caixa, DialogConfirmar, SeloAtivo } from "@/pages/admin/comum";

type Acao =
  | { tipo: "editar"; turma: AdminTurma | null }
  | { tipo: "mover" | "formar" | "arquivar"; turma: AdminTurma };

export function Turmas() {
  const consulta = useAdminTurmas();
  const salvar = useSalvarTurma();
  const formar = useFormarTurma();
  const [acao, setAcao] = useState<Acao | null>(null);
  const pagina = usePaginaLocal(consulta.data ?? []);

  function fechar() {
    setAcao(null);
    salvar.reset();
    formar.reset();
  }

  const colunas: Coluna<AdminTurma>[] = [
    { titulo: "Turma", celula: (t) => <strong>{t.nome}</strong> },
    { titulo: "Ingresso", className: "md:w-24", celula: (t) => t.ano_ingresso },
    { titulo: "Cadetes ativos", className: "md:w-32", celula: (t) => t.total_cadetes },
    {
      titulo: "Situação",
      className: "md:w-28",
      celula: (t) => <SeloAtivo ativo={t.ativa} rotulos={["Ativa", "Arquivada"]} />,
    },
    {
      titulo: "Ações",
      className: "md:w-72",
      celula: (t) => (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => setAcao({ tipo: "editar", turma: t })}>
            <Pencil aria-hidden /> Editar
          </Button>
          {t.ativa && t.total_cadetes > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setAcao({ tipo: "mover", turma: t })}
            >
              <ArrowRightLeft aria-hidden /> Mover cadetes
            </Button>
          )}
          {t.ativa && t.total_cadetes > 0 && (
            <Button
              size="sm"
              variant="destructive"
              onClick={() => setAcao({ tipo: "formar", turma: t })}
            >
              <GraduationCap aria-hidden /> Formar
            </Button>
          )}
          {(!t.ativa || t.total_cadetes === 0) && (
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                t.ativa
                  ? setAcao({ tipo: "arquivar", turma: t })
                  : salvar.mutate(
                      { id: t.id, ativa: true },
                      { onSuccess: () => toast.success("Turma reativada.") },
                    )
              }
            >
              {t.ativa ? <Archive aria-hidden /> : <ArchiveRestore aria-hidden />}
              {t.ativa ? "Arquivar" : "Reativar"}
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <Titulo
        acao={
          <Button variant="sucesso" onClick={() => setAcao({ tipo: "editar", turma: null })}>
            <Plus aria-hidden /> Nova turma
          </Button>
        }
      >
        Turmas
      </Titulo>

      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.length === 0 ? (
        <Vazio>Nenhuma turma cadastrada.</Vazio>
      ) : (
        <div className="flex flex-col gap-4">
          <TabelaResponsiva
            itens={pagina.itens}
            colunas={colunas}
            chave={(t) => t.id}
            legenda="Turmas"
          />
          <Paginacao pagina={pagina.pagina} total={pagina.total} onChange={pagina.irPara} />
        </div>
      )}

      <DialogTurma
        aberto={acao?.tipo === "editar"}
        turma={acao?.tipo === "editar" ? acao.turma : null}
        onClose={fechar}
      />
      <DialogMover
        turma={acao?.tipo === "mover" ? acao.turma : null}
        turmas={consulta.data ?? []}
        onClose={fechar}
      />
      <DialogConfirmar
        aberto={acao?.tipo === "formar"}
        titulo="Formar turma"
        rotulo="Formar turma"
        perigo
        pendente={formar.isPending}
        erro={formar.error}
        onConfirmar={() =>
          acao?.tipo === "formar" &&
          formar.mutate(acao.turma.id, {
            onSuccess: ({ quantidade }) => {
              toast.success(`Turma formada: ${quantidade} cadetes desativados.`);
              fechar();
            },
          })
        }
        onClose={fechar}
      >
        {acao?.tipo === "formar" && (
          <>
            <p>
              <strong>{acao.turma.nome}</strong>: a turma é arquivada e os{" "}
              {acao.turma.total_cadetes} cadetes ativos dela são desativados.
            </p>
            <p>Nada é apagado: anotações, mappas e histórico continuam guardados.</p>
          </>
        )}
      </DialogConfirmar>
      <DialogConfirmar
        aberto={acao?.tipo === "arquivar"}
        titulo="Arquivar turma"
        rotulo="Arquivar"
        pendente={salvar.isPending}
        erro={salvar.error}
        onConfirmar={() =>
          acao?.tipo === "arquivar" &&
          salvar.mutate(
            { id: acao.turma.id, ativa: false },
            {
              onSuccess: () => {
                toast.success("Turma arquivada.");
                fechar();
              },
            },
          )
        }
        onClose={fechar}
      >
        {acao?.tipo === "arquivar" && (
          <p>
            <strong>{acao.turma.nome}</strong> sai dos filtros e do cadastro de novos cadetes. Dá
            para reativar depois.
          </p>
        )}
      </DialogConfirmar>
    </>
  );
}

const schemaTurma = z.object({
  nome: z.string().trim().min(1, "Informe o nome da turma.").max(40),
  ano_ingresso: z.coerce
    .number<string>({ error: "Informe o ano." })
    .int()
    .min(1990, "Ano inválido.")
    .max(2100, "Ano inválido."),
});

type DadosTurma = z.input<typeof schemaTurma>;

function DialogTurma({
  aberto,
  turma,
  onClose,
}: {
  aberto: boolean;
  turma: AdminTurma | null;
  onClose: () => void;
}) {
  return (
    <Dialog open={aberto} onOpenChange={(valor) => !valor && onClose()}>
      <DialogContent>
        {aberto && <FormularioTurma key={turma?.id ?? "nova"} turma={turma} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function FormularioTurma({ turma, onClose }: { turma: AdminTurma | null; onClose: () => void }) {
  const salvar = useSalvarTurma();
  const form = useForm<DadosTurma, unknown, z.output<typeof schemaTurma>>({
    resolver: zodResolver(schemaTurma),
    defaultValues: {
      nome: turma?.nome ?? "",
      ano_ingresso: turma ? String(turma.ano_ingresso) : hojeIso().slice(0, 4),
    },
  });
  const { errors } = form.formState;

  const enviar = form.handleSubmit((dados) =>
    salvar.mutate(
      { id: turma?.id, ...dados },
      {
        onSuccess: () => {
          toast.success(turma ? "Turma atualizada." : "Turma criada.");
          onClose();
        },
        onError: (erro) => aplicarErrosNosCampos(erro, form.setError, ["nome", "ano_ingresso"]),
      },
    ),
  );

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      <DialogHeader>
        <DialogTitle>{turma ? `Editar ${turma.nome}` : "Nova turma"}</DialogTitle>
      </DialogHeader>
      <Campo rotulo="Nome" erro={errors.nome}>
        {(props) => <Input {...props} {...form.register("nome")} placeholder="CFO I" />}
      </Campo>
      <Campo rotulo="Ano de ingresso" erro={errors.ano_ingresso}>
        {(props) => <Input {...props} {...form.register("ano_ingresso")} inputMode="numeric" />}
      </Campo>
      <ErroFormulario erro={salvar.error} />
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">
            Cancelar
          </Button>
        </DialogClose>
        <Button type="submit" variant="sucesso" disabled={salvar.isPending}>
          {salvar.isPending ? "Salvando…" : "Salvar"}
        </Button>
      </DialogFooter>
    </form>
  );
}

type PaginaUsuarios = components["schemas"]["PagedAdminUsuarioOut"];

/** Todos os cadetes ativos da turma (a listagem do painel é paginada; pede o máximo, 100). */
function useCadetesDaTurma(turmaId: number | undefined) {
  return useQuery({
    queryKey: ["admin", "usuarios", "turma", turmaId],
    enabled: turmaId !== undefined,
    queryFn: async ({ signal }) => {
      const todos: AdminUsuario[] = [];
      for (let pagina = 1; ; pagina += 1) {
        const resposta = await api<PaginaUsuarios>(
          `/admin/usuarios?turma_id=${turmaId}&grupo=Cadete&ativo=true&page=${pagina}&page_size=100`,
          { signal },
        );
        todos.push(...resposta.items);
        if (todos.length >= resposta.count || resposta.items.length === 0) return todos;
      }
    },
  });
}

function DialogMover({
  turma,
  turmas,
  onClose,
}: {
  turma: AdminTurma | null;
  turmas: AdminTurma[];
  onClose: () => void;
}) {
  return (
    <Dialog open={turma !== null} onOpenChange={(valor) => !valor && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto">
        {turma && <FormularioMover turma={turma} turmas={turmas} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function FormularioMover({
  turma,
  turmas,
  onClose,
}: {
  turma: AdminTurma;
  turmas: AdminTurma[];
  onClose: () => void;
}) {
  const cadetes = useCadetesDaTurma(turma.id);
  const mover = useMoverCadetes();
  const [destino, setDestino] = useState("");
  const [marcados, setMarcados] = useState<Set<number>>(new Set());
  const lista = cadetes.data ?? [];
  const todos = lista.length > 0 && marcados.size === lista.length;

  function alternar(id: number, marcado: boolean) {
    const novo = new Set(marcados);
    if (marcado) novo.add(id);
    else novo.delete(id);
    setMarcados(novo);
  }

  return (
    <div className="flex flex-col gap-4">
      <DialogHeader>
        <DialogTitle>Mover cadetes de {turma.nome}</DialogTitle>
        <DialogDescription>Escolha os cadetes e a turma de destino.</DialogDescription>
      </DialogHeader>

      <label className="flex flex-col gap-1 text-sm font-bold">
        Turma de destino
        <SelectNativo value={destino} onChange={(e) => setDestino(e.target.value)}>
          <option value="">Escolha a turma</option>
          {turmas
            .filter((t) => t.ativa && t.id !== turma.id)
            .map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
        </SelectNativo>
      </label>

      {cadetes.isPending ? (
        <Carregando linhas={2} />
      ) : cadetes.isError ? (
        <ErroCarregar erro={cadetes.error} tentarDeNovo={() => void cadetes.refetch()} />
      ) : (
        <fieldset className="flex flex-col gap-2 rounded-lg bg-card p-3">
          <legend className="sr-only">Cadetes</legend>
          <Caixa
            rotulo={`Todos (${lista.length})`}
            marcado={todos}
            onChange={(marcado) =>
              setMarcados(marcado ? new Set(lista.map((c) => c.id)) : new Set())
            }
          />
          <hr className="border-border" />
          {lista.map((cadete) => (
            <Caixa
              key={cadete.id}
              rotulo={`${cadete.numerica} — ${cadete.nome}`}
              marcado={marcados.has(cadete.id)}
              onChange={(marcado) => alternar(cadete.id, marcado)}
            />
          ))}
        </fieldset>
      )}

      <ErroFormulario erro={mover.error} />

      <DialogFooter>
        <DialogClose asChild>
          <Button variant="outline">Cancelar</Button>
        </DialogClose>
        <Button
          variant="sucesso"
          disabled={mover.isPending || !destino || marcados.size === 0}
          onClick={() =>
            mover.mutate(
              { cadete_ids: [...marcados], destino_id: Number(destino) },
              {
                onSuccess: ({ quantidade }) => {
                  toast.success(`${quantidade} cadete(s) movido(s).`);
                  onClose();
                },
              },
            )
          }
        >
          Mover {marcados.size > 0 && `(${marcados.size})`}
        </Button>
      </DialogFooter>
    </div>
  );
}
