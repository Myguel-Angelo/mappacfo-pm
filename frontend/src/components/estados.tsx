import { CircleAlert, Inbox, RotateCw } from "lucide-react";

import { mensagemDeErro } from "@/api/erros";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

// Os três estados que toda tela com dados da API precisa mostrar.

export function Carregando({ linhas = 3 }: { linhas?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando…</span>
      {Array.from({ length: linhas }, (_, i) => (
        <Skeleton key={i} className="h-16 w-full bg-black/10" />
      ))}
    </div>
  );
}

export function Vazio({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-black/15 px-4 py-10 text-center text-muted-foreground">
      <Inbox className="size-8" aria-hidden />
      <p>{children}</p>
    </div>
  );
}

export function ErroCarregar({ erro, tentarDeNovo }: { erro: unknown; tentarDeNovo: () => void }) {
  return (
    <Alert variant="destructive">
      <CircleAlert aria-hidden />
      <AlertTitle>Não foi possível carregar</AlertTitle>
      <AlertDescription>
        <p>{mensagemDeErro(erro)}</p>
        <Button variant="outline" size="sm" className="mt-2" onClick={tentarDeNovo}>
          <RotateCw aria-hidden /> Tentar de novo
        </Button>
      </AlertDescription>
    </Alert>
  );
}
