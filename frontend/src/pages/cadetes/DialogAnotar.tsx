import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useCriarAnotacao } from "@/api/anotacoes";
import type { Cadete } from "@/api/tipos";
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
import { FieldError } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { aplicarErrosNosCampos } from "@/lib/formulario";
import { cn } from "@/lib/utils";

const MOTIVO_MAX = 2000;

// Mesmos limites do AnotacaoIn da API.
const schema = z.object({
  tipo: z.enum(["positiva", "negativa"], { error: "Escolha o tipo da anotação." }),
  motivo: z
    .string()
    .trim()
    .min(3, "Descreva o motivo (pelo menos 3 caracteres).")
    .max(MOTIVO_MAX, `O motivo pode ter até ${MOTIVO_MAX} caracteres.`),
});

type Dados = z.input<typeof schema>;

export function DialogAnotar({ cadete, onClose }: { cadete: Cadete | null; onClose: () => void }) {
  // Mantém o último cadete durante a animação de fechar.
  const [ultimo, setUltimo] = useState(cadete);
  if (cadete && cadete !== ultimo) setUltimo(cadete);
  return (
    <Dialog open={cadete !== null} onOpenChange={(aberto) => !aberto && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto">
        {ultimo && <FormularioAnotar key={ultimo.id} cadete={ultimo} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function FormularioAnotar({ cadete, onClose }: { cadete: Cadete; onClose: () => void }) {
  const criar = useCriarAnotacao();
  const form = useForm<Dados>({
    resolver: zodResolver(schema),
    defaultValues: { motivo: "" },
  });
  const { errors } = form.formState;
  const tipo = useWatch({ control: form.control, name: "tipo" });
  const tamanho = useWatch({ control: form.control, name: "motivo" })?.length ?? 0;

  const enviar = form.handleSubmit((dados) =>
    criar.mutate(
      { cadete_id: cadete.id, tipo: dados.tipo, motivo: dados.motivo.trim() },
      {
        onSuccess: () => {
          toast.success(`Anotação registrada para ${cadete.nome}.`);
          onClose();
        },
        onError: (erro) => aplicarErrosNosCampos(erro, form.setError, ["tipo", "motivo"]),
      },
    ),
  );

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      <DialogHeader>
        <DialogTitle>Anotar cadete</DialogTitle>
        <DialogDescription>
          {cadete.numerica} — {cadete.nome}
          {cadete.turma && ` (${cadete.turma.nome})`}
        </DialogDescription>
      </DialogHeader>

      <fieldset className="flex flex-col gap-2" aria-describedby="erro-tipo">
        <legend className="mb-2 text-sm font-medium">Tipo</legend>
        <div className="grid grid-cols-2 gap-2">
          {(["positiva", "negativa"] as const).map((valor) => (
            <label
              key={valor}
              className={cn(
                "flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 bg-card px-3 py-3 font-bold has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
                tipo === valor
                  ? valor === "positiva"
                    ? "border-sucesso text-sucesso"
                    : "border-destructive text-destructive"
                  : "border-border",
              )}
            >
              <input type="radio" value={valor} {...form.register("tipo")} className="sr-only" />
              {valor === "positiva" ? "Positiva" : "Negativa"}
            </label>
          ))}
        </div>
        <FieldError id="erro-tipo" errors={[errors.tipo]} />
      </fieldset>

      <Campo rotulo="Motivo" erro={errors.motivo}>
        {(props) => (
          <Textarea {...props} {...form.register("motivo")} rows={5} maxLength={MOTIVO_MAX} />
        )}
      </Campo>
      <p className="-mt-3 text-right text-xs text-muted-foreground" aria-live="polite">
        {tamanho}/{MOTIVO_MAX}
      </p>

      <ErroFormulario erro={criar.error} />

      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">
            Cancelar
          </Button>
        </DialogClose>
        <Button type="submit" variant="sucesso" disabled={criar.isPending}>
          {criar.isPending ? "Salvando…" : "Registrar anotação"}
        </Button>
      </DialogFooter>
    </form>
  );
}
