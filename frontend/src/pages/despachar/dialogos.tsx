import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import {
  useAnotacoes,
  useAnular,
  useArquivar,
  useCompensar,
  useDespachar,
  useEditarDespacho,
  useMarcarCumprida,
  usePunicoes,
} from "@/api/anotacoes";
import type { Anotacao } from "@/api/tipos";
import { SelectNativo, SeloTipo } from "@/components/anotacoes";
import { Carregando, ErroCarregar } from "@/components/estados";
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
import { Textarea } from "@/components/ui/textarea";
import { formatarData, formatarDataHora, hojeIso, pessoaComPerfil } from "@/lib/formato";
import { aplicarErrosNosCampos } from "@/lib/formulario";
import { cn } from "@/lib/utils";

type PropsDialogo = { anotacao: Anotacao | null; onClose: () => void };

/**
 * Dialog controlado pela anotação: aberto quando há uma. Guarda a última para o conteúdo
 * não sumir durante a animação de fechar (o Radix desmonta o conteúdo depois dela).
 */
function DialogDaAnotacao({
  anotacao,
  onClose,
  children,
}: PropsDialogo & { children: (anotacao: Anotacao) => React.ReactNode }) {
  const [ultima, setUltima] = useState(anotacao);
  if (anotacao && anotacao !== ultima) setUltima(anotacao);
  return (
    <Dialog open={anotacao !== null} onOpenChange={(aberto) => !aberto && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto">
        {ultima && children(ultima)}
      </DialogContent>
    </Dialog>
  );
}

function ResumoAnotacao({ anotacao }: { anotacao: Anotacao }) {
  return (
    <div className="flex flex-col gap-1 rounded-md bg-muted p-3 text-sm">
      <div className="flex items-center gap-2">
        <SeloTipo tipo={anotacao.tipo} />
        <span className="text-muted-foreground">{formatarDataHora(anotacao.criada_em)}</span>
      </div>
      <p className="whitespace-pre-line">{anotacao.motivo}</p>
      <p className="text-muted-foreground">Anotado por {pessoaComPerfil(anotacao.autor)}</p>
    </div>
  );
}

function Cabecalho({ titulo, anotacao }: { titulo: string; anotacao: Anotacao }) {
  return (
    <DialogHeader>
      <DialogTitle>{titulo}</DialogTitle>
      <DialogDescription>
        {anotacao.cadete.numerica} — {anotacao.cadete.nome}
        {anotacao.cadete.turma && ` (${anotacao.cadete.turma.nome})`}
      </DialogDescription>
    </DialogHeader>
  );
}

function BotaoCancelar() {
  return (
    <DialogClose asChild>
      <Button type="button" variant="outline">
        Cancelar
      </Button>
    </DialogClose>
  );
}

// Despacho (negativa notificada) e edição do despacho

function schemaDespacho(dataOriginal?: string) {
  return z.object({
    punicao_id: z.string().min(1, "Escolha a punição."),
    data_cumprimento: z
      .string()
      .min(1, "Informe a data de cumprimento.")
      // Ao editar dá para manter a data original, mesmo que já tenha passado.
      .refine(
        (data) => data === dataOriginal || data >= hojeIso(),
        "A data de cumprimento não pode estar no passado.",
      ),
  });
}

type DadosDespacho = z.infer<ReturnType<typeof schemaDespacho>>;

export function DialogDespacho({
  anotacao,
  onClose,
  editar = false,
}: PropsDialogo & { editar?: boolean }) {
  return (
    <DialogDaAnotacao anotacao={anotacao} onClose={onClose}>
      {(a) => <FormularioDespacho anotacao={a} onClose={onClose} editar={editar} />}
    </DialogDaAnotacao>
  );
}

function FormularioDespacho({
  anotacao,
  onClose,
  editar,
}: {
  anotacao: Anotacao;
  onClose: () => void;
  editar: boolean;
}) {
  const punicoes = usePunicoes();
  const despachar = useDespachar();
  const editarDespacho = useEditarDespacho();
  const mutacao = editar ? editarDespacho : despachar;
  const original = anotacao.despacho;

  const form = useForm<DadosDespacho>({
    resolver: zodResolver(schemaDespacho(original?.data_cumprimento)),
    defaultValues: {
      punicao_id: original ? String(original.punicao.id) : "",
      data_cumprimento: original?.data_cumprimento ?? "",
    },
  });
  const { errors } = form.formState;

  const enviar = form.handleSubmit((dados) =>
    mutacao.mutate(
      {
        id: anotacao.id,
        punicao_id: Number(dados.punicao_id),
        data_cumprimento: dados.data_cumprimento,
      },
      {
        onSuccess: () => {
          toast.success(editar ? "Despacho atualizado." : "Anotação despachada.");
          onClose();
        },
        onError: (erro) =>
          aplicarErrosNosCampos(erro, form.setError, ["punicao_id", "data_cumprimento"]),
      },
    ),
  );

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      <Cabecalho titulo={editar ? "Editar despacho" : "Despachar anotação"} anotacao={anotacao} />
      <ResumoAnotacao anotacao={anotacao} />

      {punicoes.isError ? (
        <ErroCarregar erro={punicoes.error} tentarDeNovo={() => void punicoes.refetch()} />
      ) : (
        <Campo rotulo="Punição" erro={errors.punicao_id}>
          {(props) => (
            <SelectNativo {...props} {...form.register("punicao_id")} disabled={punicoes.isPending}>
              <option value="">{punicoes.isPending ? "Carregando…" : "Escolha a punição"}</option>
              {punicoes.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome}
                </option>
              ))}
            </SelectNativo>
          )}
        </Campo>
      )}
      <Campo rotulo="Data de cumprimento" erro={errors.data_cumprimento}>
        {(props) => (
          <Input
            {...props}
            {...form.register("data_cumprimento")}
            type="date"
            min={original ? undefined : hojeIso()}
          />
        )}
      </Campo>

      <ErroFormulario erro={mutacao.error} />

      <DialogFooter>
        <BotaoCancelar />
        <Button type="submit" variant="sucesso" disabled={mutacao.isPending}>
          {mutacao.isPending ? "Salvando…" : editar ? "Salvar despacho" : "Despachar"}
        </Button>
      </DialogFooter>
    </form>
  );
}

