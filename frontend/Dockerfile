# Build de produção do frontend. Na fase 8 a etapa "dist" é copiada para a imagem do Caddy:
#   COPY --from=frontend /  /srv
# Para extrair localmente: docker build --target dist --output type=local,dest=dist .

FROM node:24-slim AS deps
WORKDIR /app
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM deps AS build
COPY . .
RUN pnpm build

# Só os arquivos estáticos, sem node nem node_modules.
FROM scratch AS dist
COPY --from=build /app/dist /
