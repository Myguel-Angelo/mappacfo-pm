import { Copy, KeyRound } from "lucide-react";
import { toast } from "sonner";

import { ErroFormulario } from "@/components/formulario";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

// Peças repetidas nas telas do painel.

type ConfirmarProps = {
  aberto: boolean;
  titulo: string;
  children: React.ReactNode;
  rotulo: string;
  perigo?: boolean;
  pendente: boolean;
  erro: unknown;
  onConfirmar: () => void;
  onClose: () => void;
};

/** Confirmação para ações sensíveis (desativar, resetar senha, formar turma). */
export function DialogConfirmar({
  aberto,
  titulo,
  children,
  rotulo,
  perigo = false,
  pendente,
  erro,
  onConfirmar,
  onClose,
}: ConfirmarProps) {
  return (
    <Dialog open={aberto} onOpenChange={(valor) => !valor && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription asChild>
            <div className="flex flex-col gap-2">{children}</div>
          </DialogDescription>
        </DialogHeader>
        <ErroFormulario erro={erro} />
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancelar</Button>
          </DialogClose>
          <Button variant={perigo ? "perigo" : "sucesso"} disabled={pendente} onClick={onConfirmar}>
            {pendente ? "Aguarde…" : rotulo}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export type SenhaEntregue = { numerica: string; nome: string; senha: string };

/**
 * A senha temporária só existe nesta resposta: não fica em lista, log nem cache. Fechar o
 * diálogo descarta o valor.
 */
export function DialogSenhaTemporaria({
  entrega,
  onClose,
}: {
  entrega: SenhaEntregue | null;
  onClose: () => void;
}) {
  return (
    <Dialog open={entrega !== null} onOpenChange={(valor) => !valor && onClose()}>
      <DialogContent onInteractOutside={(e) => e.preventDefault()}>
        {entrega && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <KeyRound className="size-5" aria-hidden /> Senha temporária
              </DialogTitle>
              <DialogDescription>
                {entrega.numerica} — {entrega.nome}. Entregue esta senha ao usuário: ela não será
                mostrada de novo. No primeiro acesso ele terá de criar uma senha própria.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2 rounded-lg border-2 border-dashed border-primary bg-card p-3">
              <code className="flex-1 text-center font-mono text-2xl tracking-wider text-primary">
                {entrega.senha}
              </code>
              <Button
                variant="outline"
                size="icon"
                aria-label="Copiar senha"
                onClick={() =>
                  void navigator.clipboard
                    ?.writeText(entrega.senha)
                    .then(() => toast.success("Senha copiada."))
                }
              >
                <Copy aria-hidden />
              </Button>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button>Já anotei</Button>
              </DialogClose>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function Caixa({
  rotulo,
  marcado,
  onChange,
  descricao,
}: {
  rotulo: string;
  marcado: boolean;
  onChange: (valor: boolean) => void;
  descricao?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 text-sm">
      <input
        type="checkbox"
        checked={marcado}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 size-4 accent-primary"
      />
      <span>
        <span className="font-medium">{rotulo}</span>
        {descricao && <span className="block text-muted-foreground">{descricao}</span>}
      </span>
    </label>
  );
}

export function SeloAtivo({
  ativo,
  rotulos = ["Ativo", "Inativo"],
}: {
  ativo: boolean;
  rotulos?: [string, string];
}) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
        ativo ? "bg-green-100 text-green-900" : "bg-muted text-muted-foreground",
      )}
    >
      {ativo ? rotulos[0] : rotulos[1]}
    </span>
  );
}
