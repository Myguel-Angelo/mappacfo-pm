import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { z } from "zod";

import { useTrocarSenha, useUsuario } from "@/auth/sessao";
import { Campo, ErroFormulario, InputSenha } from "@/components/formulario";
import { aplicarErrosNosCampos } from "@/lib/formulario";
import { Button } from "@/components/ui/button";

// Espelha o básico dos validadores do Django; a API confere o resto (senha comum, parecida
// com os dados do usuário) e devolve a lista em `erros`.
const schema = z
  .object({
    senha_atual: z.string().min(1, "Informe a senha atual."),
    nova_senha: z
      .string()
      .min(8, "A nova senha precisa ter pelo menos 8 caracteres.")
      .refine((s) => !/^\d+$/.test(s), "A nova senha não pode ter só números."),
    confirmacao: z.string().min(1, "Repita a nova senha."),
  })
  .refine((d) => d.nova_senha === d.confirmacao, {
    path: ["confirmacao"],
    message: "A confirmação não confere com a nova senha.",
  });

type Dados = z.infer<typeof schema>;

const REGRAS = [
  "Pelo menos 8 caracteres.",
  "Não pode ter só números.",
  "Não pode ser uma senha comum (como 12345678 ou senha123).",
  "Não pode ser parecida com sua numérica, nome ou e-mail.",
];

export function TrocarSenha() {
  const usuario = useUsuario();
  const trocar = useTrocarSenha();
  const navigate = useNavigate();

  const form = useForm<Dados>({
    resolver: zodResolver(schema),
    defaultValues: { senha_atual: "", nova_senha: "", confirmacao: "" },
  });
  const { errors } = form.formState;

  const enviar = form.handleSubmit((dados) =>
    trocar.mutate(dados, {
      onSuccess: () => {
        toast.success("Senha alterada.");
        navigate("/", { replace: true });
      },
      onError: (erro) =>
        aplicarErrosNosCampos(erro, form.setError, ["senha_atual", "nova_senha", "confirmacao"]),
    }),
  );

  return (
    <section className="mx-auto flex max-w-md flex-col gap-6">
      <h1 className="text-2xl font-bold text-primary">Alterar senha</h1>

      {usuario.deve_trocar_senha && (
        <div className="rounded-lg border border-primary/30 bg-accent p-4 text-sm text-accent-foreground">
          <p className="font-bold">Troca de senha obrigatória</p>
          <p>Para continuar usando o sistema, defina uma senha nova, só sua.</p>
        </div>
      )}

      <div className="rounded-lg bg-card p-4 text-sm">
        <p className="font-bold">A nova senha precisa seguir estas regras:</p>
        <ul className="mt-1 list-disc pl-5 text-muted-foreground">
          {REGRAS.map((regra) => (
            <li key={regra}>{regra}</li>
          ))}
        </ul>
      </div>

      <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <Campo rotulo="Senha atual" erro={errors.senha_atual}>
          {(props) => (
            <InputSenha
              {...props}
              {...form.register("senha_atual")}
              autoComplete="current-password"
            />
          )}
        </Campo>
        <Campo rotulo="Nova senha" erro={errors.nova_senha}>
          {(props) => (
            <InputSenha {...props} {...form.register("nova_senha")} autoComplete="new-password" />
          )}
        </Campo>
        <Campo rotulo="Confirme a nova senha" erro={errors.confirmacao}>
          {(props) => (
            <InputSenha {...props} {...form.register("confirmacao")} autoComplete="new-password" />
          )}
        </Campo>

        <ErroFormulario erro={trocar.error} />

        <Button type="submit" size="lg" variant="sucesso" disabled={trocar.isPending}>
          {trocar.isPending ? "Salvando…" : "Salvar nova senha"}
        </Button>
      </form>
    </section>
  );
}
