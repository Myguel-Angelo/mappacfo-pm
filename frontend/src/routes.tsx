import { Route, Routes } from "react-router";

import { RotaProtegida } from "@/auth/RotaProtegida";
import { Layout } from "@/components/Layout";
import { Inicio } from "@/pages/inicio/Inicio";
import { Login } from "@/pages/login/Login";
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
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