// Positiva notificada: compensar uma negativa do mesmo cadete, ou arquivar

export function DialogPositiva({ anotacao, onClose }: PropsDialogo) {
  return (
    <DialogDaAnotacao anotacao={anotacao} onClose={onClose}>
      {(a) => <FormularioPositiva positiva={a} onClose={onClose} />}
    </DialogDaAnotacao>
  );
}

function FormularioPositiva({ positiva, onClose }: { positiva: Anotacao; onClose: () => void }) {
  const [negativaId, setNegativaId] = useState<number>();
  const negativas = useAnotacoes({
    cadete_id: positiva.cadete.id,
    tipo: "negativa",
    status: "notificada",
  });
  const compensar = useCompensar();
  const arquivar = useArquivar();
  const ocupado = compensar.isPending || arquivar.isPending;

  function confirmarCompensacao() {
    if (negativaId === undefined) return;
    compensar.mutate(
      { id: positiva.id, negativa_id: negativaId },
      {
        onSuccess: () => {
          toast.success("Positiva compensou a negativa.");
          onClose();
        },
      },
    );
  }

  function confirmarArquivamento() {
    arquivar.mutate(positiva.id, {
      onSuccess: () => {
        toast.success("Positiva arquivada.");
        onClose();
      },
    });
  }

  const lista = negativas.data?.items ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Cabecalho titulo="Positiva: compensar ou arquivar" anotacao={positiva} />
      <ResumoAnotacao anotacao={positiva} />

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Negativa a compensar</legend>
        {negativas.isPending ? (
          <Carregando linhas={2} />
        ) : negativas.isError ? (
          <ErroCarregar erro={negativas.error} tentarDeNovo={() => void negativas.refetch()} />
        ) : lista.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            O cadete não tem negativa aguardando despacho. A positiva pode ser arquivada.
          </p>
        ) : (
          lista.map((negativa) => (
            <label
              key={negativa.id}
              className={cn(
                "flex cursor-pointer gap-3 rounded-lg border-2 bg-card p-3 text-sm has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
                negativaId === negativa.id ? "border-primary" : "border-border",
              )}
            >
              <input
                type="radio"
                name="negativa"
                value={negativa.id}
                checked={negativaId === negativa.id}
                onChange={() => setNegativaId(negativa.id)}
                className="mt-1 accent-primary"
              />
              <span className="flex flex-col gap-1">
                <span className="text-muted-foreground">
                  Negativa de {formatarDataHora(negativa.criada_em)}
                </span>
                <span className="whitespace-pre-line">{negativa.motivo}</span>
              </span>
            </label>
          ))
        )}
      </fieldset>

      <ErroFormulario erro={compensar.error ?? arquivar.error} />

      <DialogFooter>
        <BotaoCancelar />
        <Button type="button" variant="outline" onClick={confirmarArquivamento} disabled={ocupado}>
          Arquivar sem compensar
        </Button>
        <Button
          type="button"
          variant="sucesso"
          onClick={confirmarCompensacao}
          disabled={ocupado || negativaId === undefined}
        >
          Compensar
        </Button>
      </DialogFooter>
    </div>
  );
}

