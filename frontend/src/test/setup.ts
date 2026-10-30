import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { servidor } from "@/test/servidor";

beforeAll(() => {
  servidor.listen({ onUnhandledFrame: "error" });
  // O cliente usa caminhos relativos (/api/...), como no navegador; no Node o fetch exige
  // URL absoluta. Resolve contra a origem do jsdom depois que o MSW instalou o dele.
  const fetchMsw = globalThis.fetch;
  globalThis.fetch = (entrada, init) =>
    fetchMsw(
      typeof entrada === "string" && entrada.startsWith("/")
        ? new URL(entrada, window.location.origin)
        : entrada,
      init,
    );
});

afterEach(() => {
  cleanup();
  servidor.resetHandlers();
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

afterAll(() => servidor.close());
