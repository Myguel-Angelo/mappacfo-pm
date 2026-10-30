import { Link } from "react-router";

import { Button } from "@/components/ui/button";

export function NaoEncontrada() {
  return (
    <section className="flex flex-col items-center gap-3 py-10 text-center">
      <h1 className="text-xl font-bold">Página não encontrada</h1>
      <p className="text-muted-foreground">O endereço não existe ou foi digitado errado.</p>
      <Button asChild variant="outline">
        <Link to="/">Voltar ao início</Link>
      </Button>
    </section>
  );
}
