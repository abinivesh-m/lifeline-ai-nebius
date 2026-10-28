"""Serve the exported UI and one live endpoint, with no framework and no Node.

Why this file exists
--------------------
``ui/`` is a Next.js app, but the demo must not depend on a Node server: the
judging machine has no internet and no build step at run time. ``next build``
with ``output: "export"`` writes a plain folder of files, and this module hosts
it with Python's own ``http.server``.

It also exposes exactly one dynamic route, ``POST /api/allocate``, which runs the
real engine (``allocator.allocate``): evidence rows from ``town.json``, a
Nemotron 3 Ultra proposal when ``NEBIUS_API_KEY`` is set, and the deterministic
validator either way. The page works fully offline; that route is the live part.

Run:
    python deploy/serve.py                 # http://127.0.0.1:8080
    python deploy/serve.py --port 3000
    python deploy/serve.py --host 0.0.0.0  # reachable from outside the host

Routes:
    GET  /                the exported app
    GET  /api/health      what is configured, without spending a token
    POST /api/allocate    one real allocation; body {"mode": "auto"|"policy"}
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "ui" / "out"

# `python deploy/serve.py` puts deploy/ first on the path; the engine modules
# live at the repository root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MAX_BODY = 4 * 1024

# The exported site has one HTML entry point; anything without an extension is
# that page, so a hand-typed URL never 404s during a demo.
INDEX = "index.html"


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class Handler(SimpleHTTPRequestHandler):
    server_version = "LifeLineAI/1.0"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(self.site()), **kwargs)

    def site(self) -> Path:
        """The directory set by ``--dir``, or the built export."""
        server = getattr(self, "server", None)
        return Path(getattr(server, "site_dir", SITE))

    # -- helpers ---------------------------------------------------------- #

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        page = SITE / "404.html"
        body = page.read_bytes() if page.exists() else b"not found"
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- routes ----------------------------------------------------------- #

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            self._send_json(health())
            return
        if path in ("/", "/index.html"):
            self.path = f"/{INDEX}"
        elif not Path(path).suffix and not path.startswith("/_next"):
            # A route without an extension is a directory export (`/live/`).
            # Serve that directory's index when it exists, otherwise fall back
            # to the single-page app.
            route = path.strip("/").rstrip("/")
            candidate = self.site() / route / INDEX
            if route and candidate.exists():
                self.path = f"/{route}/{INDEX}"
            else:
                self.path = f"/{INDEX}"
        if not (self.site() / self.path.lstrip("/")).exists() and Path(self.path).suffix:
            self._not_found()
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        path = self.path.split("?", 1)[0]
        if path != "/api/allocate":
            self._send_json({"error": "unknown route", "path": path}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            self._send_json({"error": "body too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json({"error": f"bad JSON: {exc}"}, HTTPStatus.BAD_REQUEST)
            return
        mode = str((body or {}).get("mode") or "auto")
        self._send_json(allocate(mode))

    def log_message(self, fmt: str, *args) -> None:  # quieter than the default
        sys.stdout.write(f"  {self.address_string()} {fmt % args}\n")


def health() -> dict:
    """Configuration, without spending anything."""
    import allocator
    import brain

    allocator.load_env()
    return {
        "status": "ok",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site": str(SITE),
        "site_built": (SITE / INDEX).exists(),
        "engine": brain.describe(),
        "tavily": bool(os.environ.get("TAVILY_API_KEY")),
        "modes": ["auto", "policy", "nebius"],
        "note": (
            "GET is static; POST /api/allocate runs the real allocator. "
            "Nothing is dispatched - the gate is human."
        ),
    }


def allocate(mode: str = "auto") -> dict:
    """Run the real allocator. Never raises: the caller gets a status instead."""
    import allocator

    if mode not in ("auto", "policy", "nebius"):
        return {"status": "error", "detail": f"unknown mode {mode!r}", "modes": ["auto", "policy", "nebius"]}
    allocator.load_env()
    try:
        result = allocator.allocate(allocator.load_town(), mode=mode)
    except Exception as exc:  # noqa: BLE001 - a demo server must not 500 silently
        return {"status": "error", "detail": f"{type(exc).__name__}: {exc}"}
    trace = result.get("trace") or {}
    brain_trace = trace.get("nebius") or {}
    return {
        "status": "ok",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "source": result.get("source"),
        "allocation": result.get("allocation"),
        "total": result.get("total"),
        "justification": result.get("justification"),
        "confidence": result.get("confidence"),
        "validation": result.get("validation"),
        "executed": result.get("executed"),
        "human_approval_required": result.get("human_approval_required"),
        "brain": {
            "provider": brain_trace.get("provider"),
            "model": brain_trace.get("model"),
            "status": brain_trace.get("status"),
            "latency_s": brain_trace.get("latency_s"),
            "cost_usd": brain_trace.get("cost_usd"),
            "detail": brain_trace.get("detail"),
        },
        "evidence": result.get("evidence"),
        "inference": result.get("inference"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the exported LifeLine AI UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--dir", default=str(SITE), help="directory to serve")
    args = parser.parse_args(argv)

    site = Path(args.dir).resolve()
    if not (site / INDEX).exists():
        print(
            f"  {site / INDEX} not found - run `npm run build` in ui/ first",
            file=sys.stderr,
        )
        return 2

    mimetypes.add_type("application/json", ".json")
    mimetypes.add_type("text/javascript", ".js")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.site_dir = site  # type: ignore[attr-defined]
    print(f"  LifeLine AI on http://{args.host}:{args.port}")
    print(f"  site: {site}")
    print("  POST /api/allocate · GET /api/health · Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
