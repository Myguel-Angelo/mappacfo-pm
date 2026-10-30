import { CircleAlert, Eye, EyeOff } from "lucide-react";
import { useId, useState } from "react";
import type { FieldError as ErroRhf } from "react-hook-form";

import { ErroApi, mensagemDeErro } from "@/api/erros";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

type CampoProps = {
  rotulo: string;
  erro?: ErroRhf;
  children: (props: {
    id: string;
    "aria-invalid": boolean;
    "aria-describedby"?: string;
  }) => React.ReactNode;
};

/** Label ligado ao input, e a mensagem de erro anunciada pelo leitor de tela. */
export function Campo({ rotulo, erro, children }: CampoProps) {
  const id = useId();
  const idErro = `${id}-erro`;
  return (
    <Field data-invalid={!!erro}>
      <FieldLabel htmlFor={id}>{rotulo}</FieldLabel>
      {children({ id, "aria-invalid": !!erro, "aria-describedby": erro ? idErro : undefined })}
      <FieldError id={idErro} errors={[erro]} />
    </Field>
  );
}

export function InputSenha(props: React.ComponentProps<typeof Input>) {
  const [visivel, setVisivel] = useState(false);
  return (
    <div className="relative">
      <Input {...props} type={visivel ? "text" : "password"} className="pr-11" />
      <button
        type="button"
        className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
        onClick={() => setVisivel((v) => !v)}
        aria-label={visivel ? "Esconder senha" : "Mostrar senha"}
        aria-pressed={visivel}
      >
        {visivel ? (
          <EyeOff className="size-4" aria-hidden />
        ) : (
          <Eye className="size-4" aria-hidden />
        )}
      </button>
    </div>
  );
}

/** Erro geral do formulário (o que não é de um campo específico). */
export function ErroFormulario({ erro }: { erro: unknown }) {
  if (!erro) return null;
  const lista = erro instanceof ErroApi ? erro.erros : [];
  return (
    <Alert variant="destructive">
      <CircleAlert aria-hidden />
      <AlertDescription>
        <p>{mensagemDeErro(erro)}</p>
        {lista.length > 0 && (
          <ul className="mt-1 list-disc pl-4">
            {lista.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </AlertDescription>
    </Alert>
  );
}
