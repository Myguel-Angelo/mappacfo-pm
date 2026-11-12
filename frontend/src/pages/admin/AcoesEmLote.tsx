import { ArrowRightLeft, PencilLine, PencilOff, UserCheck, UserX, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useAdminTurmas, useMoverCadetes, useUsuariosEmLote, type AcaoEmLote } from "@/api/admin";
import type { AdminUsuario } from "@/api/tipos";
import { SelectNativo } from "@/components/anotacoes";
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
import { DialogConfirmar } from "@/pages/admin/comum";

// Ações nos usuários marcados na lista: uma barra presa ao rodapé da tela e um diálogo de
// confirmação por ação. A API faz tudo ou nada.

const TEXTOS: Record<
  AcaoEmLote,
  { titulo: string; rotulo: string; corpo: string; feito: string; perigo?: boolean }
> = {
  desativar: {
    titulo: "Desativar usuários",
    rotulo: "Desativar",
    corpo:
      "Eles não conseguem mais entrar e as sessões abertas são encerradas. Nada é apagado: dá para reativar depois.",
    feito: "desativado(s)",
    perigo: true,
  },
  reativar: {
    titulo: "Reativar usuários",
    rotulo: "Reativar",
    corpo: "Eles voltam a conseguir entrar com a senha que tinham.",
    feito: "reativado(s)",
  },
  permitir_anotar: {
    titulo: "Permitir anotar",
    rotulo: "Permitir",
    corpo: "Eles passam a poder anotar cadetes, como o cadete anotador.",
    feito: "com permissão de anotar",
  },
  retirar_anotar: {
    titulo: "Retirar permissão de anotar",
    rotulo: "Retirar",
    corpo:
      "A permissão individual de anotar é retirada. Quem anota pelo perfil (oficial, comandante) continua anotando.",
    feito: "sem a permissão individual de anotar",
  },
};

/** Até 8 nomes; o resto vira "e mais N". */
function Nomes({ usuarios }: { usuarios: AdminUsuario[] }) {
  const visiveis = usuarios.slice(0, 8);
  return (
    <ul className="list-inside list-disc text-sm text-foreground">
      {visiveis.map((u) => (
        <li key={u.id}>
          {u.numerica} — {u.nome}
        </li>
      ))}
      {usuarios.length > visiveis.length && (
        <li className="list-none text-muted-foreground">
          e mais {usuarios.length - visiveis.length}
        </li>
      )}
    </ul>
  );
}

export function AcoesEmLote({
  usuarios,
  onConcluir,
}: {
  usuarios: AdminUsuario[];
  onConcluir: () => void;
}) {
  const [acao, setAcao] = useState<AcaoEmLote | "mover" | null>(null);
  const lote = useUsuariosEmLote();

  if (usuarios.length === 0) return null;

  // Só aparece o botão que muda alguém: desativar se houver algum ativo, e assim por diante.
  const soCadetes = usuarios.every((u) => u.grupos.includes("Cadete"));
  const algumAtivo = usuarios.some((u) => u.ativo);
  const algumInativo = usuarios.some((u) => !u.ativo);
  const algumAnota = usuarios.some((u) => u.anotar);
  const algumSemAnotar = usuarios.some((u) => !u.anotar);

  function fechar() {
    setAcao(null);
    lote.reset();
  }

  function confirmar() {
    if (acao === null || acao === "mover") return;
    lote.mutate(
      { usuario_ids: usuarios.map((u) => u.id), acao },
      {
        onSuccess: ({ quantidade }) => {
          toast.success(`${quantidade} usuário(s) ${TEXTOS[acao].feito}.`);
          fechar();
          onConcluir();
        },
      },
    );
  }

  const textos = acao && acao !== "mover" ? TEXTOS[acao] : null;

  return (
    <>
      <section
        aria-label="Ações nos selecionados"
        className="sticky bottom-3 z-10 mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-primary/30 bg-card p-3 shadow-lg"
      >
        <p className="w-full text-sm font-bold sm:mr-auto sm:w-auto">
          {usuarios.length} {usuarios.length === 1 ? "selecionado" : "selecionados"}
        </p>
        <Button
          size="sm"
          variant="outline"
          disabled={!soCadetes}
          title={soCadetes ? undefined : "Só cadetes mudam de turma"}
          onClick={() => setAcao("mover")}
        >
          <ArrowRightLeft aria-hidden /> Mudar turma
        </Button>
        {algumSemAnotar && (
          <Button size="sm" variant="outline" onClick={() => setAcao("permitir_anotar")}>
            <PencilLine aria-hidden /> Permitir anotar
          </Button>
        )}
        {algumAnota && (
          <Button size="sm" variant="outline" onClick={() => setAcao("retirar_anotar")}>
            <PencilOff aria-hidden /> Retirar anotar
          </Button>
        )}
        {algumInativo && (
          <Button size="sm" variant="outline" onClick={() => setAcao("reativar")}>
            <UserCheck aria-hidden /> Reativar
          </Button>
        )}
        {algumAtivo && (
          <Button size="sm" variant="destructive" onClick={() => setAcao("desativar")}>
            <UserX aria-hidden /> Desativar
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={onConcluir}>
          <X aria-hidden /> Limpar seleção
        </Button>
      </section>

      <DialogConfirmar
        aberto={textos !== null}
        titulo={textos?.titulo ?? ""}
        rotulo={textos ? `${textos.rotulo} (${usuarios.length})` : ""}
        perigo={textos?.perigo}
        pendente={lote.isPending}
        erro={lote.error}
        onConfirmar={confirmar}
        onClose={fechar}
      >
        <p>{textos?.corpo}</p>
        <Nomes usuarios={usuarios} />
      </DialogConfirmar>

      <DialogMover
        aberto={acao === "mover"}
        cadetes={usuarios}
        onClose={fechar}
        onConcluir={onConcluir}
      />
    </>
  );
}

function DialogMover({
  aberto,
  cadetes,
  onClose,
  onConcluir,
}: {
  aberto: boolean;
  cadetes: AdminUsuario[];
  onClose: () => void;
  onConcluir: () => void;
}) {
  const turmas = useAdminTurmas();
  const mover = useMoverCadetes();
  const [destino, setDestino] = useState("");

  function fechar() {
    setDestino("");
    mover.reset();
    onClose();
  }

  return (
    <Dialog open={aberto} onOpenChange={(valor) => !valor && fechar()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Mudar turma</DialogTitle>
          <DialogDescription>
            {cadetes.length} cadete(s) vão para a turma escolhida. A mudança fica na auditoria.
          </DialogDescription>
        </DialogHeader>
        <label className="flex flex-col gap-1 text-sm font-bold">
          Turma de destino
          <SelectNativo value={destino} onChange={(e) => setDestino(e.target.value)}>
            <option value="">Escolha a turma</option>
            {turmas.data
              ?.filter((t) => t.ativa)
              .map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nome}
                </option>
              ))}
          </SelectNativo>
        </label>
        <Nomes usuarios={cadetes} />
        <ErroFormulario erro={mover.error} />
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancelar</Button>
          </DialogClose>
          <Button
            variant="sucesso"
            disabled={mover.isPending || !destino}
            onClick={() =>
              mover.mutate(
                { cadete_ids: cadetes.map((c) => c.id), destino_id: Number(destino) },
                {
                  onSuccess: ({ quantidade }) => {
                    toast.success(`${quantidade} cadete(s) mudaram de turma.`);
                    fechar();
                    onConcluir();
                  },
                },
              )
            }
          >
            {mover.isPending ? "Aguarde…" : `Mover (${cadetes.length})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
