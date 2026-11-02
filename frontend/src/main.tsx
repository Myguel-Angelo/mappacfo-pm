import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { garantirCsrf } from "@/api/client";
import { criarQueryClient } from "@/api/queryClient";
import { Toaster } from "@/components/ui/sonner";
import { Rotas } from "@/routes";
import "./index.css";

const queryClient = criarQueryClient();

// Pede o cookie csrftoken logo ao abrir; o cliente confere de novo antes de cada escrita.
void garantirCsrf();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Rotas />
      </BrowserRouter>
      <Toaster richColors position="top-center" />
    </QueryClientProvider>
  </StrictMode>,
);
