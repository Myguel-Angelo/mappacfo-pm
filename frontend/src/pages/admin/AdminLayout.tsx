import { NavLink, Outlet } from "react-router";

import { cn } from "@/lib/utils";

const ABAS = [
  { rota: "usuarios", rotulo: "Usuários" },
  { rota: "turmas", rotulo: "Turmas" },
  { rota: "punicoes", rotulo: "Punições" },
  { rota: "importar", rotulo: "Importar cadetes" },
  { rota: "auditoria", rotulo: "Auditoria" },
];

export function AdminLayout() {
  return (
    <>
      <p className="mb-1 text-sm font-bold tracking-wide text-muted-foreground uppercase">
        Administração
      </p>
      {/* No celular as abas rolam na horizontal em vez de quebrar a linha. */}
      <nav aria-label="Seções da administração" className="-mx-1 mb-6 overflow-x-auto">
        <ul className="flex min-w-max gap-1 border-b border-black/10 px-1">
          {ABAS.map((aba) => (
            <li key={aba.rota}>
              <NavLink
                to={aba.rota}
                className={({ isActive }) =>
                  cn(
                    "-mb-px block border-b-2 px-3 py-2 text-sm font-bold",
                    isActive
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-primary",
                  )
                }
              >
                {aba.rotulo}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </>
  );
}
