import { zodResolver } from "@hookform/resolvers/zod";
import { LogIn } from "lucide-react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router";
import { z } from "zod";

import { useLogin, useSessao } from "@/auth/sessao";
import { Campo, ErroFormulario, InputSenha } from "@/components/formulario";
import brasao from "@/assets/brasao-apmgd.webp";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const schema = z.object({
  numerica: z.string().trim().min(1, "Informe a numérica."),
  senha: z.string().min(1, "Informe a senha."),
});

type Dados = z.infer<typeof schema>;

export function Login() {
  const sessao = useSessao();
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = (location.state as { de?: string } | null)?.de ?? "/";

  const form = useForm<Dados>({
    resolver: zodResolver(schema),
    defaultValues: { numerica: "", senha: "" },
  });
  const { errors } = form.formState;

  if (sessao.data) return <Navigate to={destino} replace />;

  const enviar = form.handleSubmit((dados) =>
    login.mutate(dados, {
      onSuccess: () => navigate(destino, { replace: true }),
      onError: () => form.resetField("senha"),
    }),
  );

  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-[15px] bg-superficie p-6 shadow-[0_4px_10px_rgba(0,0,0,0.5)] sm:p-8">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <img src={brasao} alt="" className="size-20 object-contain" />
          <p className="font-marca text-3xl font-black tracking-wide text-primary">MAPPA</p>
          <h1 className="text-lg font-bold">Entrar no sistema</h1>
        </div>

        <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
          <Campo rotulo="Numérica" erro={errors.numerica}>
            {(props) => (
              <Input
                {...props}
                {...form.register("numerica")}
                autoComplete="username"
                autoCapitalize="none"
              />
            )}
          </Campo>
          <Campo rotulo="Senha" erro={errors.senha}>
            {(props) => (
              <InputSenha {...props} {...form.register("senha")} autoComplete="current-password" />
            )}
          </Campo>

          <ErroFormulario erro={login.error} />

          <Button type="submit" size="lg" disabled={login.isPending}>
            <LogIn aria-hidden />
            {login.isPending ? "Entrando…" : "Entrar"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Esqueceu a senha? Procure a administração do curso para redefini-la.
        </p>
      </div>
    </main>
  );
}
