# Build the static VitePress site, then serve it with the local-AI assistant.
FROM node:22-slim AS build
WORKDIR /src
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run docs:build

FROM python:3.12-slim
WORKDIR /app
COPY . .
COPY --from=build /src/.vitepress/dist /app/.vitepress/dist
RUN pip install --no-cache-dir -r requirements.txt
ENV WIKI_ROOT=/app
ENV WIKI_DIST=/app/.vitepress/dist
EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
