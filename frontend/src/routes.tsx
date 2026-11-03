import { Navigate, Route, Routes } from "react-router";

import { RotaProtegida } from "@/auth/RotaProtegida";
import { Layout } from "@/components/Layout";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { Auditoria } from "@/pages/admin/Auditoria";
import { Importar } from "@/pages/admin/Importar";
import { Punicoes } from "@/pages/admin/Punicoes";
import { Turmas } from "@/pages/admin/Turmas";
import { Usuarios } from "@/pages/admin/Usuarios";
import { Cadetes } from "@/pages/cadetes/Cadetes";
import { Despachadas } from "@/pages/despachadas/Despachadas";
import { Despachar } from "@/pages/despachar/Despachar";
import { Inicio } from "@/pages/inicio/Inicio";
import { Login } from "@/pages/login/Login";
import { Mappas } from "@/pages/mappas/Mappas";
import { MinhasAnotacoes } from "@/pages/minhas-anotacoes/MinhasAnotacoes";
import { NaoEncontrada } from "@/pages/NaoEncontrada";
import { TrocarSenha } from "@/pages/trocar-senha/TrocarSenha";

export function Rotas() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RotaProtegida>
            <Layout />
          </RotaProtegida>
        }
      >
        <Route index element={<Inicio />} />
        <Route path="trocar-senha" element={<TrocarSenha />} />
        <Route path="minhas-anotacoes" element={<MinhasAnotacoes />} />
        <Route path="mappas" element={<Mappas />} />
        <Route
          path="cadetes"
          element={
            <RotaProtegida permissao="anotacoes.anotar">
              <Cadetes />
            </RotaProtegida>
          }
        />
        <Route element={<RotaProtegida permissao="anotacoes.despachar" />}>
          <Route path="despachar" element={<Despachar />} />
          <Route path="despachadas" element={<Despachadas />} />
        </Route>
        <Route
          path="admin"
          element={
            <RotaProtegida permissao="contas.gerenciar_usuarios">
              <AdminLayout />
            </RotaProtegida>
          }
        >
          <Route index element={<Navigate to="usuarios" replace />} />
          <Route path="usuarios" element={<Usuarios />} />
          <Route path="turmas" element={<Turmas />} />
          <Route path="punicoes" element={<Punicoes />} />
          <Route path="importar" element={<Importar />} />
          <Route path="auditoria" element={<Auditoria />} />
        </Route>
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
