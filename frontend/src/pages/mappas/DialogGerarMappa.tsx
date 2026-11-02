import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { urlDownload, useGerarMappa } from "@/api/mappas";
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
import { formatarData, hojeIso } from "@/lib/formato";
import { aplicarErrosNosCampos } from "@/lib/formulario";

const schema = z.object({
  titulo: z
    .string()
    .trim()
    .min(1, "Informe o título do mappa.")
    .max(120, "O título pode ter até 120 caracteres."),
});

type Dados = z.infer<typeof schema>;

type Props = { aberto: boolean; total: number; onClose: () => void };

export function DialogGerarMappa({ aberto, total, onClose }: Props) {
  return (
    <Dialog open={aberto} onOpenChange={(valor) => !valor && onClose()}>
      <DialogContent>{aberto && <FormularioGerar total={total} onClose={onClose} />}</DialogContent>
    </Dialog>
  );
}

function FormularioGerar({ total, onClose }: { total: number; onClose: () => void }) {
  const gerar = useGerarMappa();
  const form = useForm<Dados>({
    resolver: zodResolver(schema),
    defaultValues: { titulo: `Mappa ${formatarData(hojeIso())}` },
  });

  const enviar = form.handleSubmit(({ titulo }) =>
    gerar.mutate(titulo, {
      onSuccess: (mappa) => {
        toast.success(`Mappa "${mappa.titulo}" gerado.`, {
          description: "Publique na tela Mappas para os cadetes verem.",
          action: { label: "Baixar", onClick: () => window.location.assign(urlDownload(mappa)) },
        });
        onClose();
      },
      onError: (erro) => aplicarErrosNosCampos(erro, form.setError, ["titulo"]),
    }),
  );

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      <DialogHeader>
        <DialogTitle>Gerar mappa</DialogTitle>
        <DialogDescription>
          {total === 1
            ? "1 anotação despachada entra no mappa e sai desta lista."
            : `${total} anotações despachadas entram no mappa e saem desta lista.`}{" "}
          Nada é apagado: elas ficam arquivadas e ligadas ao mappa.
        </DialogDescription>
      </DialogHeader>

      <Campo rotulo="Título" erro={form.formState.errors.titulo}>
        {(props) => <Input {...props} {...form.register("titulo")} maxLength={120} />}
      </Campo>

      <ErroFormulario erro={gerar.error} />

      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">
            Cancelar
          </Button>
        </DialogClose>
        <Button type="submit" variant="sucesso" disabled={gerar.isPending}>
          {gerar.isPending ? "Gerando…" : "Gerar mappa"}
        </Button>
      </DialogFooter>
    </form>
  );
}
