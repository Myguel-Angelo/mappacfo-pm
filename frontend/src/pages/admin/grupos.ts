// Grupos do sistema (criados por migração) e o que cada um permite, para o painel.

export const GRUPOS = ["Cadete", "Oficial", "Comandante", "Administrador"] as const;

export const DESCRICAO_GRUPO: Record<(typeof GRUPOS)[number], string> = {
  Cadete: "Recebe anotações; vê as próprias e os mappas publicados.",
  Oficial: "Anota cadetes e consulta as anotações.",
  Comandante: "Despacha, compensa, anula e gera o mappa.",
  Administrador: "Acessa esta área de administração.",
};
