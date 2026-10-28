# LIFELINE AI — container image
#
# Stage 1 builds the Next.js static export. Stage 2 serves it with the Python
# stdlib and runs the real engine for POST /api/allocate. No Node process is
# needed at run time.
#
#   docker build -t lifeline-ai .
#   docker run --rm -p 8080:8080 -e NEBIUS_API_KEY=... lifeline-ai
#
# The image never contains a key. Pass it at run time, or mount it as a secret
# in Nebius AI Cloud.

FROM node:20-alpine AS ui
WORKDIR /build/ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    LIFELINE_OFFLINE=0

# The exported site, built above.
COPY --from=ui /build/ui/out /app/ui/out

# The engine, artefacts and server.
COPY . /app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4)"

CMD ["python", "deploy/serve.py", "--host", "0.0.0.0"]