// Anular (substitui o "Excluir" do sistema antigo: nada é apagado)

const schemaAnular = z.object({
  justificativa: z
    .string()
    .trim()
    .min(5, "Explique o motivo da anulação (pelo menos 5 caracteres).")
    .max(2000, "A justificativa pode ter até 2000 caracteres."),
});

type DadosAnular = z.infer<typeof schemaAnular>;

export function DialogAnular({ anotacao, onClose }: PropsDialogo) {
  return (
    <DialogDaAnotacao anotacao={anotacao} onClose={onClose}>
      {(a) => <FormularioAnular anotacao={a} onClose={onClose} />}
    </DialogDaAnotacao>
  );
}

function FormularioAnular({ anotacao, onClose }: { anotacao: Anotacao; onClose: () => void }) {
  const anular = useAnular();
  const form = useForm<DadosAnular>({
    resolver: zodResolver(schemaAnular),
    defaultValues: { justificativa: "" },
  });

  const enviar = form.handleSubmit((dados) =>
    anular.mutate(
      { id: anotacao.id, justificativa: dados.justificativa },
      {
        onSuccess: () => {
          toast.success("Anotação anulada.");
          onClose();
        },
        onError: (erro) => aplicarErrosNosCampos(erro, form.setError, ["justificativa"]),
      },
    ),
  );

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      <Cabecalho titulo="Anular anotação" anotacao={anotacao} />
      <ResumoAnotacao anotacao={anotacao} />
      <p className="text-sm">
        A anotação sai das listas, mas continua registrada no histórico com a justificativa.
      </p>
      <Campo rotulo="Justificativa" erro={form.formState.errors.justificativa}>
        {(props) => (
          <Textarea {...props} {...form.register("justificativa")} rows={3} maxLength={2000} />
        )}
      </Campo>

      <ErroFormulario erro={anular.error} />

      <DialogFooter>
        <BotaoCancelar />
        <Button type="submit" variant="perigo" disabled={anular.isPending}>
          {anular.isPending ? "Anulando…" : "Anular"}
        </Button>
      </DialogFooter>
    </form>
  );
}

// Marcar despacho como cumprido

export function DialogCumprida({ anotacao, onClose }: PropsDialogo) {
  return (
    <DialogDaAnotacao anotacao={anotacao} onClose={onClose}>
      {(a) => <ConfirmarCumprida anotacao={a} onClose={onClose} />}
    </DialogDaAnotacao>
  );
}

function ConfirmarCumprida({ anotacao, onClose }: { anotacao: Anotacao; onClose: () => void }) {
  const cumprida = useMarcarCumprida();
  return (
    <div className="flex flex-col gap-4">
      <Cabecalho titulo="Marcar como cumprida" anotacao={anotacao} />
      {anotacao.despacho && (
        <p>
          Confirma que o cadete cumpriu <strong>{anotacao.despacho.punicao.nome}</strong> em{" "}
          {formatarData(anotacao.despacho.data_cumprimento)}?
        </p>
      )}
      <ErroFormulario erro={cumprida.error} />
      <DialogFooter>
        <BotaoCancelar />
        <Button
          variant="sucesso"
          disabled={cumprida.isPending}
          onClick={() =>
            cumprida.mutate(anotacao.id, {
              onSuccess: () => {
                toast.success("Punição marcada como cumprida.");
                onClose();
              },
            })
          }
        >
          Confirmar
        </Button>
      </DialogFooter>
    </div>
  );
}
