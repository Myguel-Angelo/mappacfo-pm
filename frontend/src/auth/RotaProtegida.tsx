import { ShieldX } from "lucide-react";
import { Link, Navigate, Outlet, useLocation } from "react-router";

import type { Permissao } from "@/api/tipos";
import { temPermissao, useSessao } from "@/auth/sessao";
import { Carregando, ErroCarregar } from "@/components/estados";
import { Button } from "@/components/ui/button";

type Props = {
  permissao?: Permissao;
  children?: React.ReactNode;
};

/**
 * Sem sessão → /login; troca de senha pendente → /trocar-senha; sem a permissão → 403.
 * Esconder a tela não é segurança: a API nega do mesmo jeito.
 */
export function RotaProtegida({ permissao, children }: Props) {
  const sessao = useSessao();
  const { pathname } = useLocation();

  if (sessao.isPending) {
    return (
      <div className="mx-auto max-w-md p-6">
        <Carregando />
      </div>
    );
  }
  if (sessao.isError) {
    return (
      <div className="mx-auto max-w-md p-6">
        <ErroCarregar erro={sessao.error} tentarDeNovo={() => void sessao.refetch()} />
      </div>
    );
  }

  const usuario = sessao.data;
  if (!usuario) return <Navigate to="/login" replace state={{ de: pathname }} />;
  if (usuario.deve_trocar_senha && pathname !== "/trocar-senha") {
    return <Navigate to="/trocar-senha" replace />;
  }
  if (permissao && !temPermissao(usuario, permissao)) return <SemAcesso />;

  return children ?? <Outlet />;
}

export function SemAcesso() {
  return (
    <section className="flex flex-col items-center gap-3 py-10 text-center">
      <ShieldX className="size-12 text-destructive" aria-hidden />
      <h1 className="text-xl font-bold">Acesso negado</h1>
      <p className="text-muted-foreground">Seu perfil não tem permissão para abrir esta página.</p>
      <Button asChild variant="outline">
        <Link to="/">Voltar ao início</Link>
      </Button>
    </section>
  );
}
