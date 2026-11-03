# Estágio 1: compila o editor (Vue Flow). Node só existe aqui — a imagem final
# não leva nada disso, só o HTML e o JS prontos.
FROM node:22-slim AS editor
WORKDIR /build
COPY editor/package.json editor/package-lock.json* ./
RUN npm ci --silent || npm install --silent
COPY editor/ ./
RUN npx vite build --outDir /editor-dist --emptyOutDir

# Estágio 2: a aplicação
FROM python:3.12-slim

# Vincula a imagem ao repositório no ghcr. Sem este label o pacote fica solto e o
# GITHUB_TOKEN do Actions não consegue publicar nele (denied: write_package) — foi
# o que derrubou as duas primeiras tentativas do workflow.
LABEL org.opencontainers.image.source="https://github.com/cadubezerrapro/comentaeuquero"

WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY --from=editor /editor-dist ./app/static/editor

# Roda como usuário comum, não root: se alguém achar uma falha no app, não ganha a
# máquina de brinde. O volume /data nasce com o dono certo.
RUN useradd --system --uid 10001 --home-dir /srv/app ceq \
    && mkdir -p /data && chown -R ceq:ceq /data /srv/app
USER ceq

ENV DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
