import {
  BookOpen,
  FileCheck,
  FileText,
  KeyRound,
  LogOut,
  Menu,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router";

import type { Me, Permissao } from "@/api/tipos";
import { temPermissao, useLogout, useUsuario } from "@/auth/sessao";
import { cn } from "@/lib/utils";

type ItemMenu = {
  rota: string;
  rotulo: string;
  icone: LucideIcon;
  /** Quem vê o item: uma permissão, ou uma regra própria. Sem nada, todo logado vê. */
  permissao?: Permissao;
  visivel?: (usuario: Me) => boolean;
};

// O menu segue as permissões, nunca o nome do grupo.
const MENU: ItemMenu[] = [
  {
    rota: "/minhas-anotacoes",
    rotulo: "Minhas anotações",
    icone: BookOpen,
    // Só quem é de uma turma (cadete) recebe anotações.
    visivel: (usuario) => usuario.turma !== null,
  },
  { rota: "/cadetes", rotulo: "Cadetes", icone: Users, permissao: "anotacoes.anotar" },
  { rota: "/despachar", rotulo: "Anotações", icone: FileText, permissao: "anotacoes.despachar" },
  {
    rota: "/despachadas",
    rotulo: "Despachadas",
    icone: FileCheck,
    permissao: "anotacoes.despachar",
  },
  { rota: "/trocar-senha", rotulo: "Alterar senha", icone: KeyRound },
];

function itemVisivel(item: ItemMenu, usuario: Me) {
  if (item.permissao) return temPermissao(usuario, item.permissao);
  return item.visivel?.(usuario) ?? true;
}

export function Layout() {
  const usuario = useUsuario();
  const logout = useLogout();
  const [aberto, setAberto] = useState(false);

  const itens = usuario.deve_trocar_senha ? [] : MENU.filter((item) => itemVisivel(item, usuario));

  return (
    <div className="flex min-h-svh flex-col">
      <header className="fixed inset-x-0 top-0 z-40 border-b border-border bg-superficie shadow-sm">
        <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-4">
          <Link
            to="/"
            className="font-marca text-2xl font-black tracking-wide text-primary"
            aria-label="MAPPA, início"
          >
            MAPPA
          </Link>
          <button
            type="button"
            className="inline-flex size-10 items-center justify-center rounded-md text-primary min-[950px]:hidden"
            aria-expanded={aberto}
            aria-controls="menu-principal"
            aria-label={aberto ? "Fechar menu" : "Abrir menu"}
            onClick={() => setAberto((v) => !v)}
          >
            {aberto ? <X aria-hidden /> : <Menu aria-hidden />}
          </button>
          <nav
            id="menu-principal"
            aria-label="Menu principal"
            className={cn(
              "absolute inset-x-0 top-14 border-b border-border bg-superficie shadow-md",
              "min-[950px]:static min-[950px]:block min-[950px]:border-0 min-[950px]:shadow-none",
              aberto ? "block" : "hidden",
            )}
          >
            <ul className="flex flex-col px-2 py-2 min-[950px]:flex-row min-[950px]:items-center min-[950px]:gap-1 min-[950px]:p-0">
              {itens.map((item) => (
                <li key={item.rota}>
                  <NavLink
                    to={item.rota}
                    onClick={() => setAberto(false)}
                    className={({ isActive }) =>
                      cn(
                        "group relative flex items-center gap-2 rounded-md px-3 py-3 font-bold text-primary min-[950px]:py-2",
                        isActive && "bg-accent",
                      )
                    }
                  >
                    <item.icone className="size-4" aria-hidden />
                    {item.rotulo}
                    {/* Sublinhado animado do sistema antigo */}
                    <span
                      aria-hidden
                      className="absolute inset-x-3 bottom-1 hidden h-0.5 origin-left scale-x-0 bg-destaque-menu transition-transform group-hover:scale-x-100 min-[950px]:block"
                    />
                  </NavLink>
                </li>
              ))}
              <li>
                <button
                  type="button"
                  className="flex w-full items-center gap-2 rounded-md px-3 py-3 font-bold text-sair hover:bg-black/5 min-[950px]:py-2"
                  onClick={() => logout.mutate()}
                  disabled={logout.isPending}
                >
                  <LogOut className="size-4" aria-hidden />
                  Sair
                </button>
              </li>
            </ul>
          </nav>
        </div>
      </header>

      <main className="mx-auto mt-14 w-full max-w-[1200px] flex-1 px-2 py-4 sm:px-4 sm:py-8">
        <div className="rounded-[15px] bg-superficie p-4 shadow-[0_4px_10px_rgba(0,0,0,0.5)] sm:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
