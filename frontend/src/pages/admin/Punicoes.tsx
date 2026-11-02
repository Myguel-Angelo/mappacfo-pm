import { zodResolver } from "@hookform/resolvers/zod";
import { Pencil, Plus, Power, PowerOff } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { mensagemDeErro } from "@/api/erros";
import { useAdminPunicoes, useSalvarPunicao } from "@/api/admin";
import type { AdminPunicao } from "@/api/tipos";
import { TabelaResponsiva, Titulo, type Coluna } from "@/components/anotacoes";
import { Carregando, ErroCarregar, Vazio } from "@/components/estados";
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
import { aplicarErrosNosCampos } from "@/lib/formulario";
import { SeloAtivo } from "@/pages/admin/comum";

export function Punicoes() {
  const consulta = useAdminPunicoes();
  const alternar = useSalvarPunicao();
  const [editando, setEditando] = useState<AdminPunicao | "nova" | null>(null);

  const colunas: Coluna<AdminPunicao>[] = [
    { titulo: "Tipo de punição", celula: (p) => <strong>{p.nome}</strong> },
    { titulo: "Despachos", className: "md:w-28", celula: (p) => p.total_despachos },
    {
      titulo: "Situação",
      className: "md:w-28",
      celula: (p) => <SeloAtivo ativo={p.ativo} rotulos={["Em uso", "Desativado"]} />,
    },
    {
      titulo: "Ações",
      className: "md:w-56",
      celula: (p) => (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => setEditando(p)}>
            <Pencil aria-hidden /> Renomear
          </Button>
          <Button
            size="sm"
            variant={p.ativo ? "destructive" : "outline"}
            disabled={alternar.isPending}
            onClick={() =>
              alternar.mutate(
                { id: p.id, ativo: !p.ativo },
                {
                  onSuccess: (atual) =>
                    toast.success(
                      atual.ativo ? "Tipo de punição ativado." : "Tipo de punição desativado.",
                    ),
                  onError: (erro) => toast.error(mensagemDeErro(erro)),
                },
              )
            }
          >
            {p.ativo ? <PowerOff aria-hidden /> : <Power aria-hidden />}
            {p.ativo ? "Desativar" : "Ativar"}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <>
      <Titulo
        acao={
          <Button variant="sucesso" onClick={() => setEditando("nova")}>
            <Plus aria-hidden /> Novo tipo
          </Button>
        }
      >
        Tipos de punição
      </Titulo>
      <p className="mb-4 text-sm text-muted-foreground">
        Desativar tira o tipo do formulário de despacho; os despachos antigos continuam com ele.
      </p>

      {consulta.isPending ? (
        <Carregando />
      ) : consulta.isError ? (
        <ErroCarregar erro={consulta.error} tentarDeNovo={() => void consulta.refetch()} />
      ) : consulta.data.length === 0 ? (
        <Vazio>Nenhum tipo de punição cadastrado.</Vazio>
      ) : (
        <TabelaResponsiva
          itens={consulta.data}
          colunas={colunas}
          chave={(p) => p.id}
          legenda="Tipos de punição"
        />
      )}

      <Dialog open={editando !== null} onOpenChange={(valor) => !valor && setEditando(null)}>
        <DialogContent>
          {editando !== null && (
            <FormularioPunicao
              key={editando === "nova" ? "nova" : editando.id}
              punicao={editando === "nova" ? null : editando}
              onClose={() => setEditando(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

const schema = z.object({ nome: z.string().trim().min(1, "Informe o nome.").max(60) });

function FormularioPunicao({
  punicao,
  onClose,
}: {
  punicao: AdminPunicao | null;
  onClose: () => void;
}) {
  const salvar = useSalvarPunicao();
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { nome: punicao?.nome ?? "" },
  });

  const enviar = form.handleSubmit(({ nome }) =>
    salvar.mutate(
      { id: punicao?.id, nome },
      {
        onSuccess: () => {
          toast.success(punicao ? "Tipo de punição renomeado." : "Tipo de punição criado.");
          onClose();
        },
        onError: (erro) => aplicarErrosNosCampos(erro, form.setError, ["nome"]),
      },
    ),
  );

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      <DialogHeader>
        <DialogTitle>{punicao ? "Renomear tipo de punição" : "Novo tipo de punição"}</DialogTitle>
        {punicao && (
          <DialogDescription>
            O novo nome aparece também nos {punicao.total_despachos} despachos que já usam este
            tipo.
          </DialogDescription>
        )}
      </DialogHeader>
      <Campo rotulo="Nome" erro={form.formState.errors.nome}>
        {(props) => <Input {...props} {...form.register("nome")} placeholder="Pernoite" />}
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
