import { Route, Routes } from "react-router";

import { RotaProtegida } from "@/auth/RotaProtegida";
import { Layout } from "@/components/Layout";
import { Cadetes } from "@/pages/cadetes/Cadetes";
import { Inicio } from "@/pages/inicio/Inicio";
import { Login } from "@/pages/login/Login";
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
        <Route
          path="cadetes"
          element={
            <RotaProtegida permissao="anotacoes.anotar">
              <Cadetes />
            </RotaProtegida>
          }
        />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
