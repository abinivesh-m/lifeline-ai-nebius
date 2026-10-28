# Deploying LIFELINE AI

Two targets, for two different jobs:

| Target | What runs | What works |
| --- | --- | --- |
| **Vercel** | the static Next.js export | the whole page, media, three.js scenes, every baked artefact |
| **Nebius AI Cloud** | the Docker image + `deploy/serve.py` | everything above **plus** `POST /api/allocate` and `GET /api/health` |

The page is designed to be complete without a backend. The live allocation route is the extra, not the
product.

---

## 1. Vercel — the static demo

**Live: <https://lifeline-ai-nebius.vercel.app>** — verified 200 anonymously on 28 Oct 2026 (page,
`/data/lifeline.json`, `/videos/flood.mp4`).

The UI is exported with `output: "export"` and `trailingSlash: true`, so `npm run build` writes a plain
folder of files to `ui/out`. There is no Node server at run time.

### From the dashboard

1. **Add New → Project**, import `abinivesh-m/lifeline-ai-nebius`.
2. Set **Root Directory** to `ui`.
3. Framework preset: **Next.js** (or **Other** if the preset insists on a server build).
4. Build command: `npm run build`.
5. Output directory: `out`.
6. Deploy.

### From the CLI

```bash
npm install -g vercel
vercel login
cd ui
vercel --prod
```

`vercel login` opens a browser and stores a token locally. In CI, set `VERCEL_TOKEN` instead. No key from
this repository is needed for the static build.

### What does not work on Vercel

`POST /api/allocate` is a Python route served by `deploy/serve.py`. A static Vercel deployment has no
Python process, so the **live endpoint panel is not rendered at all** on Vercel — there is no dead
button. Everything else — the plan, the evidence rows, the audio, the proofs — is already in
`ui/public/data/lifeline.json` and the media folder. The same call runs locally with
`python allocator.py --mode auto`, or in the container, where the panel appears automatically.

---

## 2. Nebius AI Cloud — the full demo

### Build the image

```bash
docker build -t lifeline-ai:1.0 .
docker run --rm -p 8080:8080 \
  -e NEBIUS_API_KEY="$NEBIUS_API_KEY" \
  lifeline-ai:1.0
```

Open `http://127.0.0.1:8080`. The container serves the exported UI and the live route.

The image has two stages:

- `node:20-alpine` runs `npm ci && npm run build` in `ui/`.
- `python:3.12-slim` copies `ui/out`, the engine and the artefacts, then runs
  `python deploy/serve.py --host 0.0.0.0`.

No key is baked into the image. `NEBIUS_API_KEY` is read at run time by `allocator.load_env()`.

### Push to a registry

```bash
docker tag lifeline-ai:1.0 <registry>/<namespace>/lifeline-ai:1.0
docker push <registry>/<namespace>/lifeline-ai:1.0
```

Use the registry your Nebius project can pull from.

### Create the Serverless Endpoint

In the Nebius AI Cloud console:

1. **Serverless Endpoints → Create endpoint**.
2. Image: the tag you pushed.
3. Container port: **8080** (or set `PORT`; `deploy/serve.py` reads it).
4. Environment / secret: `NEBIUS_API_KEY` from SecretStash. Do **not** put the value in the image or the
   repository.
5. Health check path: **`/api/health`**. It returns JSON and spends no tokens.
6. Optional: `LIFELINE_OFFLINE=0`, `NEBIUS_MODEL_*` overrides if the catalogue changes.

Once the endpoint is healthy, `POST /api/allocate` with `{"mode":"auto"}` runs the real engine: evidence
from `town.json`, a Nemotron 3 Ultra proposal when the key is present, and the deterministic validator
either way.

### Smoke test

```bash
curl -s https://<endpoint>/api/health
curl -s -X POST https://<endpoint>/api/allocate \
  -H 'content-type: application/json' \
  -d '{"mode":"auto"}'
```

The second call costs one Ultra completion. `mode:"policy"` is free and proves the offline path.

---

## 3. What to put in the submission

Only claim a URL after it answers **200 in a private window**. The static URL listed above was checked
that way; if you redeploy, check it again before you submit.

The static Vercel URL is the one a judge can open without a key. The Nebius endpoint is the one that can
make a live call.
