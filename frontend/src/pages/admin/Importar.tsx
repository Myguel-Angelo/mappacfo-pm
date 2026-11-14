import { Download, FileUp, RotateCcw, Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useConfirmarImportacao, useCriarPrevia } from "@/api/admin";
import type { AdminImportacao, AdminLinhaImportacao, AdminResultadoImportacao } from "@/api/tipos";
import { SelectNativo, TabelaResponsiva, Titulo, type Coluna } from "@/components/anotacoes";
import { ErroFormulario } from "@/components/formulario";
import { Paginacao } from "@/components/paginacao";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatarDataHora } from "@/lib/formato";
import { usePaginaLocal } from "@/lib/paginacao";
import { cn } from "@/lib/utils";
import { Caixa, CaixaSenha } from "@/pages/admin/comum";

const ACOES: Record<string, { rotulo: string; cor: string }> = {
  criar: { rotulo: "Criar", cor: "bg-green-100 text-green-900" },
  atualizar: { rotulo: "Atualizar", cor: "bg-secondary text-secondary-foreground" },
  ignorar: { rotulo: "Ignorar", cor: "bg-muted text-muted-foreground" },
  erro: { rotulo: "Erro", cor: "bg-red-100 text-red-900" },
};

/** Lista de logins para divulgar à turma (sem a senha). Gerada no navegador. */
function baixarLogins(resultado: AdminResultadoImportacao) {
  const escapar = (valor: string) => `"${valor.replaceAll('"', '""')}"`;
  const linhas = [
    "numerica;nome;login;turma",
    ...resultado.criados.map((c) => [c.numerica, c.nome, c.login, c.turma].map(escapar).join(";")),
  ];
  // BOM: o Excel abre o UTF-8 com os acentos certos.
  const arquivo = new Blob(["﻿" + linhas.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(arquivo);
  link.download = "logins-importacao.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}

export function Importar() {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [atualizar, setAtualizar] = useState(false);
  const [criarTurmas, setCriarTurmas] = useState(false);
  const [previa, setPrevia] = useState<AdminImportacao | null>(null);
  const [resultado, setResultado] = useState<AdminResultadoImportacao | null>(null);
  const [filtro, setFiltro] = useState("");
  const analisar = useCriarPrevia();
  const confirmar = useConfirmarImportacao();
  const linhas = previa?.linhas.filter((l) => !filtro || l.acao === filtro) ?? [];
  const pagina = usePaginaLocal(linhas, `${previa?.id}|${filtro}`);

  function recomecar() {
    setArquivo(null);
    setPrevia(null);
    setResultado(null);
    setFiltro("");
    analisar.reset();
    confirmar.reset();
  }

  if (resultado) {
    return (
      <>
        <Titulo>Importação concluída</Titulo>
        <div className="flex flex-col gap-4">
          <p>
            {resultado.criados.length} cadete(s) criado(s), {resultado.atualizados} atualizado(s) e{" "}
            {resultado.ignorados} ignorado(s).
          </p>
          {resultado.senha_temporaria && (
            <section
              aria-label="Senha temporária"
              className="flex max-w-xl flex-col gap-3 rounded-lg border bg-card p-4"
            >
              <p className="font-bold">Anote a senha temporária agora.</p>
              <p className="text-sm text-muted-foreground">
                É a mesma para os {resultado.criados.length} cadete(s) criado(s) e não fica guardada
                em lugar nenhum: some quando você sair desta tela. Cada um entra com CAD + o nome de
                guerra e é obrigado a trocar a senha no primeiro acesso.
              </p>
              <CaixaSenha senha={resultado.senha_temporaria} />
              <Button
                variant="outline"
                className="self-start"
                onClick={() => baixarLogins(resultado)}
              >
                <Download aria-hidden /> Baixar lista de logins (CSV)
              </Button>
            </section>
          )}
          <Button variant="outline" className="self-start" onClick={recomecar}>
            <RotateCcw aria-hidden /> Nova importação
          </Button>
        </div>
      </>
    );
  }

  const colunas: Coluna<AdminLinhaImportacao>[] = [
    { titulo: "Linha", className: "md:w-16", celula: (l) => l.linha },
    { titulo: "Numérica", className: "md:w-28", celula: (l) => l.numerica || "—" },
    { titulo: "Nome", celula: (l) => l.nome || "—" },
    { titulo: "Nome de guerra", className: "md:w-36", celula: (l) => l.nome_guerra || "—" },
    { titulo: "Turma", className: "md:w-28", celula: (l) => l.turma || "—" },
    {
      titulo: "Ação",
      className: "md:w-28",
      celula: (l) => (
        <Badge className={ACOES[l.acao]?.cor}>{ACOES[l.acao]?.rotulo ?? l.acao}</Badge>
      ),
    },
    {
      titulo: "Detalhes",
      className: "md:w-72",
      celula: (l) => (
        <ul className="text-xs">
          {l.erros.map((e) => (
            <li key={e} className="text-destructive">
              {e}
            </li>
          ))}
          {l.mudancas.map((m) => (
            <li key={m} className="text-muted-foreground">
              {m}
            </li>
          ))}
        </ul>
      ),
    },
  ];

  return (
    <>
      <Titulo>Importar cadetes</Titulo>

      {!previa ? (
        <form
          className="flex max-w-xl flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!arquivo) return;
            analisar.mutate(
              { arquivo, atualizar_existentes: atualizar, criar_turmas: criarTurmas },
              { onSuccess: setPrevia },
            );
          }}
        >
          <p className="text-sm">
            Envie uma planilha <strong>.xlsx</strong> ou <strong>.csv</strong> com as colunas{" "}
            <code>numerica</code>, <code>nome</code>, <code>nome_guerra</code> e <code>turma</code>{" "}
            (e <code>email</code>, opcional). O nome de guerra vai sem o CAD. Nada é gravado antes
            de você conferir a prévia.
          </p>
          <a
            href="/modelo-cadetes.csv"
            download
            className="inline-flex items-center gap-2 self-start text-sm font-bold text-primary underline"
          >
            <Download className="size-4" aria-hidden /> Baixar planilha modelo
          </a>
          <div className="flex flex-col gap-1">
            <label htmlFor="arquivo-importacao" className="text-sm font-bold">
              Planilha
            </label>
            <Input
              id="arquivo-importacao"
              type="file"
              accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
              className="h-auto py-2"
            />
          </div>
          <Caixa
            rotulo="Atualizar cadetes que já existem"
            descricao="Nome, e-mail e turma de quem já tem a numérica cadastrada. Sem isto, eles são ignorados."
            marcado={atualizar}
            onChange={setAtualizar}
          />
          <Caixa
            rotulo="Criar turmas que não existem"
            descricao="Sem isto, uma turma desconhecida vira erro na linha."
            marcado={criarTurmas}
            onChange={setCriarTurmas}
          />
          <ErroFormulario erro={analisar.error} />
          <Button type="submit" className="self-start" disabled={!arquivo || analisar.isPending}>
            <FileUp aria-hidden /> {analisar.isPending ? "Analisando…" : "Analisar planilha"}
          </Button>
        </form>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-bold">{previa.nome_arquivo}:</span>
            {Object.entries(previa.totais).map(([acao, total]) => (
              <Badge key={acao} className={cn(ACOES[acao]?.cor)}>
                {total} {ACOES[acao]?.rotulo.toLowerCase()}
              </Badge>
            ))}
            <span className="text-muted-foreground">
              · prévia válida até {formatarDataHora(previa.expira_em)}
            </span>
          </div>

          {previa.totais.erro > 0 && (
            <p className="rounded-lg bg-red-50 p-3 text-sm text-red-900">
              Há {previa.totais.erro} linha(s) com erro. Corrija a planilha e envie de novo: a
              importação só é confirmada sem erros, para nada entrar pela metade.
            </p>
          )}

          <label className="flex flex-col gap-1 text-sm font-bold sm:w-56">
            Mostrar
            <SelectNativo value={filtro} onChange={(e) => setFiltro(e.target.value)}>
              <option value="">Todas as linhas</option>
              {Object.entries(ACOES).map(([valor, { rotulo }]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </SelectNativo>
          </label>

          <TabelaResponsiva
            itens={pagina.itens}
            colunas={colunas}
            chave={(l) => l.linha}
            legenda="Prévia da importação"
          />
          <Paginacao pagina={pagina.pagina} total={pagina.total} onChange={pagina.irPara} />

          <ErroFormulario erro={confirmar.error} />

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={recomecar}>
              <RotateCcw aria-hidden /> Enviar outra planilha
            </Button>
            <Button
              variant="sucesso"
              disabled={
                previa.totais.erro > 0 ||
                previa.totais.criar + previa.totais.atualizar === 0 ||
                confirmar.isPending
              }
              onClick={() =>
                confirmar.mutate(previa.id, {
                  onSuccess: (r) => {
                    setResultado(r);
                    toast.success("Importação concluída.");
                  },
                })
              }
            >
              <Upload aria-hidden />
              {confirmar.isPending
                ? "Gravando…"
                : `Confirmar (${previa.totais.criar} novos, ${previa.totais.atualizar} atualizações)`}
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
