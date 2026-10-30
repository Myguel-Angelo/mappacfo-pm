import { useUsuario } from "@/auth/sessao";

export function Inicio() {
  const usuario = useUsuario();
  return (
    <h1 className="text-xl font-bold text-primary">
      Bem-vindo(a) ao sistema, {usuario.perfil} {usuario.nome}
    </h1>
  );
}
