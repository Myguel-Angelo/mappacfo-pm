import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ErroValidacao } from "@/api/erros";

/**
 * Leva os 422 do Ninja para os campos do formulário. Devolve true se tratou o erro;
 * os demais (400 com mensagem pronta, rede) ficam para o ErroFormulario.
 */
export function aplicarErrosNosCampos<T extends FieldValues>(
  erro: unknown,
  setError: UseFormSetError<T>,
  campos: readonly Path<T>[],
): boolean {
  if (!(erro instanceof ErroValidacao)) return false;
  let tratou = false;
  for (const [campo, mensagem] of Object.entries(erro.campos)) {
    const alvo = campos.find((c) => c === campo);
    if (alvo) {
      setError(alvo, { message: mensagem });
      tratou = true;
    }
  }
  return tratou;
}
