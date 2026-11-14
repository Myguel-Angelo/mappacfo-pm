import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useAdminTurmas, useCriarUsuario, useEditarUsuario } from "@/api/admin";
import type { AdminUsuario } from "@/api/tipos";
import { SelectNativo } from "@/components/anotacoes";
import { Campo, ErroFormulario } from "@/components/formulario";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { aplicarErrosNosCampos } from "@/lib/formulario";
import { Caixa, type SenhaEntregue } from "@/pages/admin/comum";
import { DESCRICAO_GRUPO, GRUPOS } from "@/pages/admin/grupos";

const schema = z
  .object({
    numerica: z.string().trim().min(1, "Informe a numérica.").max(20),
    nome: z.string().trim().min(1, "Informe o nome.").max(120),
    nome_guerra: z.string().trim().min(1, "Informe o nome de guerra.").max(40),
    email: z.union([z.literal(""), z.email("E-mail inválido.")]),
    turma_id: z.string(),
    grupos: z.array(z.string()),
    anotar: z.boolean(),
  })
  .refine((d) => !d.grupos.includes("Cadete") || d.turma_id !== "", {
    path: ["turma_id"],
    message: "Cadete precisa de uma turma.",
  });

type Dados = z.infer<typeof schema>;

type Props = {
  /** null: fechado; "novo": criar; usuário: editar. */
  alvo: AdminUsuario | "novo" | null;
  onClose: () => void;
  onSenha: (entrega: SenhaEntregue) => void;
};

export function DialogUsuario({ alvo, onClose, onSenha }: Props) {
  const [ultimo, setUltimo] = useState(alvo);
  if (alvo !== null && alvo !== ultimo) setUltimo(alvo);
  return (
    <Dialog open={alvo !== null} onOpenChange={(valor) => !valor && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto">
        {ultimo !== null && (
          <Formulario
            key={ultimo === "novo" ? "novo" : ultimo.id}
            usuario={ultimo === "novo" ? null : ultimo}
            onClose={onClose}
            onSenha={onSenha}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function Formulario({
  usuario,
  onClose,
  onSenha,
}: {
  usuario: AdminUsuario | null;
  onClose: () => void;
  onSenha: (entrega: SenhaEntregue) => void;
}) {
  const turmas = useAdminTurmas();
  const criar = useCriarUsuario();
  const editar = useEditarUsuario();
  const mutacao = usuario ? editar : criar;

  const form = useForm<Dados>({
    resolver: zodResolver(schema),
    defaultValues: {
      numerica: usuario?.numerica ?? "",
      nome: usuario?.nome ?? "",
      nome_guerra: usuario?.nome_guerra ?? "",
      email: usuario?.email ?? "",
      turma_id: usuario?.turma ? String(usuario.turma.id) : "",
      grupos: usuario?.grupos ?? ["Cadete"],
      anotar: usuario?.anotar ?? false,
    },
  });
  const { errors } = form.formState;
  const grupos = useWatch({ control: form.control, name: "grupos" });
  const ehCadete = grupos.includes("Cadete");

  const enviar = form.handleSubmit((dados) => {
    const corpo = {
      nome: dados.nome,
      nome_guerra: dados.nome_guerra,
      email: dados.email,
      turma_id: dados.turma_id ? Number(dados.turma_id) : null,
      grupos: dados.grupos,
      anotar: ehCadete && dados.anotar,
    };
    const aoErrar = (erro: unknown) =>
      aplicarErrosNosCampos(erro, form.setError, [
        "numerica",
        "nome",
        "nome_guerra",
        "email",
        "turma_id",
      ]);
    if (usuario) {
      editar.mutate(
        { id: usuario.id, ...corpo },
        {
          onSuccess: () => {
            toast.success("Usuário atualizado.");
            onClose();
          },
          onError: aoErrar,
        },
      );
    } else {
      criar.mutate(
        { numerica: dados.numerica, ...corpo },
        {
          onSuccess: ({ usuario: novo, senha_temporaria }) => {
            onClose();
            onSenha({ login: novo.login, nome: novo.nome, senha: senha_temporaria });
          },
          onError: aoErrar,
        },
      );
    }
  });

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      <DialogHeader>
        <DialogTitle>{usuario ? `Editar ${usuario.numerica}` : "Novo usuário"}</DialogTitle>
      </DialogHeader>

      {!usuario && (
        <Campo rotulo="Numérica" erro={errors.numerica}>
          {(props) => <Input {...props} {...form.register("numerica")} autoCapitalize="none" />}
        </Campo>
      )}
      <Campo rotulo="Nome completo" erro={errors.nome}>
        {(props) => <Input {...props} {...form.register("nome")} />}
      </Campo>
      <Campo
        rotulo="Nome de guerra"
        erro={errors.nome_guerra}
        descricao={
          ehCadete
            ? "É o login, com CAD na frente (ex.: CAD SILVA). Não precisa digitar o CAD aqui."
            : "É o login (ex.: TEN SILVA). Não pode repetir o de outro usuário."
        }
      >
        {(props) => <Input {...props} {...form.register("nome_guerra")} />}
      </Campo>
      <Campo rotulo="E-mail (opcional)" erro={errors.email}>
        {(props) => <Input {...props} {...form.register("email")} type="email" />}
      </Campo>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium">Perfis</legend>
        <Controller
          control={form.control}
          name="grupos"
          render={({ field }) => (
            <>
              {GRUPOS.map((grupo) => (
                <Caixa
                  key={grupo}
                  rotulo={grupo}
                  descricao={DESCRICAO_GRUPO[grupo]}
                  marcado={field.value.includes(grupo)}
                  onChange={(marcado) =>
                    field.onChange(
                      marcado ? [...field.value, grupo] : field.value.filter((g) => g !== grupo),
                    )
                  }
                />
              ))}
            </>
          )}
        />
      </fieldset>

      <Campo rotulo={ehCadete ? "Turma" : "Turma (opcional)"} erro={errors.turma_id}>
        {(props) => (
          <SelectNativo {...props} {...form.register("turma_id")}>
            <option value="">Sem turma</option>
            {turmas.data
              ?.filter((t) => t.ativa || String(t.id) === form.getValues("turma_id"))
              .map((turma) => (
                <option key={turma.id} value={turma.id}>
                  {turma.nome}
                  {!turma.ativa && " (arquivada)"}
                </option>
              ))}
          </SelectNativo>
        )}
      </Campo>

      {ehCadete && (
        <Controller
          control={form.control}
          name="anotar"
          render={({ field }) => (
            <Caixa
              rotulo="Pode anotar outros cadetes"
              descricao="O antigo “cadete com permissão de anotar”."
              marcado={field.value}
              onChange={field.onChange}
            />
          )}
        />
      )}

      <ErroFormulario erro={mutacao.error} />

      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">
            Cancelar
          </Button>
        </DialogClose>
        <Button type="submit" variant="sucesso" disabled={mutacao.isPending}>
          {mutacao.isPending ? "Salvando…" : usuario ? "Salvar" : "Criar e gerar senha"}
        </Button>
      </DialogFooter>
    </form>
  );
}
