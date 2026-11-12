import {
  BookOpen,
  ChevronDown,
  FolderOpen,
  FileCheck,
  FileText,
  KeyRound,
  LogOut,
  Menu,
  Settings,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router";

import type { Me, Permissao } from "@/api/tipos";
import { temPermissao, useLogout, useUsuario } from "@/auth/sessao";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  {
    rota: "/mappas",
    rotulo: "Mappas",
    icone: FolderOpen,
    // Cadetes baixam os publicados; quem exporta gerencia todos.
    visivel: (usuario) => usuario.turma !== null || temPermissao(usuario, "anotacoes.exportar"),
  },
  { rota: "/cadetes", rotulo: "Cadetes", icone: Users, permissao: "anotacoes.anotar" },
  { rota: "/despachar", rotulo: "Anotações", icone: FileText, permissao: "anotacoes.despachar" },
  {
    rota: "/despachadas",
    rotulo: "Despachadas",
    icone: FileCheck,
    permissao: "anotacoes.despachar",
  },
];

function itemVisivel(item: ItemMenu, usuario: Me) {
  if (item.permissao) return temPermissao(usuario, item.permissao);
  return item.visivel?.(usuario) ?? true;
}

/** "Cap João da Silva" vira "CS": primeira e última palavra. */
function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (partes[0][0] + ultima).toUpperCase();
}

/**
 * Círculo de perfil com o nome sempre à vista; o menu dele guarda o que é da conta.
 * A foto entra depois (AvatarImage); até lá, as iniciais.
 */
function MenuPerfil({ usuario, onAbrir }: { usuario: Me; onAbrir: () => void }) {
  const logout = useLogout();
  // O painel é da conta de quem administra, não do dia a dia: fica no menu do perfil.
  const administra =
    !usuario.deve_trocar_senha && temPermissao(usuario, "contas.gerenciar_usuarios");

  return (
    <DropdownMenu onOpenChange={(aberto) => aberto && onAbrir()}>
      <DropdownMenuTrigger
        className="flex min-w-0 items-center gap-2 rounded-full py-1 pr-2 pl-1 text-primary outline-none hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50 aria-expanded:bg-accent"
        aria-label={`Menu de ${usuario.nome}`}
      >
        <Avatar className="size-8 after:border-0">
          <AvatarFallback className="bg-primary text-xs font-bold text-primary-foreground">
            {iniciais(usuario.nome)}
          </AvatarFallback>
        </Avatar>
        <span className="max-w-28 truncate text-sm font-bold sm:max-w-40 lg:max-w-28 xl:max-w-40">
          {usuario.nome}
        </span>
        <ChevronDown className="size-4 shrink-0" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="flex flex-col gap-0.5 px-2 py-1.5">
          <span className="truncate text-sm font-bold text-foreground">{usuario.nome}</span>
          <span className="truncate text-xs font-normal">
            {usuario.numerica}
            {usuario.perfil && ` · ${usuario.perfil}`}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {administra && (
          <DropdownMenuItem asChild className="px-2 py-2">
            <Link to="/admin">
              <Settings aria-hidden /> Administração
            </Link>
          </DropdownMenuItem>
        )}
        <DropdownMenuItem asChild className="px-2 py-2">
          <Link to="/trocar-senha">
            <KeyRound aria-hidden /> Alterar senha
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem
          variant="destructive"
          className="px-2 py-2"
          disabled={logout.isPending}
          onSelect={() => logout.mutate()}
        >
          <LogOut aria-hidden /> Sair
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function Layout() {
  const usuario = useUsuario();
  const [aberto, setAberto] = useState(false);

  const itens = usuario.deve_trocar_senha ? [] : MENU.filter((item) => itemVisivel(item, usuario));

  return (
    <div className="flex min-h-svh flex-col">
      <header className="fixed inset-x-0 top-0 z-40 border-b border-border bg-superficie shadow-sm">
        <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-2 px-4">
          <Link
            to="/"
            className="mr-auto font-marca text-2xl font-black tracking-wide text-primary"
            aria-label="MAPPA, início"
          >
            MAPPA
          </Link>
          <nav
            id="menu-principal"
            aria-label="Menu principal"
            className={cn(
              "absolute inset-x-0 top-14 border-b border-border bg-superficie shadow-md",
              "lg:static lg:block lg:border-0 lg:shadow-none",
              aberto && itens.length > 0 ? "block" : "hidden",
            )}
          >
            <ul className="flex flex-col px-2 py-2 lg:flex-row lg:items-center lg:gap-1 lg:p-0">
              {itens.map((item) => (
                <li key={item.rota}>
                  <NavLink
                    to={item.rota}
                    onClick={() => setAberto(false)}
                    className={({ isActive }) =>
                      cn(
                        "group relative flex items-center gap-2 rounded-md px-3 py-3 font-bold text-primary lg:px-2.5 lg:py-2",
                        isActive && "bg-accent",
                      )
                    }
                  >
                    <item.icone className="size-4" aria-hidden />
                    {item.rotulo}
                    {/* Sublinhado animado do sistema antigo */}
                    <span
                      aria-hidden
                      className="absolute inset-x-3 bottom-1 hidden h-0.5 origin-left scale-x-0 bg-destaque-menu transition-transform group-hover:scale-x-100 lg:block"
                    />
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <MenuPerfil usuario={usuario} onAbrir={() => setAberto(false)} />
          {/* Na troca de senha obrigatória não há itens: o menu do perfil basta. */}
          {itens.length > 0 && (
            <button
              type="button"
              className="inline-flex size-10 shrink-0 items-center justify-center rounded-md text-primary lg:hidden"
              aria-expanded={aberto}
              aria-controls="menu-principal"
              aria-label={aberto ? "Fechar menu" : "Abrir menu"}
              onClick={() => setAberto((v) => !v)}
            >
              {aberto ? <X aria-hidden /> : <Menu aria-hidden />}
            </button>
          )}
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
